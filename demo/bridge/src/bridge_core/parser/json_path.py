"""JsonParser : decode un payload JSON et extrait les champs declares.

Le `source_path` du mapping suit une syntaxe minimale : `$.<champ>` ou
`$.<sub>.<champ>` (chemin pointe). C'est suffisant pour les profils
de glucometres et oxymetres en JSON.

Au sprint 7, on pourra remplacer par jsonpath-ng pour une syntaxe
plus expressive. La syntaxe pointee minimaliste evite une dependance
supplementaire pour la demo.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog

from bridge_core.models import Measurement, NormalizedMeasurement
from bridge_core.parser.base import BaseParser, ParseError, parser_registry

if TYPE_CHECKING:
    from bridge_core.adapter.base import RawFrame

logger = structlog.get_logger(__name__)


def _resolve_path(data: Any, path: str) -> Any:
    """Suit un chemin `$.a.b.c` dans un dict imbrique."""
    if not path.startswith("$"):
        return None
    parts = [p for p in path.lstrip("$").split(".") if p]
    cursor: Any = data
    for part in parts:
        if isinstance(cursor, dict) and part in cursor:
            cursor = cursor[part]
        else:
            return None
    return cursor


@parser_registry.register("json")
class JsonParser(BaseParser):
    """Parser JSON avec selecteurs pointes."""

    def parse(self, frame: RawFrame) -> NormalizedMeasurement:
        try:
            text = frame.payload.decode(
                self.profile.parser.encoding or "utf-8", errors="replace"
            )
        except (UnicodeDecodeError, LookupError) as exc:
            raise ParseError(f"decoding: {exc}") from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ParseError(f"json invalid: {exc}") from exc

        measurements: list[Measurement] = []
        for fm in self.profile.mapping.fields:
            raw_value = _resolve_path(data, fm.source_path)
            if raw_value is None:
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                logger.warning(
                    "json.non_numeric",
                    device_id=self.profile.id,
                    loinc=fm.loinc_code,
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
            raise ParseError("aucune mesure mappee trouvee dans le JSON")

        if any(not m.in_plausibility_range for m in measurements):
            out = [m.loinc_code for m in measurements if not m.in_plausibility_range]
            raise ParseError(f"valeur(s) hors plage : {','.join(out)}")

        return NormalizedMeasurement(
            device_id=self.profile.id,
            timestamp_utc=frame.received_at_utc,
            measurements=measurements,
        )
