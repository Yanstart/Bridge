"""LogOnlyTransport : journalise le payload sans le transmettre.

Utile pour les tests et la mise au point. Aucune valeur clinique n'est
journalisee : seules les metadonnees (device_id, nombre d'entrees,
timestamp) sont logguees.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from bridge_core.models import TransmissionStatus
from bridge_core.transport.base import BaseTransport, transport_registry

logger = structlog.get_logger(__name__)


@transport_registry.register("log_only")
class LogOnlyTransport(BaseTransport):
    """Affiche un log structure et marque la transmission comme reussie."""

    async def send(self, payload: dict[str, Any]) -> TransmissionStatus:
        entries = payload.get("entry", []) if isinstance(payload, dict) else []
        logger.info(
            "transport.log_only.sent",
            device_id=self.profile.id,
            entries=len(entries),
        )
        return TransmissionStatus(
            device_id=self.profile.id,
            timestamp_utc=datetime.now(tz=UTC),
            success=True,
            http_status=200,
        )
