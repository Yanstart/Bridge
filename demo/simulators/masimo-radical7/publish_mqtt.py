"""Simulateur Masimo Radical-7.

Publie un message JSON sur MQTT toutes les `INTERVAL_SEC` secondes
contenant SpO2, frequence cardiaque (PR) et indice de perfusion (PI).

Le canal Bluetooth Low Energy reel est ici simule via MQTT pour rester
cote conteneur Docker. La semantique du payload reste identique : un
objet JSON plat avec les grandeurs vitales.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt_client

LOGGER = logging.getLogger("masimo-radical7")


def build_payload() -> dict[str, object]:
    return {
        "device": "masimo-radical7",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "spo2": random.randint(94, 99),
        "pr": random.randint(58, 92),
        "pi": round(random.uniform(2.0, 8.0), 1),
    }


def main() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    host = os.getenv("MQTT_HOST", "mqtt")
    port = int(os.getenv("MQTT_PORT", "1883"))
    topic = os.getenv("MQTT_TOPIC", "devices/masimo-radical7/spo2")
    interval = float(os.getenv("INTERVAL_SEC", "8"))

    client = mqtt_client.Client(
        mqtt_client.CallbackAPIVersion.VERSION2,
        client_id="sim-masimo-radical7",
    )
    client.connect(host, port, keepalive=60)
    client.loop_start()
    LOGGER.info("connecte au broker %s:%s, topic %s", host, port, topic)

    try:
        while True:
            payload = build_payload()
            data = json.dumps(payload).encode("utf-8")
            info = client.publish(topic, data, qos=1)
            info.wait_for_publish(timeout=5.0)
            LOGGER.info("publie sur %s : %s", topic, payload)
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
