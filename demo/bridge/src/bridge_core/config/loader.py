"""ProfileLoader : lit, valide et expose les profils JSON dispositifs.

Au demarrage, le loader scanne le repertoire `profiles/` (configurable),
parse chaque `.json`, valide via Pydantic, et publie un dictionnaire
`{device_id: DeviceProfile}`. Une erreur sur un profil n'invalide pas
les autres : le profil fautif est ignore, l'erreur est loguee.

Le hot-reload via watchdog est ajoute au sprint 7 pour respecter
EF-ADP-006 (rechargement sans redemarrage).
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog
from pydantic import ValidationError

from bridge_core.models import DeviceProfile

logger = structlog.get_logger(__name__)


class ProfileLoadError(Exception):
    """Erreur de chargement d'un profil."""


class ProfileLoader:
    """Charge et expose les DeviceProfile depuis un repertoire."""

    def __init__(self, profiles_dir: Path) -> None:
        self.profiles_dir = profiles_dir
        self._profiles: dict[str, DeviceProfile] = {}

    def load_all(self) -> dict[str, DeviceProfile]:
        """Scanne le repertoire et charge tous les profils valides."""
        self._profiles.clear()

        if not self.profiles_dir.exists():
            logger.warning("profile_loader.dir_missing", path=str(self.profiles_dir))
            return self._profiles

        for path in sorted(self.profiles_dir.glob("*.json")):
            try:
                profile = self._load_one(path)
            except ProfileLoadError as exc:
                logger.error(
                    "profile_loader.invalid",
                    path=str(path),
                    error=str(exc),
                )
                continue
            self._profiles[profile.id] = profile
            logger.info(
                "profile_loader.loaded",
                device_id=profile.id,
                channel=profile.channel.type,
                parser=profile.parser.type,
                destination=profile.destination.type,
            )

        logger.info("profile_loader.summary", count=len(self._profiles))
        return self._profiles

    def _load_one(self, path: Path) -> DeviceProfile:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ProfileLoadError(f"lecture {path.name} : {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProfileLoadError(f"JSON invalide {path.name} : {exc}") from exc

        try:
            return DeviceProfile.model_validate(data)
        except ValidationError as exc:
            raise ProfileLoadError(f"schema invalide {path.name} : {exc}") from exc

    @property
    def profiles(self) -> dict[str, DeviceProfile]:
        return dict(self._profiles)

    def get(self, device_id: str) -> DeviceProfile | None:
        return self._profiles.get(device_id)
