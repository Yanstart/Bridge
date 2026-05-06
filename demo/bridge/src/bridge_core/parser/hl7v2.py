"""Hl7v2Parser : decodage HL7 v2 ORU^R01 (et variantes).

Le parser parcourt les segments OBX du message, extrait l'identifiant
d'observation (champ OBX-3, format `code^display^system`) et compare
avec les codes LOINC declares dans `profile.mapping.fields`. Pour
chaque champ trouve, il produit une `Measurement` avec la valeur du
champ OBX-5 et l'unite du champ OBX-6.

Format de `source_path` reconnu :
    "OBX[loinc=<code>]/value"  -> OBX dont OBX-3 a le code LOINC.

Pour la demo, ce format suffit pour les 4 grandeurs vitales du
moniteur Philips. Le sprint 7 etendra a JSONPath et XPath pour les
autres formats.
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

# Regex extracteur de code LOINC dans la source_path
_LOINC_RE = re.compile(r"OBX\[loinc=([\w-]+)\]")


@parser_registry.register("hl7v2")
class Hl7v2Parser(BaseParser):
    """Decodeur HL7 v2 simple, base sur split par `\\r` et `|`."""

    def parse(self, frame: RawFrame) -> NormalizedMeasurement:
        try:
            text = frame.payload.decode(
                self.profile.parser.encoding or "utf-8", errors="replace"
            )
        except (UnicodeDecodeError, LookupError) as exc:
            raise ParseError(f"decoding: {exc}") from exc

        segments = [s for s in text.split("\r") if s.strip()]
        if not segments or not segments[0].startswith("MSH"):
            raise ParseError("MSH segment missing or not first")

        # Recuperer separateur de champ depuis MSH (toujours `|` mais on lit
        # tout de meme par robustesse).
        msh = segments[0]
        field_sep = msh[3] if len(msh) > 3 else "|"

        # Extraire les OBX en dictionnaire {loinc_code: (value_str, unit_str)}
        obx_by_loinc: dict[str, tuple[str, str]] = {}
        for seg in segments:
            if not seg.startswith("OBX"):
                continue
            fields = seg.split(field_sep)
            if len(fields) < 6:
                continue
            obs_id = fields[3]   # OBX-3 : identifier (code^display^system)
            value = fields[5]    # OBX-5 : observation value
            units = fields[6] if len(fields) > 6 else ""
            loinc = obs_id.split("^")[0].strip() if obs_id else ""
            if not loinc:
                continue
            obx_by_loinc[loinc] = (value, units)

        # Construire les Measurement selon le mapping du profil
        measurements: list[Measurement] = []
        for fm in self.profile.mapping.fields:
            match = _LOINC_RE.search(fm.source_path)
            if not match:
                continue
            target_loinc = match.group(1)
            if target_loinc != fm.loinc_code:
                continue
            entry = obx_by_loinc.get(target_loinc)
            if entry is None:
                continue
            value_str, _unit = entry
            try:
                value = float(value_str)
            except ValueError:
                # Ignore les valeurs non numeriques (pas de log de la valeur)
                logger.warning(
                    "hl7v2.non_numeric_value",
                    device_id=self.profile.id,
                    loinc=target_loinc,
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
            raise ParseError("aucune mesure mappee trouvee dans le message")

        # Si une mesure est hors plage, on signale via ParseError pour
        # que le BridgeCore mette en quarantaine.
        if any(not m.in_plausibility_range for m in measurements):
            out_of_range = [m.loinc_code for m in measurements if not m.in_plausibility_range]
            raise ParseError(
                f"valeur(s) hors plage de plausibilite : {','.join(out_of_range)}"
            )

        return NormalizedMeasurement(
            device_id=self.profile.id,
            timestamp_utc=frame.received_at_utc,
            measurements=measurements,
        )
