"""Routes FastAPI du dashboard.

Renvoie des fragments HTML rendus par Jinja2. Les interactions
asynchrones passent par HTMX (boutons et formulaires) ou par WebSocket
(push de statut). Aucune valeur clinique patient n'est jamais
inseree dans les templates.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

if TYPE_CHECKING:
    from bridge_core.core import BridgeCore

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _color_label(color: str) -> str:
    return {
        "green": "Nominal",
        "amber": "Anomalie",
        "red": "Deconnecte",
        "gray": "Inconnu",
    }.get(color, color)


def _humanize_seconds(delta: float) -> str:
    if delta < 1:
        return "a l'instant"
    if delta < 60:
        return f"il y a {int(delta)} s"
    if delta < 3600:
        return f"il y a {int(delta // 60)} min"
    return f"il y a {int(delta // 3600)} h"


templates.env.filters["color_label"] = _color_label


def _common_context(request: Request) -> dict[str, object]:
    return {
        "request": request,
        "now_utc": datetime.now(tz=UTC).isoformat(),
        "year": datetime.now(tz=UTC).year,
    }


# =====================================================================
# Vue d'ensemble
# =====================================================================


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request) -> HTMLResponse:
    core: BridgeCore = request.app.state.core
    statuses = core.device_statuses()
    counters = _counters_summary(core)
    recent_events = [e.to_dict() for e in core.events.recent(limit=10)]

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            **_common_context(request),
            "active_section": "overview",
            "statuses": statuses,
            "counters": counters,
            "events": recent_events,
            "humanize": _humanize_seconds,
        },
    )


@router.get("/fragments/devices-grid", response_class=HTMLResponse)
async def fragment_devices_grid(request: Request) -> HTMLResponse:
    """Fragment HTMX rafraichi periodiquement par la home."""
    core: BridgeCore = request.app.state.core
    statuses = core.device_statuses()
    return templates.TemplateResponse(
        request,
        "partials/devices_grid.html",
        {
            **_common_context(request),
            "statuses": statuses,
            "humanize": _humanize_seconds,
        },
    )


@router.get("/fragments/recent-events", response_class=HTMLResponse)
async def fragment_recent_events(request: Request) -> HTMLResponse:
    core: BridgeCore = request.app.state.core
    events = [e.to_dict() for e in core.events.recent(limit=10)]
    return templates.TemplateResponse(
        request,
        "partials/events_list.html",
        {
            **_common_context(request),
            "events": events,
            "humanize": _humanize_seconds,
        },
    )


# =====================================================================
# Detail d'un equipement
# =====================================================================


@router.get("/devices/{device_id}", response_class=HTMLResponse)
async def device_detail(request: Request, device_id: str) -> HTMLResponse:
    core: BridgeCore = request.app.state.core
    profile = core.profiles.get(device_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    status = next(
        (s for s in core.device_statuses() if s.device_id == device_id), None
    )
    events = [e.to_dict() for e in core.events.recent(limit=50, device_id=device_id)]

    return templates.TemplateResponse(
        request,
        "device_detail.html",
        {
            **_common_context(request),
            "active_section": "overview",
            "profile": profile,
            "status": status,
            "events": events,
            "humanize": _humanize_seconds,
        },
    )


# =====================================================================
# Configuration des profils
# =====================================================================


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request) -> HTMLResponse:
    core: BridgeCore = request.app.state.core
    profiles = list(core.profiles.values())
    return templates.TemplateResponse(
        request,
        "config.html",
        {
            **_common_context(request),
            "active_section": "config",
            "profiles": profiles,
        },
    )


# =====================================================================
# Logs
# =====================================================================


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(
    request: Request,
    device: str | None = None,
    level: str | None = None,
) -> HTMLResponse:
    core: BridgeCore = request.app.state.core
    events = core.events.recent(limit=200, device_id=device)
    if level:
        events = [e for e in events if e.level == level]

    devices = sorted(core.profiles.keys())
    return templates.TemplateResponse(
        request,
        "logs.html",
        {
            **_common_context(request),
            "active_section": "logs",
            "events": [e.to_dict() for e in events],
            "devices": devices,
            "selected_device": device,
            "selected_level": level,
            "humanize": _humanize_seconds,
        },
    )


# =====================================================================
# Plugins
# =====================================================================


@router.get("/plugins", response_class=HTMLResponse)
async def plugins_page(request: Request) -> HTMLResponse:
    pm = request.app.state.plugin_manager
    records = list(pm.records.values()) if hasattr(pm, "records") else []
    return templates.TemplateResponse(
        request,
        "plugins.html",
        {
            **_common_context(request),
            "active_section": "plugins",
            "records": records,
        },
    )


# =====================================================================
# WebSocket pour push temps reel
# =====================================================================


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await websocket.accept()
    core: BridgeCore = websocket.app.state.core
    queue = core.events.subscribe()
    try:
        # Heartbeat optionnel : toutes les 15 s pour eviter les coupures proxy
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                await websocket.send_json(event.to_dict())
            except TimeoutError:
                await websocket.send_json({"kind": "heartbeat"})
    except WebSocketDisconnect:
        pass
    finally:
        core.events.unsubscribe(queue)


# =====================================================================
# Helpers
# =====================================================================


def _counters_summary(core: BridgeCore) -> dict[str, int]:
    statuses = core.device_statuses()
    connected = sum(1 for s in statuses if s.color == "green")
    anomaly = sum(1 for s in statuses if s.color == "amber")
    disconnected = sum(1 for s in statuses if s.color == "red")
    total_messages = sum(s.messages_total for s in statuses)
    quarantine = sum(s.messages_in_quarantine for s in statuses)
    return {
        "devices_total": len(statuses),
        "devices_connected": connected,
        "devices_anomaly": anomaly,
        "devices_disconnected": disconnected,
        "messages_total": total_messages,
        "messages_quarantine": quarantine,
    }
