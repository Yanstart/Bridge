"""Interface de base de l'Adapter Layer.

Un Adapter ouvre une source (port TCP, abonnement MQTT, surveillance de
dossier, port serie) et emet des `RawFrame` vers une queue commune. Les
Adapters concrets sont enregistres dans `adapter_registry` et instancies
par le BridgeCore a partir d'un `DeviceProfile`.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

from bridge_core.registry import Registry

if TYPE_CHECKING:
    from bridge_core.models import DeviceProfile

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class RawFrame:
    """Trame brute capturee par un Adapter, avant decodage."""

    device_id: str
    payload: bytes
    received_at_utc: datetime
    metadata: dict[str, str]


class BaseAdapter(ABC):
    """Interface abstraite d'un Adapter.

    Cycle de vie :
    - `__init__(profile)` : instanciation a partir d'un profil JSON.
    - `start(queue)` : demarre la capture asynchrone, pousse les RawFrame.
    - `stop()` : arret propre.
    """

    def __init__(self, profile: DeviceProfile) -> None:
        self.profile = profile
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self, queue: asyncio.Queue[RawFrame]) -> None:
        """Demarre la capture asynchrone."""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(queue), name=f"adapter-{self.profile.id}")
        logger.info("adapter.started", device_id=self.profile.id, type=self.profile.channel.type)

    async def stop(self) -> None:
        """Arrete la capture proprement."""
        self._stop_event.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except TimeoutError:
                self._task.cancel()
                logger.warning("adapter.stop_timeout", device_id=self.profile.id)
        logger.info("adapter.stopped", device_id=self.profile.id)

    @abstractmethod
    async def _run(self, queue: asyncio.Queue[RawFrame]) -> None:
        """Boucle de capture. A implementer par chaque Adapter concret."""

    def _make_frame(self, payload: bytes, metadata: dict[str, str] | None = None) -> RawFrame:
        """Helper pour construire un RawFrame avec horodatage UTC."""
        return RawFrame(
            device_id=self.profile.id,
            payload=payload,
            received_at_utc=datetime.now(tz=UTC),
            metadata=metadata or {},
        )


# Registry global des Adapters concrets, peuple par les modules adapter/*.py
# et par les plugins communautaires (sprint 6).
adapter_registry: Registry[type[BaseAdapter]] = Registry("adapter")
