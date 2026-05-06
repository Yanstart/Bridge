"""Parser CSV pour capteur de temperature corporelle.

Plugin exemple. Lit un fichier CSV avec deux colonnes : `timestamp_iso`
et `temperature_celsius`. Pour chaque ligne, produit une mesure
LOINC 8310-5 (Body temperature). Si plusieurs lignes sont presentes,
seule la derniere est retenue (pour rester aligne sur le pattern
"une mesure par fichier").

Demontre comment un tiers peut etendre le bridge sans modifier le
code coeur : le decorateur @parser_registry.register fait suffit.
"""

from __future__ import annotations

import csv
import io

from bridge_core.models import Measurement, NormalizedMeasurement
from bridge_core.parser.base import BaseParser, ParseError, parser_registry


@parser_registry.register("temperature_csv")
class TemperatureCsvParser(BaseParser):
    """Parser CSV ultra simple pour la demonstration."""

    def parse(self, frame):  # type: ignore[no-untyped-def]
        try:
            text = frame.payload.decode(
                self.profile.parser.encoding or "utf-8", errors="replace"
            )
        except (UnicodeDecodeError, LookupError) as exc:
            raise ParseError(f"decoding: {exc}") from exc

        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            raise ParseError("CSV vide")

        last = rows[-1]
        try:
            value = float(last.get("temperature_celsius", ""))
        except (TypeError, ValueError) as exc:
            raise ParseError("temperature_celsius non numerique") from exc

        # Verifier la plage de plausibilite si declaree dans le profil
        in_range = True
        for fm in self.profile.mapping.fields:
            if fm.loinc_code == "8310-5" and fm.plausibility:
                in_range = fm.plausibility.min <= value <= fm.plausibility.max
                break
        if not in_range:
            raise ParseError(f"temperature {value} hors plage de plausibilite")

        measurement = Measurement(
            loinc_code="8310-5",
            loinc_display="Body temperature",
            value=value,
            unit="Cel",
            ucum_code="Cel",
            in_plausibility_range=True,
        )

        return NormalizedMeasurement(
            device_id=self.profile.id,
            timestamp_utc=frame.received_at_utc,
            measurements=[measurement],
        )
