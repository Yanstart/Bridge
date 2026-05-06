"""MqttAdapter : abonne le bridge a un topic MQTT et pousse les payloads.

Utilise `paho-mqtt` en mode network-loop pilote par un thread dedie ;
les messages recus sont transferes vers la queue asyncio via
`asyncio.run_coroutine_threadsafe`. C'est le pattern recommande par
paho pour cohabiter avec un event loop asyncio.

Le topic est lu depuis `profile.channel.topic` (wildcards `+` et `#`
supportes par MQTT). L'host par defaut est l'hote `mqtt` du compose.
"""

from __future__ import annotations

import asyncio
import threading

import structlog
from paho.mqtt import client as mqtt_client

from bridge_core.adapter.base import BaseAdapter, RawFrame, adapter_registry

logger = structlog.get_logger(__name__)


@adapter_registry.register("mqtt")
class MqttAdapter(BaseAdapter):
    """Abonne au broker MQTT et reemet les messages en RawFrame."""

    async def _run(self, queue: asyncio.Queue[RawFrame]) -> None:
        host = self.profile.channel.host or "mqtt"
        port = self.profile.channel.port or 1883
        topic = self.profile.channel.topic or f"devices/{self.profile.id}/#"
        loop = asyncio.get_running_loop()

        client = mqtt_client.Client(
            mqtt_client.CallbackAPIVersion.VERSION2,
            client_id=f"bridge-{self.profile.id}",
            clean_session=True,
        )

        def on_connect(_c, _u, _f, rc, _props=None) -> None:  # type: ignore[no-untyped-def]
            # paho-mqtt v2 callback API V2 : rc est un ReasonCode, pas un int.
            rc_value = getattr(rc, "value", rc)
            logger.info(
                "mqtt.connected",
                device_id=self.profile.id,
                host=host,
                port=port,
                rc=int(rc_value) if isinstance(rc_value, int) else str(rc_value),
            )
            client.subscribe(topic, qos=1)

        def on_message(_c, _u, msg) -> None:  # type: ignore[no-untyped-def]
            frame = self._make_frame(
                msg.payload,
                metadata={"topic": msg.topic, "qos": str(msg.qos)},
            )
            asyncio.run_coroutine_threadsafe(queue.put(frame), loop)

        def on_disconnect(_c, _u, _f, rc, _props=None) -> None:  # type: ignore[no-untyped-def]
            rc_value = getattr(rc, "value", rc)
            logger.info(
                "mqtt.disconnected",
                device_id=self.profile.id,
                rc=int(rc_value) if isinstance(rc_value, int) else str(rc_value),
            )

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect

        connect_event = threading.Event()

        def runner() -> None:
            try:
                client.connect(host, port, keepalive=60)
            except OSError as exc:
                logger.error(
                    "mqtt.connect_error",
                    device_id=self.profile.id,
                    host=host,
                    port=port,
                    error=str(exc),
                )
                connect_event.set()
                return
            connect_event.set()
            client.loop_forever(retry_first_connection=True)

        thread = threading.Thread(target=runner, name=f"mqtt-{self.profile.id}", daemon=True)
        thread.start()
        connect_event.wait(timeout=10.0)

        try:
            await self._stop_event.wait()
        finally:
            try:
                client.disconnect()
            except Exception:  # noqa: BLE001
                pass
            thread.join(timeout=5.0)
