"""Interface de base du Mapper Layer.

Un Mapper transforme une `NormalizedMeasurement` en un payload pret pour
la destination. Pour FHIR R4, le payload est un Bundle de type
`transaction` contenant Patient, Device et un ou plusieurs Observation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from bridge_core.registry import Registry

if TYPE_CHECKING:
    from bridge_core.models import DeviceProfile, NormalizedMeasurement


class BaseMapper(ABC):
    """Interface abstraite d'un Mapper."""

    def __init__(self, profile: DeviceProfile) -> None:
        self.profile = profile

    @abstractmethod
    def map(self, normalized: NormalizedMeasurement) -> dict[str, Any]:
        """Transforme la mesure normalisee en payload destination-ready."""


mapper_registry: Registry[type[BaseMapper]] = Registry("mapper")
