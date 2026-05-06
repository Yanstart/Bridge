"""BridgeCore : orchestre les 4 couches Adapter/Parser/Mapper/Transport.

Le coeur instancie pour chaque DeviceProfile :
- 1 Adapter (selon `profile.channel.type`)
- 1 Parser (selon `profile.parser.type`)
- 1 Mapper (par defaut `fhir_bundle`)
- 1 Transport (selon `profile.destination.type`)

Tous les Adapters partagent une meme `asyncio.Queue[RawFrame]`. Une
boucle de traitement consomme les trames, les passe au Parser puis au
Mapper, et envoie le resultat au Transport.

Au sprint 2, les implementations concretes (TCP MLLP, MQTT, etc.) ne
sont pas encore enregistrees. Le BridgeCore s'instancie sans erreur
mais ne traite rien tant qu'aucun Adapter concret n'est enregistre.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from bridge_core.adapter.base import BaseAdapter, RawFrame, adapter_registry
from bridge_core.events import BridgeEvent, EventBuffer
from bridge_core.mapper.base import BaseMapper, mapper_registry
from bridge_core.parser.base import BaseParser, ParseError, parser_registry
from bridge_core.persistence import FallbackQueue
from bridge_core.transport.base import BaseTransport, transport_registry
from bridge_core.transport.fhir_hapi import FhirHapiTransport

if TYPE_CHECKING:
    from bridge_core.models import DeviceProfile, DeviceStatus

logger = structlog.get_logger(__name__)


class BridgeCore:
    """Orchestrateur principal du middleware."""

    def __init__(
        self,
        profiles: dict[str, DeviceProfile],
        mapper_type: str = "fhir_bundle",
        fallback_db: Path | None = None,
        replay_interval_seconds: float = 30.0,
    ) -> None:
        self.profiles = profiles
        self.mapper_type = mapper_type
        self.queue: asyncio.Queue[RawFrame] = asyncio.Queue(maxsize=1000)
        self.adapters: dict[str, BaseAdapter] = {}
        self.parsers: dict[str, BaseParser] = {}
        self.mappers: dict[str, BaseMapper] = {}
        self.transports: dict[str, BaseTransport] = {}
        self.statuses: dict[str, _DeviceCounters] = defaultdict(_DeviceCounters)
        self.events = EventBuffer(capacity=300)
        self.fallback_queue: FallbackQueue | None = None
        if fallback_db is not None:
            self.fallback_queue = FallbackQueue(fallback_db)
            FhirHapiTransport.attach_fallback(self.fallback_queue)
        self.replay_interval_seconds = replay_interval_seconds
        self._processing_task: asyncio.Task[None] | None = None
        self._replay_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Demarre tous les Adapters et la boucle de traitement."""
        for device_id, profile in self.profiles.items():
            if not profile.enabled:
                continue
            try:
                self._instantiate_pipeline(profile)
            except KeyError as exc:
                logger.error(
                    "bridge_core.skip_profile",
                    device_id=device_id,
                    reason=str(exc),
                )
                continue

        # Demarrage Adapters
        for adapter in self.adapters.values():
            await adapter.start(self.queue)

        # Boucle de traitement
        self._stop_event.clear()
        self._processing_task = asyncio.create_task(self._process_loop(), name="bridge-process")

        # Boucle de rejeu de la file de repli
        if self.fallback_queue is not None:
            self._replay_task = asyncio.create_task(self._replay_loop(), name="bridge-replay")

        logger.info(
            "bridge_core.started",
            adapters=list(self.adapters),
            parsers=list(self.parsers),
            transports=list(self.transports),
            fallback=self.fallback_queue is not None,
        )

    async def stop(self) -> None:
        """Arrete proprement Adapters et boucles internes."""
        self._stop_event.set()
        for adapter in self.adapters.values():
            await adapter.stop()
        if self._processing_task is not None:
            self._processing_task.cancel()
        if self._replay_task is not None:
            self._replay_task.cancel()
        for transport in self.transports.values():
            await transport.close()
        logger.info("bridge_core.stopped")

    async def _replay_loop(self) -> None:
        """Tente periodiquement de rejouer les Bundles en file de repli."""
        assert self.fallback_queue is not None
        import httpx

        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self.replay_interval_seconds)
                items = self.fallback_queue.list_pending(limit=20)
                if not items:
                    continue
                logger.info("bridge_core.replay_start", queue_size=len(items))
                for item in items:
                    transport = self.transports.get(item.device_id)
                    if transport is None:
                        # Profil non charge : on garde l'item, on ne le perd pas
                        continue
                    try:
                        status = await transport.send(item.payload)
                    except Exception as exc:  # noqa: BLE001
                        self.fallback_queue.mark_failed(item.id, f"replay: {type(exc).__name__}")
                        continue
                    if status.success:
                        self.fallback_queue.mark_sent(item.id)
                        self.events.push(
                            BridgeEvent(
                                kind="transport_success",
                                level="info",
                                device_id=item.device_id,
                                message=f"rejeu reussi (item #{item.id})",
                            )
                        )
                    else:
                        self.fallback_queue.mark_failed(
                            item.id, status.error_message or "replay failed"
                        )
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("bridge_core.replay_error", error=str(exc))

    def _instantiate_pipeline(self, profile: DeviceProfile) -> None:
        """Instancie les 4 couches pour un profil donne."""
        adapter_cls = adapter_registry.get(profile.channel.type)
        parser_cls = parser_registry.get(profile.parser.type)
        mapper_cls = mapper_registry.get(self.mapper_type)
        transport_cls = transport_registry.get(profile.destination.type)

        self.adapters[profile.id] = adapter_cls(profile)
        self.parsers[profile.id] = parser_cls(profile)
        self.mappers[profile.id] = mapper_cls(profile)
        self.transports[profile.id] = transport_cls(profile)

    async def _process_loop(self) -> None:
        """Consomme les RawFrame et execute Parser->Mapper->Transport."""
        while not self._stop_event.is_set():
            try:
                frame = await asyncio.wait_for(self.queue.get(), timeout=0.5)
            except TimeoutError:
                continue

            await self._process_one(frame)

    async def _process_one(self, frame: RawFrame) -> None:
        device_id = frame.device_id
        counters = self.statuses[device_id]
        counters.last_seen = frame.received_at_utc

        parser = self.parsers.get(device_id)
        mapper = self.mappers.get(device_id)
        transport = self.transports.get(device_id)
        if not (parser and mapper and transport):
            logger.warning("bridge_core.no_pipeline", device_id=device_id)
            return

        self.events.push(
            BridgeEvent(
                kind="frame_received",
                level="info",
                device_id=device_id,
                message=f"trame de {len(frame.payload)} octets recue",
            )
        )

        # 1. Parser
        try:
            normalized = parser.parse(frame)
        except ParseError as exc:
            counters.quarantined += 1
            counters.last_error = f"parse: {exc}"
            self.events.push(
                BridgeEvent(
                    kind="frame_quarantined",
                    level="warn",
                    device_id=device_id,
                    message=str(exc),
                )
            )
            logger.warning(
                "bridge_core.parse_error",
                device_id=device_id,
                error=str(exc),
            )
            return

        self.events.push(
            BridgeEvent(
                kind="frame_parsed",
                level="info",
                device_id=device_id,
                message=f"{len(normalized.measurements)} mesure(s) normalisee(s)",
            )
        )

        # 2. Mapper
        try:
            payload = mapper.map(normalized)
        except Exception as exc:  # noqa: BLE001  (mapper peut leve diverses erreurs)
            counters.errors += 1
            counters.last_error = f"map: {type(exc).__name__}"
            self.events.push(
                BridgeEvent(
                    kind="transport_failure",
                    level="error",
                    device_id=device_id,
                    message=f"erreur mapping: {type(exc).__name__}",
                )
            )
            logger.error("bridge_core.map_error", device_id=device_id, error=str(exc))
            return

        # 3. Transport
        try:
            status = await transport.send(payload)
        except Exception as exc:  # noqa: BLE001
            counters.errors += 1
            counters.last_error = f"transport: {type(exc).__name__}"
            self.events.push(
                BridgeEvent(
                    kind="transport_failure",
                    level="error",
                    device_id=device_id,
                    message=f"erreur transport: {type(exc).__name__}",
                )
            )
            logger.error("bridge_core.transport_error", device_id=device_id, error=str(exc))
            return

        if status.success:
            counters.success += 1
            self.events.push(
                BridgeEvent(
                    kind="transport_success",
                    level="info",
                    device_id=device_id,
                    message=f"publication FHIR {status.http_status or ''}".strip(),
                    extra={"resources": len(status.fhir_resource_ids)},
                )
            )
        else:
            counters.errors += 1
            counters.last_error = status.error_message or "transport failed"
            self.events.push(
                BridgeEvent(
                    kind="transport_failure",
                    level="error",
                    device_id=device_id,
                    message=status.error_message or "transport failed",
                )
            )

    # -----------------------------------------------------------------
    # Etat pour le dashboard
    # -----------------------------------------------------------------

    def device_statuses(self) -> list[DeviceStatus]:
        """Etat operationnel de tous les profils, pour le dashboard."""
        from bridge_core.models import DeviceStatus

        result: list[DeviceStatus] = []
        now = datetime.now(tz=UTC)
        for device_id, profile in self.profiles.items():
            counters = self.statuses[device_id]
            color, ctx = self._compute_color(counters, now)
            result.append(
                DeviceStatus(
                    device_id=device_id,
                    name=profile.name,
                    color=color,
                    last_seen_utc=counters.last_seen,
                    messages_total=counters.success + counters.errors + counters.quarantined,
                    messages_in_quarantine=counters.quarantined,
                    indicative_context=ctx,
                )
            )
        return result

    @staticmethod
    def _compute_color(
        counters: _DeviceCounters, now: datetime
    ) -> tuple[str, str | None]:
        """Calcule la couleur de statut et un contexte indicatif."""
        if counters.last_seen is None:
            return "gray", "aucune communication recue"
        delta = (now - counters.last_seen).total_seconds()
        if delta > 30:
            return "red", f"n'emet plus depuis {int(delta)} s"
        if counters.quarantined > 0:
            return "amber", f"{counters.quarantined} message(s) en quarantaine"
        if counters.errors > 0:
            return "amber", counters.last_error or "erreurs detectees"
        return "green", None


class _DeviceCounters:
    """Compteurs internes par equipement (no PII)."""

    __slots__ = ("errors", "last_error", "last_seen", "quarantined", "success")

    def __init__(self) -> None:
        self.success: int = 0
        self.errors: int = 0
        self.quarantined: int = 0
        self.last_seen: datetime | None = None
        self.last_error: str | None = None
