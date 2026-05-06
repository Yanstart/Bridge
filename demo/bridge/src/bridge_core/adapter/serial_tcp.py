"""SerialTcpAdapter : RS-232 simule via un port TCP.

Un vrai pseudo-tty (`socat`) expose un port serie virtuel sous forme de
port TCP. Cet Adapter se comporte en client TCP : il se connecte au
simulateur, lit en streaming, et decoupe les trames a partir des
delimiteurs declares dans le profil (par defaut MEDIBUS : STX/ETX).
"""

from __future__ import annotations

import asyncio

import structlog

from bridge_core.adapter.base import BaseAdapter, RawFrame, adapter_registry

logger = structlog.get_logger(__name__)

STX = 0x02
ETX = 0x03


@adapter_registry.register("serial_tcp")
class SerialTcpAdapter(BaseAdapter):
    """Client TCP qui consomme un flux serie expose via socat."""

    async def _run(self, queue: asyncio.Queue[RawFrame]) -> None:
        host = self.profile.channel.host or "sim-drager"
        port = self.profile.channel.port or 6100

        backoff = 1.0
        while not self._stop_event.is_set():
            try:
                reader, writer = await asyncio.open_connection(host, port)
            except OSError as exc:
                logger.warning(
                    "serial_tcp.connect_error",
                    device_id=self.profile.id,
                    host=host,
                    port=port,
                    error=str(exc),
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                continue

            backoff = 1.0
            logger.info(
                "serial_tcp.connected",
                device_id=self.profile.id,
                host=host,
                port=port,
            )
            try:
                buffer = bytearray()
                while not self._stop_event.is_set():
                    chunk = await reader.read(1024)
                    if not chunk:
                        break
                    buffer.extend(chunk)
                    while True:
                        start = buffer.find(STX)
                        if start < 0:
                            buffer.clear()
                            break
                        end = buffer.find(ETX, start + 1)
                        if end < 0:
                            if start > 0:
                                del buffer[:start]
                            break
                        payload = bytes(buffer[start + 1 : end])
                        del buffer[: end + 1]
                        if payload:
                            frame = self._make_frame(
                                payload,
                                metadata={"transport": "serial_tcp"},
                            )
                            await queue.put(frame)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "serial_tcp.io_error",
                    device_id=self.profile.id,
                    error=str(exc),
                )
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:  # noqa: BLE001
                    pass
                logger.info("serial_tcp.disconnected", device_id=self.profile.id)
                if not self._stop_event.is_set():
                    await asyncio.sleep(backoff)
