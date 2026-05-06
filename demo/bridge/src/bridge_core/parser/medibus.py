"""MedibusParser : decode des trames ASCII MEDIBUS simplifiees.

Format retenu pour la demo (inspire du MEDIBUS legacy Drager) :
    RDATA|FIO2:30|PEEP:5|VT:450|RR:14|PIP:18

Les segments commencent par un type de message (`RDATA` = realtime data),
suivi de paires `cle:valeur` separees par `|`. Les delimiteurs STX/ETX
sont retires en amont par l'Adapter SerialTcp.

La cle MEDIBUS est mise en correspondance avec un code LOINC via le
champ `source_path` du profil, sous la forme `MEDIBUS[<key>]/value`.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog

from bridge_core.models import Measurement, NormalizedMeasurement
from bridge_core.parser.base import BaseParser, ParseError, parser_registry

if TYPE_CHECKING:
    from bridge_core.adapter.base import RawFrame

logger = structlog.get_logger(__name__)

_KEY_RE = re.compile(r"MEDIBUS\[(\w+)\]")


@parser_registry.register("medibus_ascii")
class MedibusParser(BaseParser):
    """Parser MEDIBUS ASCII simplifie."""

    def parse(self, frame: RawFrame) -> NormalizedMeasurement:
        try:
            text = frame.payload.decode(
                self.profile.parser.encoding or "ascii", errors="replace"
            ).strip()
        except (UnicodeDecodeError, LookupError) as exc:
            raise ParseError(f"decoding: {exc}") from exc

        parts = text.split("|")
        if not parts or not parts[0]:
            raise ParseError("trame vide")

        msg_type = parts[0].strip().upper()
        if msg_type != "RDATA":
            raise ParseError(f"type de message non supporte: {msg_type}")

        # Parse les paires cle:valeur
        kv: dict[str, str] = {}
        for token in parts[1:]:
            if ":" not in token:
                continue
            key, value = token.split(":", 1)
            kv[key.strip().upper()] = value.strip()

        if not kv:
            raise ParseError("aucune paire cle:valeur dans la trame MEDIBUS")

        measurements: list[Measurement] = []
        for fm in self.profile.mapping.fields:
            match = _KEY_RE.search(fm.source_path)
            if not match:
                continue
            target_key = match.group(1).upper()
            raw_value = kv.get(target_key)
            if raw_value is None:
                continue
            try:
                value = float(raw_value)
            except ValueError:
                logger.warning(
                    "medibus.non_numeric",
                    device_id=self.profile.id,
                    key=target_key,
                )
                continue

            in_range = True
            if fm.plausibility is not None:
                in_range = fm.plausibility.min <= value <= fm.plausibility.max

            measurements.append(
                Measurement(
                    loinc_code=fm.loinc_code,
                    loinc_display=fm.loinc_display,
                    value=value,
                    unit=fm.unit,
                    ucum_code=fm.ucum_code,
                    in_plausibility_range=in_range,
                )
            )

        if not measurements:
            raise ParseError("aucune mesure mappee dans la trame MEDIBUS")

        if any(not m.in_plausibility_range for m in measurements):
            out = [m.loinc_code for m in measurements if not m.in_plausibility_range]
            raise ParseError(f"valeur(s) hors plage : {','.join(out)}")

        return NormalizedMeasurement(
            device_id=self.profile.id,
            timestamp_utc=frame.received_at_utc,
            measurements=measurements,
        )
