"""Buffer circulaire d'evenements pour le dashboard.

Stocke les N derniers evenements operationnels (connexion, message
traite, quarantaine, erreur transport). Aucune valeur clinique
patient ne transite ici. Sert a alimenter :
- le flux d'activite recente (vue d'ensemble)
- la timeline d'un equipement (page detail)
- le push WebSocket
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

EventLevel = Literal["info", "warn", "error"]
EventKind = Literal[
    "device_connected",
    "device_disconnected",
    "frame_received",
    "frame_parsed",
    "frame_quarantined",
    "transport_success",
    "transport_failure",
    "plugin_loaded",
    "plugin_error",
    "config_reloaded",
]


@dataclass(slots=True)
class BridgeEvent:
    """Evenement operationnel sans donnee patient."""

    kind: EventKind
    level: EventLevel
    device_id: str | None
    message: str
    timestamp_utc: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "level": self.level,
            "device_id": self.device_id,
            "message": self.message,
            "timestamp": self.timestamp_utc.isoformat(),
            "extra": self.extra,
        }


class EventBuffer:
    """Deque borne avec abonnement asynchrone via asyncio.Queue."""

    def __init__(self, capacity: int = 200) -> None:
        self._buffer: deque[BridgeEvent] = deque(maxlen=capacity)
        self._subscribers: list[asyncio.Queue[BridgeEvent]] = []

    def push(self, event: BridgeEvent) -> None:
        """Ajoute un evenement et le diffuse aux abonnes (best-effort)."""
        self._buffer.append(event)
        for sub in list(self._subscribers):
            try:
                sub.put_nowait(event)
            except asyncio.QueueFull:
                # Abonne lent : on ignore pour ne pas bloquer le push
                pass

    def recent(self, limit: int = 50, device_id: str | None = None) -> list[BridgeEvent]:
        """Retourne les derniers evenements, plus recents en tete."""
        items = list(self._buffer)
        if device_id is not None:
            items = [e for e in items if e.device_id == device_id]
        items.reverse()
        return items[:limit]

    def subscribe(self) -> asyncio.Queue[BridgeEvent]:
        """Cree un abonnement pour le push WebSocket."""
        queue: asyncio.Queue[BridgeEvent] = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[BridgeEvent]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)
