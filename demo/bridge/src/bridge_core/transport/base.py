"""Interface de base du Transport Layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from bridge_core.registry import Registry

if TYPE_CHECKING:
    from bridge_core.models import DeviceProfile, TransmissionStatus


class BaseTransport(ABC):
    """Interface abstraite d'un Transport."""

    def __init__(self, profile: DeviceProfile) -> None:
        self.profile = profile

    @abstractmethod
    async def send(self, payload: dict[str, Any]) -> TransmissionStatus:
        """Envoie le payload a la destination, retourne le statut."""

    async def close(self) -> None:
        """Liberation propre des ressources (override si client persistant)."""


transport_registry: Registry[type[BaseTransport]] = Registry("transport")
