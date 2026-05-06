"""Simulateur Drager Evita V500.

Expose un serveur TCP qui imite un port serie (RS-232) en mode push.
A chaque client connecte, envoie une trame MEDIBUS ASCII toutes les
`INTERVAL_SEC` secondes :

    <STX>RDATA|FIO2:30|PEEP:5|VT:450|RR:14|PIP:18<ETX>

Format compatible avec le SerialTcpAdapter du bridge (delimitation par
STX/ETX, parsing par le MedibusParser).
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime, timezone

LOGGER = logging.getLogger("drager-evita-v500")

STX = b"\x02"
ETX = b"\x03"


def build_frame() -> bytes:
    fio2 = random.randint(21, 80)
    peep = random.randint(0, 15)
    vt = random.randint(350, 600)
    rr = random.randint(8, 22)
    pip = random.randint(12, 35)
    payload = f"RDATA|FIO2:{fio2}|PEEP:{peep}|VT:{vt}|RR:{rr}|PIP:{pip}"
    return STX + payload.encode("ascii") + ETX


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    LOGGER.info("client connecte : %s", peer)
    interval = float(os.getenv("INTERVAL_SEC", "5"))
    try:
        while not writer.is_closing():
            frame = build_frame()
            writer.write(frame)
            await writer.drain()
            LOGGER.info(
                "%s envoye %d octets : %s",
                datetime.now(tz=timezone.utc).isoformat(),
                len(frame),
                frame[1:-1].decode("ascii"),
            )
            await asyncio.sleep(interval)
    except (ConnectionResetError, BrokenPipeError):
        LOGGER.info("client deconnecte : %s", peer)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass


async def main() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    host = os.getenv("LISTEN_HOST", "0.0.0.0")  # noqa: S104  (conteneur)
    port = int(os.getenv("LISTEN_PORT", "6100"))

    server = await asyncio.start_server(handle_client, host, port)
    LOGGER.info("simulateur Drager Evita V500 ecoute sur %s:%d", host, port)

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
