"""PluginManager : decouverte et chargement des plugins.

Chaque plugin est un dossier dans `plugins/` contenant :
- `plugin.toml` : manifeste (nom, version, layer, codes LOINC, entrypoints)
- un ou plusieurs modules Python qui enregistrent des Adapter / Parser /
  Mapper / Transport via les registries.

Cycle de vie :
1. `discover()` scanne le dossier et lit chaque `plugin.toml`.
2. `load()` ajoute le dossier du plugin a `sys.path` et importe le module
   declaratif `entrypoints.module`. Les decorateurs `@register` y declares
   ajoutent les types au registry approprie.
3. Si l'import echoue, le plugin est marque `error` et l'exception est
   journalisee. Le coeur du bridge continue a tourner.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import structlog
from pydantic import ValidationError

from bridge_core.models import PluginManifest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]

logger = structlog.get_logger(__name__)

PluginStatus = Literal["loaded", "error", "discovered"]


@dataclass
class PluginRecord:
    """Etat d'un plugin connu du manager."""

    name: str
    path: Path
    manifest: PluginManifest
    status: PluginStatus = "discovered"
    error: str | None = None
    loaded_at: datetime | None = None


class PluginManager:
    """Decouvre et charge les plugins du repertoire `plugins/`."""

    def __init__(self, plugins_dir: Path) -> None:
        self.plugins_dir = plugins_dir
        self._records: dict[str, PluginRecord] = {}

    # -----------------------------------------------------------------
    # Decouverte
    # -----------------------------------------------------------------

    def discover(self) -> dict[str, PluginRecord]:
        """Scanne le repertoire, lit les `plugin.toml`, sans charger les modules."""
        self._records.clear()

        if not self.plugins_dir.exists():
            logger.info("plugin_manager.dir_missing", path=str(self.plugins_dir))
            return self._records

        for entry in sorted(self.plugins_dir.iterdir()):
            if not entry.is_dir():
                continue
            toml_path = entry / "plugin.toml"
            if not toml_path.exists():
                continue
            try:
                manifest = self._read_manifest(toml_path)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "plugin_manager.invalid_manifest",
                    plugin=entry.name,
                    error=str(exc),
                )
                continue
            record = PluginRecord(name=manifest.name, path=entry, manifest=manifest)
            self._records[manifest.name] = record
            logger.info(
                "plugin_manager.discovered",
                name=manifest.name,
                version=manifest.version,
                layer=manifest.layer,
            )

        logger.info("plugin_manager.summary", count=len(self._records))
        return self._records

    # -----------------------------------------------------------------
    # Chargement effectif des modules Python
    # -----------------------------------------------------------------

    def load_all(self) -> None:
        """Charge tous les plugins decouverts, isole les erreurs."""
        for record in self._records.values():
            self._load_one(record)

    def _load_one(self, record: PluginRecord) -> None:
        module_name = record.manifest.entrypoints.get("module") if record.manifest.entrypoints else None
        if not module_name:
            record.status = "loaded"
            record.loaded_at = datetime.now(tz=UTC)
            logger.info("plugin_manager.no_module", plugin=record.name)
            return

        plugin_path = str(record.path)
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)

        # Cle d'import : nom du plugin + nom du module
        full_module = f"{record.path.name.replace('-', '_')}__{module_name}"

        try:
            spec = importlib.util.spec_from_file_location(
                full_module,
                record.path / f"{module_name}.py",
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"module {module_name}.py introuvable dans {record.path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[full_module] = module
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            record.status = "error"
            record.error = f"{type(exc).__name__}: {exc}"
            logger.error(
                "plugin_manager.load_error",
                plugin=record.name,
                error=record.error,
                trace=traceback.format_exc(limit=3),
            )
            return

        record.status = "loaded"
        record.loaded_at = datetime.now(tz=UTC)
        logger.info(
            "plugin_manager.loaded",
            plugin=record.name,
            module=module_name,
        )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _read_manifest(self, path: Path) -> PluginManifest:
        with path.open("rb") as f:
            data = tomllib.load(f)
        plugin = data.get("plugin", {})
        flat: dict[str, Any] = {**plugin}
        if "loinc" in data:
            flat["loinc_codes"] = data["loinc"].get("codes", [])
        if "entrypoints" in data:
            flat["entrypoints"] = data["entrypoints"]
        try:
            return PluginManifest.model_validate(flat)
        except ValidationError as exc:
            raise ValueError(f"manifest invalide : {exc}") from exc

    @property
    def records(self) -> dict[str, PluginRecord]:
        return dict(self._records)

    @property
    def manifests(self) -> dict[str, PluginManifest]:
        """Compatibilite avec le code existant : expose les manifestes."""
        return {name: rec.manifest for name, rec in self._records.items()}
