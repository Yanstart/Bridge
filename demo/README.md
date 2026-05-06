# Démo IoT Edge Bridge

Démonstration dockerisée du middleware. Tout tourne en local, aucun accès Internet requis pendant la démo.

## Aperçu

```
                          docker compose up
                                 |
   ┌─────────────────────────────┼─────────────────────────────┐
   │                             │                             │
   v                             v                             v
sim-philips         sim-masimo / sim-welchallyn /         hapi (FHIR)
(TCP MLLP)              sim-drager                       <─ POST Bundle
   │                             │                             ^
   └────────────┐  ┌─────────────┘                              │
                v  v                                            │
              bridge ──────────── 4 couches ──────────── transport
              :8080 (dashboard)
              :2575 (MLLP)
                |
                v
          file-watcher (drop/)
                +
          plugin example-temperature
```

## Prérequis

- **Docker Desktop** ou Docker Engine 24+ avec Docker Compose 2.20+
- 8 Go de RAM disponibles
- 5 Go d'espace disque
- Ports libres : `8080` (dashboard), `8081` (HAPI), `1883` (MQTT), `2575` (MLLP)

## Lancement

```bash
cd demo/
docker compose up -d
```

Les services démarrent dans cet ordre :

| Ordre | Service | Rôle |
|---|---|---|
| 1 | `mqtt` | broker eclipse-mosquitto |
| 2 | `hapi` | HAPI FHIR Server (healthcheck pendant ~30 s) |
| 3 | `bridge` | cœur middleware Python (attend HAPI healthy) |
| 4 | `sim-philips` | TCP MLLP HL7v2 ORU^R01 toutes les 10 s |
| 4 | `sim-masimo` | MQTT JSON sur `devices/masimo-radical7/spo2` toutes les 8 s |
| 4 | `sim-welchallyn` | dépose un `welchallyn-*.json` dans `volumes/drop/` toutes les 20 s |
| 4 | `sim-drager` | TCP port 6100, MEDIBUS ASCII toutes les 5 s |

## Vérification

| URL | Service | Réponse attendue |
|---|---|---|
| http://localhost:8080/ | Dashboard | Vue d'ensemble HTML, 4 cartes équipement |
| http://localhost:8080/health | Bridge healthcheck | JSON registries + status ok |
| http://localhost:8080/api/devices | Statuts | 4 ou 5 équipements (avec plugin) |
| http://localhost:8080/api/queue | File de repli | `{enabled: true, count: 0, ...}` |
| http://localhost:8081/fhir/metadata | HAPI FHIR | CapabilityStatement |
| http://localhost:8081/fhir/Observation | Observations | Bundle de ressources publiées |

## Scénario de démonstration (5 min)

1. **Ouvrir le dashboard** : http://localhost:8080/
   - Les 4 équipements apparaissent en gris (gray) puis passent en vert (green) au fur et à mesure des premiers messages.
2. **Observer le flux temps réel** : la barre WebSocket en haut à droite indique « temps réel ». Des toasts apparaissent à chaque message traité.
3. **Cliquer sur Philips IntelliVue MX450** : page détail, profil + mappings LOINC + timeline.
4. **Ouvrir l'URL HAPI** : http://localhost:8081/fhir/Observation. Les Observations FHIR R4 publiées sont visibles.
5. **Déposer un fichier de température** (plugin) :
   ```bash
   echo "timestamp_iso,temperature_celsius
   2026-05-05T12:00:00Z,37.2" > volumes/drop/temperature-test-001.csv
   ```
   Le plugin `example-temperature` traite le fichier, publie une Observation LOINC 8310-5.
6. **Forcer une anomalie** :
   ```bash
   echo "timestamp_iso,temperature_celsius
   2026-05-05T12:01:00Z,99.0" > volumes/drop/temperature-bad-001.csv
   ```
   La carte passe en orange (amber), motif "temperature 99.0 hors plage de plausibilite".
7. **Couper HAPI** : `docker compose stop hapi`. Les nouveaux messages basculent en file de repli SQLite. Page Logs et `/api/queue` montrent les items en attente. Redémarrer HAPI : la boucle de rejeu purge la queue automatiquement.

## Plugins

Pour ajouter un dispositif **sans modifier le code du bridge** :

1. Créer un dossier `plugins/<nom>/` avec un `plugin.toml` et un module Python.
2. Le module Python utilise un décorateur du registry :
   ```python
   from bridge_core.parser.base import BaseParser, parser_registry

   @parser_registry.register("mon_format")
   class MonParser(BaseParser):
       def parse(self, frame):
           ...
   ```
3. Créer un profil JSON dans `profiles/` qui référence `parser.type = "mon_format"`.
4. `docker compose restart bridge` (ou POST `/api/reload` pour les profils seuls).

Le plugin de démo `plugins/example-temperature/` montre la structure complète.

## Logs et observabilité

```bash
docker compose logs -f bridge       # logs JSON structurés
docker compose logs -f sim-philips  # trace des envois
docker compose logs -f hapi
```

## Arrêt

```bash
docker compose down                 # arrête, conserve les volumes
docker compose down -v              # arrête + supprime les volumes (reset complet)
```

## Architecture

| Couche | Rôle | Fichier |
|---|---|---|
| Adapter | Capture des trames depuis le canal physique | `bridge_core/adapter/{tcp_mllp,mqtt,file_watcher,serial_tcp}.py` |
| Parser | Décodage selon le format déclaré | `bridge_core/parser/{hl7v2,json_path,medibus}.py` |
| Mapper | Codification LOINC + génération FHIR R4 | `bridge_core/mapper/fhir.py` |
| Transport | POST mTLS, retry exponentiel, fallback SQLite | `bridge_core/transport/fhir_hapi.py` |
| Dashboard | FastAPI + HTMX + WebSocket | `bridge_core/dashboard/` |
| Plugin Manager | Chargement dynamique de modules tiers | `bridge_core/plugin/manager.py` |
| Persistence | File de repli SQLite WAL | `bridge_core/persistence/fallback_queue.py` |

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `BRIDGE_PORT` | `8080` | Port FastAPI |
| `HAPI_FHIR_URL` | `http://hapi:8080/fhir` | Cible FHIR |
| `MQTT_HOST` | `mqtt` | Hôte broker |
| `MQTT_PORT` | `1883` | Port MQTT |
| `PROFILES_DIR` | `/app/profiles` | Profils JSON |
| `PLUGINS_DIR` | `/app/plugins` | Plugins |
| `FALLBACK_DB` | `/app/data/fallback.sqlite` | Base SQLite WAL |
| `REPLAY_INTERVAL_SEC` | `30` | Intervalle de rejeu de la file de repli |
| `LOG_LEVEL` | `info` | Niveau Uvicorn |

## Dépannage

### Le bridge ne démarre pas

```bash
docker compose logs bridge
```

Causes fréquentes :
- Port 8080 déjà utilisé : `lsof -i :8080`
- Image pas encore construite : `docker compose build bridge`

### HAPI FHIR healthcheck KO

HAPI met 30 à 60 s à démarrer la première fois. Patience.

### Aucune Observation sur HAPI

Vérifier dans cet ordre :
1. `docker compose logs sim-philips` : envois détectés ?
2. `docker compose logs bridge | grep transport` : POST tenté ?
3. `curl http://localhost:8080/api/queue` : items en file de repli ?

### Reset complet

```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

## Test E2E automatisé

```bash
./scripts/e2e_test.sh
```

Lance les conteneurs, attend 60 s, vérifie que les Observations apparaissent sur HAPI, génère un compte rendu.
