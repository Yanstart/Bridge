"""Simulateur Welch Allyn CP150 (export ECG).

Depose periodiquement un fichier JSON dans `/drop`. Le fichier contient
un resume d'etude ECG : frequence cardiaque, intervalle PR, intervalle
QT. L'export reel du CP150 est en SCP-ECG binaire ; le format JSON
retenu pour la demo facilite la lecture par le bridge sans dependance
sur python-ecg-scp.

Pattern d'ecriture atomique : ecrire dans `*.json.tmp`, fsync, puis
renommer en `*.json` pour eviter les lectures partielles cote bridge.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger("welchallyn-cp150")


def build_payload() -> dict[str, object]:
    return {
        "device": "welchallyn-cp150",
        "study_id": f"ECG-{int(time.time())}",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "heart_rate": random.randint(58, 92),
        "pr_interval_ms": random.randint(120, 200),
        "qt_interval_ms": random.randint(360, 440),
    }


def write_atomically(directory: Path, payload: dict[str, object]) -> Path:
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"welchallyn-{timestamp}.json"
    final_path = directory / filename
    tmp_path = directory / f"{filename}.tmp"
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(final_path)
    return final_path


def main() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    drop_dir = Path(os.getenv("DROP_DIR", "/drop"))
    interval = float(os.getenv("INTERVAL_SEC", "20"))
    drop_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info("simulateur Welch Allyn CP150, depose dans %s toutes les %ss", drop_dir, interval)

    try:
        while True:
            payload = build_payload()
            path = write_atomically(drop_dir, payload)
            LOGGER.info("fichier depose : %s", path.name)
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
