"""Modeles Pydantic du bridge.

Le profil JSON par dispositif decrit les 3 questions du produit :
1. Quel canal de communication ?    -> ChannelConfig
2. Quelle langue / structuration ?    -> ParserConfig
3. Quelle sortie configuree ?         -> DestinationConfig + MappingConfig

Le DeviceProfile rassemble ces 4 elements et constitue l'unique source
de verite pour brancher un dispositif. Aucun code Python a ecrire pour
ajouter un dispositif : un fichier JSON dans `profiles/` suffit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Note : channel.type, parser.type, destination.type sont des `str` libres
# (pas de Literal) afin que les plugins puissent enregistrer de nouveaux
# types. La validation effective se fait via les registries au moment de
# l'instanciation du pipeline.


# =====================================================================
# Phase 1 : Handshake technique (canal + langue)
# =====================================================================


class ChannelConfig(BaseModel):
    """Canal de communication : TCP/MLLP, MQTT, fichier, RS-232 ou autre."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(
        ..., description="Type de canal supporte par un Adapter enregistre."
    )
    # Champs specifiques au type, valides par chaque Adapter concret.
    host: str | None = None
    port: int | None = None
    topic: str | None = None
    directory: str | None = None
    file_pattern: str | None = None
    baudrate: int | None = None
    bits: str | None = None  # "8E1", "8N1" (informatif)


class ParserConfig(BaseModel):
    """Langue / structuration des donnees emises par le dispositif."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(
        ..., description="Type de format reconnu par un Parser enregistre."
    )
    message_type: str | None = None  # ORU_R01 pour HL7v2 etc.
    encoding: str = "utf-8"
    schema_path: str | None = None  # chemin XSD/JSON Schema optionnel


# =====================================================================
# Phase 2 : Configuration metier (mapping + sortie)
# =====================================================================


class PlausibilityRange(BaseModel):
    """Plage de plausibilite clinique pour mise en quarantaine."""

    model_config = ConfigDict(extra="forbid")

    min: float
    max: float


class FieldMapping(BaseModel):
    """Mapping d'un champ source vers une mesure normalisee LOINC.

    Le `source_path` est un selecteur dependant du type de Parser.
    Pour HL7v2 : chemin de segment OBX (ex. "OBX[1]/observation_value").
    Pour JSON : JSONPath (ex. "$.spo2").
    Pour XML : XPath (ex. "/Result/SpO2").
    """

    model_config = ConfigDict(extra="forbid")

    source_path: str = Field(..., description="Selecteur du champ dans la trame brute.")
    loinc_code: str = Field(..., description="Code LOINC de la mesure.")
    loinc_display: str = Field(..., description="Libelle humain LOINC.")
    unit: str = Field(..., description="Unite humaine (ex. '%', 'bpm', 'mmHg').")
    ucum_code: str = Field(..., description="Code UCUM normalise pour FHIR.")
    plausibility: PlausibilityRange | None = None


class MappingConfig(BaseModel):
    """Ensemble des mappings d'un dispositif vers des codes LOINC."""

    model_config = ConfigDict(extra="forbid")

    fields: list[FieldMapping] = Field(default_factory=list)


class DestinationConfig(BaseModel):
    """Cible de publication : HAPI FHIR, eHealthBox, hub, etc."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(
        ..., description="Type de transport enregistre."
    )
    url: str | None = None
    timeout_seconds: float = 10.0
    retry_max: int = 3
    mtls_enabled: bool = False
    mtls_cert: str | None = None
    mtls_key: str | None = None


class DeviceMetadata(BaseModel):
    """Metadonnees du dispositif : fabricant, modele, identifiant FHIR Device."""

    model_config = ConfigDict(extra="allow")

    manufacturer: str
    model_number: str
    serial_number: str | None = None
    udi: str | None = None  # Unique Device Identifier (FDA/EUDAMED)


# =====================================================================
# Profil dispositif complet
# =====================================================================


class DeviceProfile(BaseModel):
    """Profil JSON complet d'un dispositif.

    Une instance de ce modele = un fichier dans `profiles/<id>.json`.
    Le ProfileLoader le charge a l'amorcage et le valide. Toute erreur
    de schema rejette le profil avec un log clair.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Identifiant stable, kebab-case recommande.")
    name: str = Field(..., description="Libelle humain pour le dashboard.")
    enabled: bool = True
    channel: ChannelConfig
    parser: ParserConfig
    mapping: MappingConfig
    destination: DestinationConfig
    device_metadata: DeviceMetadata


# =====================================================================
# Modele interne normalise (sortie du Parser)
# =====================================================================


class NormalizedMeasurement(BaseModel):
    """Mesure normalisee produite par le Parser.

    C'est le pivot interne : le Mapper la transforme ensuite en ressource
    FHIR Observation. Aucune valeur clinique n'est jamais journalisee
    par le bridge (regle de minimisation).
    """

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(..., description="ID du DeviceProfile source.")
    timestamp_utc: datetime = Field(..., description="Horodatage UTC d'arrivee.")
    measurements: list[Measurement] = Field(default_factory=list)
    raw_payload_hash: str | None = Field(
        None, description="Hash SHA-256 du payload brut, pour tracabilite."
    )


class Measurement(BaseModel):
    """Une grandeur mesuree, codifiee LOINC, avec valeur et unite."""

    model_config = ConfigDict(extra="forbid")

    loinc_code: str
    loinc_display: str
    value: float
    unit: str
    ucum_code: str
    in_plausibility_range: bool = True


NormalizedMeasurement.model_rebuild()


# =====================================================================
# Statut de transmission
# =====================================================================


class TransmissionStatus(BaseModel):
    """Statut d'une transmission vers la destination."""

    model_config = ConfigDict(extra="allow")

    device_id: str
    timestamp_utc: datetime
    success: bool
    http_status: int | None = None
    fhir_resource_ids: list[str] = Field(default_factory=list)
    retry_count: int = 0
    error_message: str | None = None  # technique, sans donnee patient


# =====================================================================
# Etat d'un equipement (pour le dashboard)
# =====================================================================


class DeviceStatus(BaseModel):
    """Etat operationnel d'un equipement, exposable par le dashboard.

    Aucune valeur clinique du patient n'est presente ici.
    """

    model_config = ConfigDict(extra="forbid")

    device_id: str
    name: str
    color: Literal["green", "amber", "red", "gray"] = "gray"
    last_seen_utc: datetime | None = None
    messages_total: int = 0
    messages_in_quarantine: int = 0
    indicative_context: str | None = None  # ex. "n'emet plus depuis 5 min"


# =====================================================================
# Manifeste plugin
# =====================================================================


class PluginManifest(BaseModel):
    """Manifeste TOML d'un plugin communautaire."""

    model_config = ConfigDict(extra="allow")

    name: str
    version: str
    layer: str  # "adapter", "parser", "mapper", "adapter+parser", etc.
    description: str = ""
    loinc_codes: list[str] = Field(default_factory=list)
    entrypoints: dict[str, Any] = Field(default_factory=dict)
