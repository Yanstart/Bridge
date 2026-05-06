# Bridge Core

Cœur Python du middleware IoT Edge Bridge. Sert de passerelle entre les dispositifs médicaux Legacy et la plateforme cible (HAPI FHIR ou DPI hospitalier).

## Structure

```
bridge/
├── pyproject.toml
├── Dockerfile
├── README.md
└── src/
    └── bridge_core/
        ├── __init__.py
        └── main.py        # entry point FastAPI
```

Au sprint 2, on ajoutera :

```
bridge_core/
├── adapter/        # drivers d'entrée (TCP MLLP, MQTT, file-watcher, série)
├── parser/         # décodeurs (HL7v2, JSON, XML, MEDIBUS)
├── mapper/         # codification LOINC + génération FHIR R4
├── transport/      # client httpx + retry + fallback SQLite
├── dashboard/      # routes FastAPI + templates HTMX
├── plugin/         # plugin manager
├── persistence/    # SQLite WAL chiffrée
└── config/         # loaders profils JSON et plugin.toml
```

## Lancement local (dev, hors Docker)

```bash
pip install -e .
bridge-server
```

L'API est exposée sur `http://localhost:8080`.

## Endpoints

| Route | Description |
|---|---|
| `GET /` | Page d'accueil minimale |
| `GET /health` | Healthcheck JSON, statut de chaque composant |

Le dashboard et les endpoints de configuration arriveront au sprint 5.

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `BRIDGE_PORT` | `8080` | Port d'écoute Uvicorn |
| `HAPI_FHIR_URL` | `http://hapi:8080/fhir` | URL du serveur FHIR cible |
| `MQTT_HOST` | `mqtt` | Hôte du broker MQTT |
| `LOG_LEVEL` | `info` | Niveau de log Uvicorn |
