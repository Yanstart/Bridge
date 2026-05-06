"""FhirHapiTransport : POST d'un Bundle FHIR vers HAPI FHIR Server.

Stratégie de fiabilité :
- Retry exponentiel via `tenacity` sur les erreurs reseau (3 tentatives,
  intervalles 1 s, 2 s, 4 s).
- Sur echec final apres retries : optionnellement enqueue dans la
  FallbackQueue pour rejeu ulterieur. Le bridge expose une tache
  d'arriere-plan (`replay_loop`) qui purge la queue toutes les N s.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bridge_core.models import TransmissionStatus
from bridge_core.persistence import FallbackQueue
from bridge_core.transport.base import BaseTransport, transport_registry

logger = structlog.get_logger(__name__)


@transport_registry.register("fhir_hapi")
class FhirHapiTransport(BaseTransport):
    """Envoie un Bundle FHIR R4 a un serveur HAPI, avec retry et fallback."""

    fallback_queue: FallbackQueue | None = None

    @classmethod
    def attach_fallback(cls, queue: FallbackQueue) -> None:
        """Branche la file de repli partagee (instanciee une fois par BridgeCore)."""
        cls.fallback_queue = queue

    async def send(self, payload: dict[str, Any]) -> TransmissionStatus:
        url = self.profile.destination.url
        timeout = self.profile.destination.timeout_seconds
        retry_max = max(1, self.profile.destination.retry_max)
        device_id = self.profile.id
        ts = datetime.now(tz=UTC)

        if not url:
            return TransmissionStatus(
                device_id=device_id,
                timestamp_utc=ts,
                success=False,
                error_message="destination.url manquant dans le profil",
            )

        last_error: str | None = None
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(retry_max),
                wait=wait_exponential(multiplier=1.0, min=1.0, max=8.0),
                retry=retry_if_exception_type(httpx.RequestError),
                reraise=True,
            ):
                with attempt:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(
                            url,
                            json=payload,
                            headers={
                                "Content-Type": "application/fhir+json",
                                "Accept": "application/fhir+json",
                            },
                        )
        except RetryError as exc:  # pragma: no cover (defensif)
            last_error = f"retry_error: {type(exc.last_attempt.exception()).__name__}"
        except httpx.RequestError as exc:
            last_error = f"network: {type(exc).__name__}"

        if last_error is not None:
            logger.warning(
                "transport.fhir_hapi.network_failure",
                device_id=device_id,
                error=last_error,
            )
            self._maybe_enqueue(payload, last_error)
            return TransmissionStatus(
                device_id=device_id,
                timestamp_utc=ts,
                success=False,
                error_message=last_error,
            )

        ok = response.is_success
        resource_ids: list[str] = []
        if ok:
            try:
                body = response.json()
                for entry in body.get("entry", []):
                    location = entry.get("response", {}).get("location")
                    if location:
                        resource_ids.append(location)
            except (ValueError, KeyError):
                pass

        logger.info(
            "transport.fhir_hapi.sent",
            device_id=device_id,
            http_status=response.status_code,
            ok=ok,
            resources=len(resource_ids),
        )

        if not ok:
            err = f"http {response.status_code}"
            self._maybe_enqueue(payload, err)
            return TransmissionStatus(
                device_id=device_id,
                timestamp_utc=ts,
                success=False,
                http_status=response.status_code,
                error_message=err,
            )

        return TransmissionStatus(
            device_id=device_id,
            timestamp_utc=ts,
            success=True,
            http_status=response.status_code,
            fhir_resource_ids=resource_ids,
        )

    def _maybe_enqueue(self, payload: dict[str, Any], error: str) -> None:
        """Persiste le bundle dans la file de repli si elle est branchee."""
        if FhirHapiTransport.fallback_queue is None:
            return
        try:
            FhirHapiTransport.fallback_queue.enqueue(self.profile.id, payload, error)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "transport.fhir_hapi.fallback_enqueue_error",
                device_id=self.profile.id,
                error=str(exc),
            )
