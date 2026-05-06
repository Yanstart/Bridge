"""Simulateur Philips IntelliVue MX450.

Genere periodiquement un message HL7 v2 ORU^R01 contenant les 4 mesures
vitales : SpO2, frequence cardiaque, pression arterielle systolique et
diastolique. Encadre le message dans des delimiteurs MLLP et l'envoie
au bridge sur TCP.

Configuration via variables d'environnement :
- BRIDGE_HOST   (default: bridge)
- BRIDGE_PORT   (default: 2575)
- INTERVAL_SEC  (default: 30)
- DEVICE_ID     (default: MX450-DEMO-001)
- ROOM_ID       (default: ROOM-12)
- LOG_LEVEL     (default: INFO)
"""

from __future__ import annotations

import logging
import os
import random
import socket
import sys
import time
from datetime import datetime, timezone

LOGGER = logging.getLogger("philips-mx450")

# Delimiteurs MLLP
MLLP_START = b"\x0b"
MLLP_END = b"\x1c\x0d"


def build_message(device_id: str, room_id: str, control_id: str) -> str:
    """Construit un message HL7 v2 ORU^R01 plausible.

    Les valeurs sont aleatoires mais physiologiquement plausibles :
    - SpO2 : 92 a 99 %
    - FC   : 55 a 95 bpm
    - PAS  : 105 a 135 mmHg
    - PAD  : 65 a 90 mmHg
    """
    spo2 = random.randint(92, 99)
    hr = random.randint(55, 95)
    sbp = random.randint(105, 135)
    dbp = random.randint(65, 90)

    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
    sep = "|"

    msh = sep.join(
        [
            "MSH",
            "^~\\&",
            "MX450",  # sending application
            "EPHEC-DEMO",  # sending facility
            "BRIDGE",  # receiving application
            "EPHEC-DEMO",  # receiving facility
            ts,  # timestamp
            "",  # security
            "ORU^R01",  # message type
            control_id,
            "P",  # processing id (P=production)
            "2.5",  # version
        ]
    )
    pid = sep.join(
        [
            "PID",
            "1",
            "",
            f"{room_id}^^^EPHEC^MR",  # patient identifier (room based, no PII)
            "",
            "DEMO^PATIENT",  # nom symbolique non identifiant
            "",
            "",
            "",
        ]
    )
    pv1 = sep.join(["PV1", "1", "I", room_id])  # I = inpatient
    obr = sep.join(
        [
            "OBR",
            "1",
            "",
            f"{control_id}^MX450",  # filler order number
            "VITALS^Vital signs^L",
            "",
            "",
            ts,
        ]
    )

    obx_lines = []
    for idx, (loinc, name, value, unit) in enumerate(
        [
            ("59408-5", "Oxygen saturation in Arterial blood by Pulse oximetry", spo2, "%"),
            ("8867-4", "Heart rate", hr, "bpm"),
            ("8480-6", "Systolic blood pressure", sbp, "mmHg"),
            ("8462-4", "Diastolic blood pressure", dbp, "mmHg"),
        ],
        start=1,
    ):
        obx_lines.append(
            sep.join(
                [
                    "OBX",
                    str(idx),
                    "NM",  # numeric
                    f"{loinc}^{name}^LN",
                    "",
                    str(value),
                    unit,
                    "",
                    "",
                    "",
                    "F",  # final result
                ]
            )
        )

    segments = [msh, pid, pv1, obr, *obx_lines]
    return "\r".join(segments) + "\r"


def send_one(host: str, port: int, message: str) -> bool:
    """Envoie un message MLLP au bridge. Retourne True si ACK recu."""
    payload = MLLP_START + message.encode("utf-8") + MLLP_END
    try:
        with socket.create_connection((host, port), timeout=5.0) as sock:
            sock.sendall(payload)
            data = sock.recv(4096)
            if not data:
                return False
            ack_text = data.decode("utf-8", errors="replace")
            ok = "MSA|AA" in ack_text
            return ok
    except OSError as exc:
        LOGGER.warning("connexion impossible vers %s:%s : %s", host, port, exc)
        return False


def main() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    host = os.getenv("BRIDGE_HOST", "bridge")
    port = int(os.getenv("BRIDGE_PORT", "2575"))
    interval = float(os.getenv("INTERVAL_SEC", "30"))
    device_id = os.getenv("DEVICE_ID", "MX450-DEMO-001")
    room_id = os.getenv("ROOM_ID", "ROOM-12")

    LOGGER.info(
        "demarrage simulateur Philips MX450 -> %s:%s, intervalle %ss",
        host,
        port,
        interval,
    )

    counter = 0
    while True:
        counter += 1
        control_id = f"MX450-{int(time.time())}-{counter:04d}"
        message = build_message(device_id, room_id, control_id)
        ok = send_one(host, port, message)
        if ok:
            LOGGER.info("trame %s envoyee, ACK recu", control_id)
        else:
            LOGGER.warning("trame %s : pas d'ACK ou erreur reseau", control_id)
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
