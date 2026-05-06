"""FhirBundleMapper : transforme une mesure normalisee en Bundle FHIR R4.

Genere un Bundle de type `transaction` avec :
- 1 ressource Patient (identifiant simule par room/device, no PII)
- 1 ressource Device (avec manufacturer, model, UDI)
- N ressources Observation (une par mesure dans la NormalizedMeasurement)

Aucune valeur clinique n'est conservee dans les logs : le bridge passe
le Bundle au Transport puis l'oublie.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from bridge_core.mapper.base import BaseMapper, mapper_registry

if TYPE_CHECKING:
    from bridge_core.models import NormalizedMeasurement


@mapper_registry.register("fhir_bundle")
class FhirBundleMapper(BaseMapper):
    """Construit un Bundle FHIR R4 transaction conforme."""

    def map(self, normalized: NormalizedMeasurement) -> dict[str, Any]:
        device_id = self.profile.id
        meta = self.profile.device_metadata

        patient_id = f"demo-{device_id}"
        device_resource_id = f"device-{device_id}"

        timestamp_iso = normalized.timestamp_utc.isoformat()

        entries: list[dict[str, Any]] = []

        # --- Patient (identifiant simule, no PII) ---------------------
        entries.append(
            {
                "fullUrl": f"urn:uuid:patient-{patient_id}",
                "resource": {
                    "resourceType": "Patient",
                    "id": patient_id,
                    "identifier": [
                        {
                            "system": "urn:bridge:demo:device-room",
                            "value": patient_id,
                        }
                    ],
                },
                "request": {"method": "PUT", "url": f"Patient/{patient_id}"},
            }
        )

        # --- Device ---------------------------------------------------
        device_resource: dict[str, Any] = {
            "resourceType": "Device",
            "id": device_resource_id,
            "manufacturer": meta.manufacturer,
            "modelNumber": meta.model_number,
        }
        if meta.serial_number:
            device_resource["serialNumber"] = meta.serial_number
        if meta.udi:
            device_resource["udiCarrier"] = [{"deviceIdentifier": meta.udi}]
        entries.append(
            {
                "fullUrl": f"urn:uuid:{device_resource_id}",
                "resource": device_resource,
                "request": {"method": "PUT", "url": f"Device/{device_resource_id}"},
            }
        )

        # --- Observations (1 par mesure) ------------------------------
        for measurement in normalized.measurements:
            obs_uuid = str(uuid.uuid4())
            obs_resource = {
                "resourceType": "Observation",
                "status": "final",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": measurement.loinc_code,
                            "display": measurement.loinc_display,
                        }
                    ]
                },
                "subject": {"reference": f"Patient/{patient_id}"},
                "device": {"reference": f"Device/{device_resource_id}"},
                "effectiveDateTime": timestamp_iso,
                "valueQuantity": {
                    "value": measurement.value,
                    "unit": measurement.unit,
                    "system": "http://unitsofmeasure.org",
                    "code": measurement.ucum_code,
                },
            }
            entries.append(
                {
                    "fullUrl": f"urn:uuid:{obs_uuid}",
                    "resource": obs_resource,
                    "request": {"method": "POST", "url": "Observation"},
                }
            )

        return {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": entries,
        }
