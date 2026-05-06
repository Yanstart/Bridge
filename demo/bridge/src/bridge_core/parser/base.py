"""Interface de base du Parser Layer.

Un Parser decode un `RawFrame` selon le format declare dans le profil
(HL7v2, JSON, XML, MEDIBUS ASCII, SCP-ECG, etc.) et produit une instance
de `NormalizedMeasurement`. Les valeurs hors plage de plausibilite sont
marquees mais pas filtrees ici (le filtrage est decide par le mapper).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import structlog

from bridge_core.registry import Registry

if TYPE_CHECKING:
    from bridge_core.adapter.base import RawFrame
    from bridge_core.models import DeviceProfile, NormalizedMeasurement

logger = structlog.get_logger(__name__)


class BaseParser(ABC):
    """Interface abstraite d'un Parser."""

    def __init__(self, profile: DeviceProfile) -> None:
        self.profile = profile

    @abstractmethod
    def parse(self, frame: RawFrame) -> NormalizedMeasurement:
        """Decode la trame brute et produit une mesure normalisee.

        Doit lever `ParseError` (ou sous-classe) en cas de format invalide.
        Le BridgeCore intercepte l'exception et place le message en
        quarantaine, avec le statut "amber" sur le dashboard.
        """


class ParseError(Exception):
    """Erreur de decodage. Le BridgeCore met le message en quarantaine."""


parser_registry: Registry[type[BaseParser]] = Registry("parser")
