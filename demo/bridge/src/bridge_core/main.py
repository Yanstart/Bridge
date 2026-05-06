"""Point d'entree FastAPI du bridge.

Wire les 4 couches via BridgeCore. Charge les profils depuis `profiles/`,
decouvre les plugins dans `plugins/`, expose les endpoints HTTP minimaux.

Sprint 2 : architecture modulaire complete + profils JSON. Aucun Adapter
concret enregistre par defaut. Au sprint 3, on ajoute TcpMllpAdapter +
Hl7v2Parser et le premier flux end-to-end fonctionne.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from bridge_core import __version__
from bridge_core.adapter.base import adapter_registry
from bridge_core.config import ProfileLoader
from bridge_core.core import BridgeCore
from bridge_core.dashboard import router as dashboard_router
from bridge_core.mapper.base import mapper_registry
from bridge_core.parser.base import parser_registry
from bridge_core.plugin import PluginManager
from bridge_core.transport.base import transport_registry

# Importer les modules pour declencher leurs decorateurs @register
from bridge_core.adapter import file_watcher as _file_watcher  # noqa: F401
from bridge_core.adapter import mqtt as _mqtt_adapter  # noqa: F401
from bridge_core.adapter import serial_tcp as _serial_tcp  # noqa: F401
from bridge_core.adapter import tcp_mllp as _tcp_mllp  # noqa: F401
from bridge_core.mapper import fhir as _fhir_mapper  # noqa: F401
from bridge_core.parser import hl7v2 as _hl7v2_parser  # noqa: F401
from bridge_core.parser import json_path as _json_parser  # noqa: F401
from bridge_core.parser import medibus as _medibus_parser  # noqa: F401
from bridge_core.transport import fhir_hapi as _fhir_hapi  # noqa: F401
from bridge_core.transport import log_only as _log_only  # noqa: F401

logger = structlog.get_logger(__name__)

PROFILES_DIR = Path(os.getenv("PROFILES_DIR", "/app/profiles"))
PLUGINS_DIR = Path(os.getenv("PLUGINS_DIR", "/app/plugins"))
FALLBACK_DB = Path(os.getenv("FALLBACK_DB", "/app/data/fallback.sqlite"))
REPLAY_INTERVAL_SEC = float(os.getenv("REPLAY_INTERVAL_SEC", "30"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cycle de vie : charge les profils + plugins, demarre le BridgeCore."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ]
    )

    logger.info(
        "bridge.startup",
        version=__version__,
        profiles_dir=str(PROFILES_DIR),
        plugins_dir=str(PLUGINS_DIR),
    )

    # 1. Decouvrir et charger les plugins AVANT les profils, pour que
    #    leurs Adapter/Parser/Mapper/Transport custom soient enregistres
    #    quand le BridgeCore tente d'instancier les pipelines.
    plugin_manager = PluginManager(PLUGINS_DIR)
    plugin_manager.discover()
    plugin_manager.load_all()
    manifests = plugin_manager.manifests

    # 2. Charger les profils (qui peuvent reference les types ajoutes par plugins)
    loader = ProfileLoader(PROFILES_DIR)
    profiles = loader.load_all()

    # 3. Demarrer le BridgeCore (instancie les pipelines + fallback SQLite)
    core = BridgeCore(
        profiles,
        fallback_db=FALLBACK_DB,
        replay_interval_seconds=REPLAY_INTERVAL_SEC,
    )
    await core.start()

    # Stockage dans l'etat de l'app
    app.state.loader = loader
    app.state.plugin_manager = plugin_manager
    app.state.core = core
    app.state.manifests = manifests

    yield

    # Arret propre
    await core.stop()
    logger.info("bridge.shutdown")


app = FastAPI(
    title="IoT Edge Bridge",
    description=(
        "Passerelle d'interoperabilite pour dispositifs medicaux Legacy. "
        "Absorbe TCP/MLLP, MQTT, fichier et RS-232. Publie en FHIR R4."
    ),
    version=__version__,
    lifespan=lifespan,
)


from pathlib import Path as _Path

_STATIC_DIR = _Path(__file__).parent / "dashboard" / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
app.include_router(dashboard_router)


@app.get("/api/info")
async def api_info() -> dict[str, str]:
    return {
        "name": "IoT Edge Bridge",
        "version": __version__,
        "status": "ok",
    }


@app.get("/health")
async def health() -> dict[str, object]:
    """Healthcheck JSON."""
    return {
        "status": "ok",
        "version": __version__,
        "registries": {
            "adapter": adapter_registry.names(),
            "parser": parser_registry.names(),
            "mapper": mapper_registry.names(),
            "transport": transport_registry.names(),
        },
    }


@app.get("/api/devices")
async def list_devices() -> dict[str, object]:
    """Liste les profils charges et leur etat operationnel."""
    core: BridgeCore = app.state.core
    statuses = core.device_statuses()
    return {
        "count": len(statuses),
        "devices": [s.model_dump(mode="json") for s in statuses],
    }


@app.get("/api/profiles")
async def list_profiles() -> dict[str, object]:
    """Liste les profils JSON charges (vue brute pour debug)."""
    loader: ProfileLoader = app.state.loader
    return {
        "count": len(loader.profiles),
        "profiles": {
            device_id: profile.model_dump(mode="json")
            for device_id, profile in loader.profiles.items()
        },
    }


@app.get("/api/plugins")
async def api_list_plugins() -> dict[str, object]:
    """Liste les manifestes plugins decouverts."""
    pm: PluginManager = app.state.plugin_manager
    return {
        "count": len(pm.manifests),
        "plugins": [m.model_dump(mode="json") for m in pm.manifests.values()],
    }


@app.get("/api/queue")
async def api_queue() -> dict[str, object]:
    """Etat de la file de repli SQLite."""
    core: BridgeCore = app.state.core
    if core.fallback_queue is None:
        return {"enabled": False, "count": 0, "items": []}
    items = core.fallback_queue.list_pending(limit=50)
    return {
        "enabled": True,
        "count": core.fallback_queue.count(),
        "items": [
            {
                "id": item.id,
                "device_id": item.device_id,
                "enqueued_at": item.enqueued_at.isoformat(),
                "retries": item.retries,
                "last_error": item.last_error,
            }
            for item in items
        ],
    }


@app.post("/api/reload")
async def api_reload() -> dict[str, object]:
    """Recharge les profils JSON et redemarre le BridgeCore.

    Le hot-reload des plugins necessite un redemarrage du processus
    (Python ne supporte pas le rechargement propre des modules importes).
    On recharge donc uniquement les profils, et on signale les eventuels
    types manquants.
    """
    loader: ProfileLoader = app.state.loader
    core: BridgeCore = app.state.core

    new_profiles = loader.load_all()

    await core.stop()

    new_core = BridgeCore(
        new_profiles,
        fallback_db=FALLBACK_DB,
        replay_interval_seconds=REPLAY_INTERVAL_SEC,
    )
    await new_core.start()
    app.state.core = new_core

    return {
        "status": "ok",
        "profiles_loaded": len(new_profiles),
        "adapters_running": list(new_core.adapters.keys()),
    }


def run() -> None:
    """Entry point CLI : `bridge-server`."""
    uvicorn.run(
        "bridge_core.main:app",
        host="0.0.0.0",  # noqa: S104  (conteneur)
        port=int(os.getenv("BRIDGE_PORT", "8080")),
        log_level=os.getenv("LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    run()
