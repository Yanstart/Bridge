"""TcpMllpAdapter : ecoute MLLP (Minimal Lower Layer Protocol) HL7 v2.

MLLP encadre chaque message HL7 v2 entre :
- VT (0x0B) au debut
- FS + CR (0x1C 0x0D) a la fin

L'Adapter ecoute un port TCP, accepte plusieurs connexions concurrentes,
extrait les messages MLLP et les pousse en RawFrame.
"""

from __future__ import annotations

import asyncio

import structlog

from bridge_core.adapter.base import BaseAdapter, RawFrame, adapter_registry

logger = structlog.get_logger(__name__)

MLLP_START = 0x0B  # VT, debut de message
MLLP_END_1 = 0x1C  # FS, fin de message
MLLP_END_2 = 0x0D  # CR, fin de message


@adapter_registry.register("tcp_mllp")
class TcpMllpAdapter(BaseAdapter):
    """Listener MLLP sur TCP pour HL7 v2.

    Le port et l'host sont lus depuis `profile.channel`. Plusieurs
    clients peuvent etre connectes simultanement (ex. plusieurs lits
    monitor sur le meme moniteur ou plusieurs sources en redondance).
    """

    async def _run(self, queue: asyncio.Queue[RawFrame]) -> None:
        host = self.profile.channel.host or "0.0.0.0"  # noqa: S104
        port = self.profile.channel.port or 2575

        async def handle_client(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            peer = writer.get_extra_info("peername")
            logger.info(
                "tcp_mllp.client_connected",
                device_id=self.profile.id,
                peer=str(peer),
            )
            try:
                async for message in self._read_mllp_messages(reader):
                    frame = self._make_frame(
                        message,
                        metadata={"peer": str(peer), "transport": "tcp_mllp"},
                    )
                    await queue.put(frame)
                    # Acquitter la trame avec un ACK MLLP minimal (MSH ACK)
                    ack = self._build_ack(message)
                    if ack is not None:
                        writer.write(ack)
                        await writer.drain()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "tcp_mllp.client_error",
                    device_id=self.profile.id,
                    error=str(exc),
                )
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:  # noqa: BLE001
                    pass
                logger.info(
                    "tcp_mllp.client_disconnected",
                    device_id=self.profile.id,
                    peer=str(peer),
                )

        server = await asyncio.start_server(handle_client, host=host, port=port)
        logger.info(
            "tcp_mllp.listening",
            device_id=self.profile.id,
            host=host,
            port=port,
        )

        try:
            async with server:
                await self._stop_event.wait()
        finally:
            server.close()
            try:
                await server.wait_closed()
            except Exception:  # noqa: BLE001
                pass

    async def _read_mllp_messages(
        self, reader: asyncio.StreamReader
    ):  # AsyncIterator[bytes]
        """Generateur asynchrone qui yield chaque message MLLP complet."""
        buffer = bytearray()
        while not self._stop_event.is_set():
            chunk = await reader.read(4096)
            if not chunk:
                break  # client deconnecte
            buffer.extend(chunk)

            while True:
                start = buffer.find(MLLP_START)
                if start < 0:
                    buffer.clear()
                    break
                end = self._find_end(buffer, start + 1)
                if end < 0:
                    if start > 0:
                        # Conserver a partir du debut detecte
                        del buffer[:start]
                    break
                payload = bytes(buffer[start + 1 : end])
                # Avancer le buffer apres le marqueur de fin (2 octets)
                del buffer[: end + 2]
                if payload:
                    yield payload

    @staticmethod
    def _find_end(buffer: bytearray, offset: int) -> int:
        """Cherche FS+CR a partir d'offset, retourne l'index de FS, ou -1."""
        i = offset
        while i < len(buffer) - 1:
            if buffer[i] == MLLP_END_1 and buffer[i + 1] == MLLP_END_2:
                return i
            i += 1
        return -1

    @staticmethod
    def _build_ack(message: bytes) -> bytes | None:
        """Construit un ACK MLLP minimal pour le message recu.

        On garde le control_id et l'application source / destination du
        MSH d'origine. Le message ACK est un MSH + MSA simples.
        """
        try:
            text = message.decode("utf-8", errors="replace")
            first_line = text.split("\r")[0]
            fields = first_line.split("|")
            if len(fields) < 10:
                return None
            sending_app = fields[2]
            sending_facility = fields[3]
            receiving_app = fields[4]
            receiving_facility = fields[5]
            timestamp = fields[6]
            msg_control_id = fields[9]
            ack_msh = (
                f"MSH|^~\\&|{receiving_app}|{receiving_facility}|"
                f"{sending_app}|{sending_facility}|{timestamp}||"
                f"ACK|{msg_control_id}|P|2.5"
            )
            ack_msa = f"MSA|AA|{msg_control_id}"
            ack_payload = (ack_msh + "\r" + ack_msa + "\r").encode("utf-8")
            return bytes([MLLP_START]) + ack_payload + bytes([MLLP_END_1, MLLP_END_2])
        except (UnicodeDecodeError, IndexError):
            return None
