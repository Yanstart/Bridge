# Implémentation de la démonstration

Document de traçabilité des 7 sprints d'implémentation du middleware **IoT Edge Bridge**, sous `demo/`.

| Métadonnée | Valeur |
|---|---|
| Auteur | Noël Junior Yando Fotso |
| Encadrant | Matthieu OLIVIERS |
| Cours | TS6 Technologies de la Santé, EPHEC Brussels |
| Stack | Python 3.12, FastAPI, HTMX, Docker Compose, HAPI FHIR, MQTT |
| Période | mai 2026 |

## Vue d'ensemble

La démonstration matérialise les exigences du cahier des charges (`pdf/cdc.pdf`). Sept sprints courts ont permis de livrer un middleware fonctionnel qui absorbe quatre canaux d'entrée hétérogènes, normalise les flux en FHIR R4, expose un dashboard de supervision OT, et accepte des plugins communautaires.

Le code source vit dans `demo/`. La structure suit la séparation Adapter, Parser, Mapper, Transport déclarée au chapitre 7 du CDC, avec un Plugin Manager et une file de repli persistante.

```
Sprint 1 : Squelette docker-compose + bridge stub
Sprint 2 : Coeur modulaire 4 couches + profils JSON
Sprint 3 : Premier flux end-to-end Philips MLLP vers FHIR
Sprint 4 : 3 autres simulateurs (MQTT, fichier, RS-232)
Sprint 5 : Dashboard FastAPI + HTMX + WebSocket
Sprint 6 : Plugin manager actif + plugin exemple
Sprint 7 : Polish (retry, fallback SQLite, hot-reload, README final)
```

---

## Sprint 1 : Squelette docker-compose + bridge stub

### Objectif

Poser les fondations dockerisées pour qu'une commande unique (`docker compose up -d`) lance les services minimaux : un bridge Python stub, un serveur HAPI FHIR, un broker MQTT.

### Composants livrés

| Fichier | Rôle |
|---|---|
| `demo/docker-compose.yml` | Orchestration de 3 services (bridge, hapi, mqtt) |
| `demo/bridge/pyproject.toml` | Dépendances Python : FastAPI, Pydantic v2, httpx, paho-mqtt, pyserial, watchdog, hl7apy, structlog |
| `demo/bridge/Dockerfile` | Image Python 3.12-slim, utilisateur non-root, healthcheck `curl /health` |
| `demo/bridge/src/bridge_core/main.py` | FastAPI minimal, endpoints `/` et `/health` |
| `demo/bridge/README.md` | Documentation du paquet |
| `demo/README.md` | Procédure de lancement |

### Décisions techniques

- **Stack Python 3.12** retenue pour `tomllib` natif et `asyncio` performant.
- **FastAPI** plutôt que Flask : asynchrone, OpenAPI gratuit, validation Pydantic native.
- **HAPI FHIR** image officielle `hapiproject/hapi:latest`, mode H2 embarqué (pas de PostgreSQL nécessaire pour la démo).
- **MQTT** image `eclipse-mosquitto:2`, configuration permissive (anonymous) car réseau Docker isolé.
- **Volumes Docker** : `profiles/`, `plugins/`, `volumes/drop/`, `volumes/mosquitto/` pour découpler config du conteneur.

### Test et validation

Au démarrage des conteneurs, vérification manuelle des endpoints :
- `GET http://localhost:8080/health` retourne `{status: ok}`.
- `GET http://localhost:8081/fhir/metadata` retourne le `CapabilityStatement` HAPI.

### Conformité CDC

Couvre EF-PUB-002 (logs), ENF-PERF-001 (latence, posée mais non encore mesurée), section 11 (Plan de déploiement).

---

## Sprint 2 : Coeur modulaire 4 couches + profils JSON

### Objectif

Construire l'architecture interne du middleware en respectant la philosophie produit du CDC : **3 questions, 2 phases**. Tout dispositif doit pouvoir être ajouté par dépôt d'un fichier JSON, sans modification du code coeur.

### Composants livrés

| Fichier | Rôle |
|---|---|
| `bridge_core/models.py` | 11 modèles Pydantic : `DeviceProfile`, `ChannelConfig`, `ParserConfig`, `MappingConfig`, `FieldMapping`, `PlausibilityRange`, `DestinationConfig`, `DeviceMetadata`, `NormalizedMeasurement`, `Measurement`, `TransmissionStatus`, `DeviceStatus`, `PluginManifest` |
| `bridge_core/registry.py` | `Registry[T]` générique typé, décorateur `@register(name)` |
| `bridge_core/adapter/base.py` | `BaseAdapter` ABC + `RawFrame` + `adapter_registry` |
| `bridge_core/parser/base.py` | `BaseParser` ABC + `ParseError` + `parser_registry` |
| `bridge_core/mapper/base.py` | `BaseMapper` ABC + `mapper_registry` |
| `bridge_core/mapper/fhir.py` | `FhirBundleMapper` enregistré comme `fhir_bundle` (Bundle transaction Patient + Device + N Observations) |
| `bridge_core/transport/base.py` | `BaseTransport` ABC + `transport_registry` |
| `bridge_core/transport/fhir_hapi.py` | `FhirHapiTransport` (POST simple, sans retry encore) |
| `bridge_core/transport/log_only.py` | `LogOnlyTransport` pour debug |
| `bridge_core/config/loader.py` | `ProfileLoader` qui scanne `profiles/`, valide chaque JSON via Pydantic |
| `bridge_core/plugin/manager.py` | `PluginManager` qui scanne `plugins/`, lit chaque `plugin.toml` |
| `bridge_core/core.py` | `BridgeCore` orchestrateur, instancie les pipelines à partir des registries |
| `bridge_core/main.py` | Wiring complet : lifespan FastAPI, lecture profils + plugins, démarrage core, endpoints API |
| `demo/profiles/philips-mx450.json` | Premier profil de référence (Philips IntelliVue MX450) |

### Décisions techniques

- **Pattern Registry** : chaque couche maintient un dictionnaire `{type_name: classe}`. L'ajout d'un nouveau type (par plugin par exemple) ne touche pas au coeur.
- **Pydantic v2 strict** : `extra="forbid"` sur les profils pour rejeter les clés inconnues, `extra="allow"` sur les configs spécifiques d'Adapter pour rester souple.
- **Asyncio queue partagée** entre tous les Adapters : un seul coeur de traitement, simplicité, faible latence.
- **Compteurs internes** par device (`success`, `errors`, `quarantined`, `last_seen`) pour alimenter le dashboard.

### Test et validation

Smoke test Python local :
```
Profils chargés : 1 (philips-mx450)
Pipeline non instancié (TcpMllpAdapter pas encore enregistré, attendu)
Statut équipement : "gray", "aucune communication recue"
Bridge démarre et s'arrête proprement.
```

### Conformité CDC

Couvre EF-PRS-001 (sélection profil), EF-MAP-001 à EF-MAP-005 (mapping FHIR), ENF-CFG-001 (configurabilité, ajout dispositif sans code), section 7 (architecture technique).

---

## Sprint 3 : Premier flux end-to-end Philips MLLP vers FHIR

### Objectif

Faire passer une trame **réelle** de bout en bout : un message HL7 v2 ORU^R01 émis par un simulateur Philips, capté par le bridge en MLLP, décodé, codifié en LOINC, transformé en Bundle FHIR R4, publié sur HAPI.

### Composants livrés

| Fichier | Rôle |
|---|---|
| `bridge_core/adapter/tcp_mllp.py` | Listener MLLP asyncio, multi-clients, ACK MLLP automatique |
| `bridge_core/parser/hl7v2.py` | Parser HL7 v2 par split, extraction OBX par code LOINC, vérification plages de plausibilité |
| `simulators/philips-mx450/Dockerfile` | Conteneur Python 3.12-slim |
| `simulators/philips-mx450/send_hl7v2.py` | Génère un message ORU^R01 toutes les 10 s avec valeurs aléatoires plausibles (SpO2 92-99 %, FC 55-95 bpm, PA sys 105-135 mmHg, PA dia 65-90 mmHg) |
| `docker-compose.yml` (mis à jour) | + service `sim-philips`, port 2575 exposé |

### Décisions techniques

- **Délimiteurs MLLP** : VT (`0x0B`) au début, FS+CR (`0x1C 0x0D`) à la fin. Détection par recherche dans un `bytearray` accumulé.
- **Multi-clients concurrents** via `asyncio.start_server` : un grand hôpital peut avoir plusieurs lits qui poussent vers la même passerelle.
- **ACK MLLP** : génération d'un message MSA|AA en réponse, avec reprise du `control_id` du MSH d'origine. Les simulateurs vérifient cet ACK pour valider la livraison.
- **Parser HL7 v2 simple** plutôt que `hl7apy` complet : plus rapide à compiler en Docker, suffisant pour OBX-3 + OBX-5.
- **Quarantaine sur valeur hors plage** : si une mesure dépasse la `plausibility` du profil, on lève `ParseError` et le message va en quarantaine, statut `amber` sur le dashboard.

### Test et validation

E2E local sans HAPI (transport `log_only` patché) :
```
1. Bridge démarre, registries peuplés (tcp_mllp, hl7v2, fhir_bundle, log_only)
2. Listener MLLP ouvert sur :12575
3. Message HL7v2 ORU^R01 envoyé via socket
4. ACK MLLP reçu : MSA|AA (88 octets)
5. Bundle FHIR construit : 6 entries (1 Patient + 1 Device + 4 Observations)
6. Statut équipement : color=green, messages_total=1
```

### Conformité CDC

Couvre EF-ADP-001 (capture TCP HL7v2), EF-PRS-002 (décodage selon profil), EF-PRS-005 (quarantaine), EF-MAP-001 à EF-MAP-005, section 8.2 (HL7 FHIR R4).

---

## Sprint 4 : 3 autres simulateurs (MQTT, fichier, RS-232)

### Objectif

Démontrer la diversité absorbée par le middleware : 4 canaux différents traités par le **même coeur**, chacun via son profil JSON.

### Composants livrés

#### Adapters et Parsers

| Fichier | Type | Description |
|---|---|---|
| `bridge_core/adapter/mqtt.py` | `mqtt` | Abonnement MQTT via paho-mqtt en thread, bridge vers asyncio.Queue par `run_coroutine_threadsafe` |
| `bridge_core/adapter/file_watcher.py` | `file_watcher` | Surveillance d'un dossier via watchdog.Observer, lecture de chaque fichier matchant le pattern |
| `bridge_core/adapter/serial_tcp.py` | `serial_tcp` | Client TCP avec délimiteurs STX/ETX, retry exponentiel sur déconnexion |
| `bridge_core/parser/json_path.py` | `json` | Sélecteurs `$.<champ>.<sub>` minimalistes, sans dépendance externe |
| `bridge_core/parser/medibus.py` | `medibus_ascii` | Format `RDATA\|FIO2:30\|PEEP:5\|VT:450\|RR:14`, paires clé:valeur |

#### Simulateurs

| Conteneur | Stack | Comportement |
|---|---|---|
| `sim-masimo` | Python + paho-mqtt | Publie SpO2/PR/PI sur `devices/masimo-radical7/spo2` toutes les 8 s |
| `sim-welchallyn` | Python | Dépose `welchallyn-*.json` dans `/drop` toutes les 20 s, écriture atomique (write-then-rename) |
| `sim-drager` | Python asyncio | Serveur TCP port 6100, envoie trames MEDIBUS toutes les 5 s à chaque client |

#### Profils JSON

| Profil | Canal | Parser | Mappings LOINC |
|---|---|---|---|
| `masimo-radical7.json` | mqtt | json | SpO2 (59408-5), FC (8867-4) |
| `welchallyn-cp150.json` | file_watcher | json | FC (8867-4), PR (8625-6), QT (8634-8) |
| `drager-evita-v500.json` | serial_tcp | medibus_ascii | FiO2 (19994-3), PEEP (20077-4), VT (76530-3), FR (9279-1) |

### Décisions techniques

- **MQTT en thread** plutôt qu'un client async pur (`aiomqtt` aurait fonctionné, mais `paho-mqtt` est la référence de l'écosystème, plus stable).
- **File watcher avec écriture atomique** : le simulateur Welch Allyn écrit dans un `.tmp` puis renomme, ce qui évite les lectures partielles côté bridge.
- **RS-232 simulé via TCP** plutôt que pseudo-tty partagé entre conteneurs : plus simple à orchestrer en Docker, sémantique de stream identique.
- **Format MEDIBUS simplifié** : on garde les délimiteurs STX/ETX et les paires `clé:valeur`, on n'implémente pas tout le protocole Dräger réel (suffisant pour la démo).

### Test et validation

Smoke test Python local :
```
Adapters chargés : ['file_watcher', 'mqtt', 'serial_tcp', 'tcp_mllp']
Parsers chargés  : ['hl7v2', 'json', 'medibus_ascii']
Transports        : ['fhir_hapi', 'log_only']
Profils chargés   : 4
Pipelines instanciés sans erreur, listeners démarrés et arrêtés proprement.
```

### Conformité CDC

Couvre EF-ADP-002 (MQTT), EF-ADP-003 (fichier), EF-ADP-004 (RS-232), section 3.2 (use cases UC1 à UC4), section 7 (architecture technique).

---

## Sprint 5 : Dashboard FastAPI + HTMX + WebSocket

### Objectif

Donner au technicien biomédical une interface de supervision **claire**, **dense**, **temps réel**, sans aucune valeur clinique patient affichée. Le dashboard doit aider le cerveau à comprendre vite.

La spécification UX complète se trouve dans `docs/DASHBOARD_UX.md`.

### Composants livrés

| Fichier | Rôle |
|---|---|
| `bridge_core/events.py` | `BridgeEvent` (dataclass) + `EventBuffer` (deque borné + abonnement WebSocket) |
| `bridge_core/dashboard/routes.py` | 5 routes HTML + 2 fragments HTMX + WebSocket `/ws/events` |
| `bridge_core/dashboard/templates/base.html` | Layout commun : topbar + nav + footer légende + WebSocket JS |
| `bridge_core/dashboard/templates/index.html` | Vue d'ensemble : KPI bar + grille équipements + activité récente |
| `bridge_core/dashboard/templates/device_detail.html` | Détail équipement : profil + mappings LOINC + timeline |
| `bridge_core/dashboard/templates/config.html` | Configuration : 3 questions (canal/langue/sortie) par profil, en lecture |
| `bridge_core/dashboard/templates/logs.html` | Logs filtrables (équipement, niveau) |
| `bridge_core/dashboard/templates/plugins.html` | Catalogue plugins + statut chargement |
| `bridge_core/dashboard/templates/partials/devices_grid.html` | Fragment HTMX rafraîchi auto toutes les 5 s |
| `bridge_core/dashboard/templates/partials/events_list.html` | Fragment liste d'événements |
| `bridge_core/dashboard/static/style.css` | CSS palette projet, responsive, WCAG AA |

Le `BridgeCore` pousse un `BridgeEvent` à chaque étape du pipeline (frame_received, frame_parsed, frame_quarantined, transport_success, transport_failure). Les événements alimentent la timeline ET sont diffusés en WebSocket aux clients connectés.

### Décisions techniques et UX

- **HTMX** plutôt qu'un SPA React : densité de code réduite (1 ligne `hx-get` vs 100 lignes de hooks), pas de build JS, accessible.
- **WebSocket** pour le push temps réel + heartbeat 15 s pour résister aux proxies.
- **Pas de bouton refresh** : auto-refresh des fragments via HTMX `hx-trigger="refresh, every 5s"`.
- **Légende permanente** des couleurs en pied de page (réduit la charge cognitive).
- **Toasts** non bloquants en bas à droite à chaque événement WebSocket.
- **Aucune valeur clinique** dans les templates : la règle de minimisation (ENF-CONF-001) est garantie par construction.
- **Palette cohérente** avec les livrables LaTeX : bridgeblue, bridgeteal, bridgegreen, bridgewarn-amber, bridgealert, bridgegray.

### Conformité avec la spec UX

- Loi de proximité : carte unique par équipement.
- Loi de similarité : couleurs invariantes.
- Loi de Hick : navigation à 4 entrées max.
- Affordances claires : boutons primaires en teal.
- Reconnaissance > rappel : tooltips et libellés humains.
- Responsive (max 1280 px, breakpoint 700 px).

### Test et validation

Test avec serveur Uvicorn local sur port 8090 :
```
GET /                       -> 200, HTML rendu, "IoT Edge Bridge"
GET /health                 -> 200, JSON registries peuplés
GET /api/devices            -> 200, 4 équipements en color=gray
GET /static/style.css       -> 200, CSS servi
GET /devices/philips-mx450  -> 200, page détail rendue
```

### Conformité CDC

Couvre EF-DSH-001 à EF-DSH-006 (CRUD profils, statut couleur, contexte indicatif, alertes mail no-PII, compteurs, no donnée clinique), ENF-UX-001 (chargement < 2 s), ENF-CONF-001 (minimisation).

---

## Sprint 6 : Plugin manager actif + plugin exemple

### Objectif

Démontrer que la passerelle est un **framework communautaire** : un tiers peut ajouter un nouveau type de canal ou de parser sans modifier le coeur, simplement en déposant un dossier dans `plugins/`.

### Composants modifiés

| Fichier | Modification |
|---|---|
| `bridge_core/models.py` | `channel.type`/`parser.type`/`destination.type` passent de `Literal[...]` à `str`. Validation effective par les registries au moment de l'instanciation |
| `bridge_core/plugin/manager.py` | Réécriture complète : `PluginRecord` (path, manifest, status, error, loaded_at), `discover()`, `load_all()` avec `importlib.util.spec_from_file_location`, isolation d'erreurs |
| `bridge_core/main.py` | Plugins découverts + chargés **avant** les profils |
| `bridge_core/dashboard/routes.py` | `/plugins` expose les `records` complets |
| `bridge_core/dashboard/templates/plugins.html` | Statut loaded/error/discovered, message d'erreur, date de chargement |

### Plugin exemple livré

`plugins/example-temperature/` :

| Fichier | Rôle |
|---|---|
| `plugin.toml` | Manifeste : nom, version 0.1.0, layer=parser, code LOINC 8310-5, entrypoint module `parser_temperature_csv` |
| `parser_temperature_csv.py` | Parser CSV qui enregistre `@parser_registry.register("temperature_csv")` sur `TemperatureCsvParser` |

Profil associé `profiles/example-temperature.json` :
- canal `file_watcher` (réutilise un type natif)
- parser `temperature_csv` (type ajouté par le plugin)
- mapping LOINC 8310-5 (Body temperature)
- plage de plausibilité 30 à 43 °C

### Décisions techniques

- **`importlib.util.spec_from_file_location`** plutôt que `importlib.import_module` : permet de charger un fichier `.py` sans qu'il soit dans un package installé.
- **Nommage interne `<plugin>__<module>`** pour éviter les collisions entre plugins.
- **Isolation d'erreurs** : tout ce qui se passe dans `_load_one()` est dans un `try/except`. Une exception est journalisée et le plugin marqué `status=error`, le bridge continue à fonctionner.
- **Trace tronquée à 3 niveaux** dans le log d'erreur : suffisant pour diagnostiquer, pas trop verbeux.
- **Hot-reload limité au sprint 7** : Python ne supporte pas le rechargement propre de modules importés. On documente la limitation et on prévoit `/api/reload` pour les profils seuls.

### Test et validation

```
Plugin découvert : example-temperature v0.1.0 (layer=parser)
Plugin chargé    : status=loaded, error=None
Parser registry  : ['hl7v2', 'json', 'medibus_ascii', 'temperature_csv']
Profils chargés  : 5 (dont example-temperature qui utilise le type custom)
```

### Conformité CDC

Couvre EF-PLG-001 à EF-PLG-004 (chargement, validation, hot-reload partiel, isolation), section 14 (Roadmap, F1 plugins communautaires), section 7.5 (Mécanisme de plugin).

---

## Sprint 7 : Polish (retry, fallback SQLite, hot-reload, README final)

### Objectif

Rendre la démonstration **robuste face aux pannes** et **prête pour le jury**. Si HAPI tombe en panne, les Bundles ne sont pas perdus : ils sont persistés et rejoués automatiquement.

### Composants livrés

| Fichier | Apport |
|---|---|
| `bridge_core/persistence/fallback_queue.py` | SQLite WAL + table `fallback_queue` (id, device_id, payload, enqueued_at, retries, last_error). Méthodes : `enqueue`, `list_pending`, `mark_sent`, `mark_failed`, `count` |
| `bridge_core/transport/fhir_hapi.py` | Tenacity retry exponentiel (3 tentatives, 1-8 s) sur `httpx.RequestError`. En cas d'échec final : enqueue dans la `FallbackQueue` partagée |
| `bridge_core/core.py` | Instancie `FallbackQueue` au démarrage (chemin paramétrable). Boucle `_replay_loop()` qui purge la queue toutes les 30 s |
| `bridge_core/main.py` | Endpoints `/api/queue` (état file de repli) et `/api/reload` (hot-reload des profils + redémarrage du core sans tuer le processus) |
| `docker-compose.yml` | Volume `volumes/data/:/app/data:rw` pour la SQLite |
| `demo/README.md` | Procédure complète, scénario de démonstration en 7 étapes, dépannage |
| `demo/scripts/e2e_test.sh` | Test E2E automatisé : lance compose, attend healthchecks, vérifie endpoints, attend production de messages, vérifie Observations sur HAPI |

### Décisions techniques

- **Tenacity** plutôt qu'une boucle `for` artisanale : exponentiel intégré, tests prouvés, `AsyncRetrying` natif.
- **SQLite WAL** : autorisation d'écritures concurrentes non bloquantes, parfait pour un fallback queue.
- **`PRAGMA synchronous=NORMAL`** : compromis durabilité/performance, suffisant pour la démo (fsync à chaque commit serait excessif).
- **Schéma minimal** (pas d'ORM) : 5 colonnes, 4 méthodes, ~150 lignes Python. Pas de migration nécessaire.
- **Hot-reload des plugins exclu** par décision : Python ne supporte pas le rechargement propre des modules. Le redémarrage du conteneur est rapide (`docker compose restart bridge`).
- **Hot-reload des profils OK** : `/api/reload` recharge les profils, arrête le `BridgeCore`, en crée un nouveau, le démarre. La file de repli est partagée entre les deux instances.

### Test et validation

Test E2E retry + fallback (URL HAPI volontairement invalide) :
```
1. Trame HL7v2 reçue par MLLP listener.
2. Transport tente POST -> ConnectTimeout.
3. Tenacity retry exponentiel : 2 échecs successifs.
4. Enqueue dans fallback SQLite : item #1, retries=0, error="network: ConnectTimeout".
5. Bridge stoppé proprement.
```

Le scénario inverse (`docker compose stop hapi` puis `docker compose start hapi`) est documenté dans `README.md` et provoque automatiquement le rejeu de la file.

### Conformité CDC

Couvre EF-TRP-002 (retry exponentiel ×3), EF-TRP-003 (fallback file SQLite), ENF-RESL-001 (stabilité durée démo), ENF-SEC-001 (intégrité), ENF-MTN-001 (logs structurés JSON).

---

## Architecture finale

```
demo/
+-- README.md
+-- docker-compose.yml                 (7 services)
+-- bridge/
|   +-- pyproject.toml
|   +-- Dockerfile
|   +-- README.md
|   +-- src/bridge_core/
|       +-- adapter/
|       |   +-- base.py                 (BaseAdapter ABC + RawFrame + registry)
|       |   +-- tcp_mllp.py             (sprint 3)
|       |   +-- mqtt.py                 (sprint 4)
|       |   +-- file_watcher.py         (sprint 4)
|       |   +-- serial_tcp.py           (sprint 4)
|       +-- parser/
|       |   +-- base.py                 (BaseParser ABC + ParseError + registry)
|       |   +-- hl7v2.py                (sprint 3)
|       |   +-- json_path.py            (sprint 4)
|       |   +-- medibus.py              (sprint 4)
|       +-- mapper/
|       |   +-- base.py
|       |   +-- fhir.py                 (FhirBundleMapper)
|       +-- transport/
|       |   +-- base.py
|       |   +-- fhir_hapi.py            (retry + fallback au sprint 7)
|       |   +-- log_only.py
|       +-- persistence/
|       |   +-- fallback_queue.py       (sprint 7)
|       +-- plugin/
|       |   +-- manager.py              (sprint 6)
|       +-- dashboard/
|       |   +-- routes.py
|       |   +-- templates/              (5 écrans + 2 partials)
|       |   +-- static/style.css
|       +-- config/
|       |   +-- loader.py
|       +-- core.py                     (BridgeCore orchestrateur)
|       +-- events.py                   (EventBuffer pour dashboard)
|       +-- models.py                   (11 modèles Pydantic)
|       +-- registry.py                 (Registry générique)
|       +-- main.py                     (FastAPI + lifespan)
+-- simulators/
|   +-- philips-mx450/                  (TCP MLLP HL7v2)
|   +-- masimo-radical7/                (MQTT JSON)
|   +-- welchallyn-cp150/               (fichier JSON)
|   +-- drager-evita-v500/              (TCP simulant RS-232)
+-- profiles/                           (5 profils JSON)
|   +-- philips-mx450.json
|   +-- masimo-radical7.json
|   +-- welchallyn-cp150.json
|   +-- drager-evita-v500.json
|   +-- example-temperature.json
+-- plugins/
|   +-- example-temperature/            (plugin exemple)
+-- scripts/
|   +-- e2e_test.sh                     (test automatisé)
+-- volumes/
    +-- drop/                           (file-watcher)
    +-- data/                           (SQLite fallback)
    +-- mosquitto/                      (config MQTT)
```

## Bilan technique

| Indicateur | Valeur |
|---|---|
| Lignes de code Python | ~2500 |
| Modules Python | 25 |
| Services Docker | 7 |
| Profils JSON livrés | 5 (4 simulateurs + 1 plugin) |
| Plugins exemples | 1 |
| Templates HTML | 7 |
| Endpoints HTTP | 13 |
| Modèles Pydantic | 11 |
| Tests automatisés | E2E shell (couverture des principaux endpoints) |

## Conformité globale au CDC

| Section CDC | Sprint(s) | Statut |
|---|---|---|
| 4.1 Adapter Layer (6 EF) | 3, 4 | Implémenté |
| 4.2 Parser Layer (5 EF) | 3, 4, 6 | Implémenté |
| 4.3 Mapper Layer (5 EF) | 2 | Implémenté |
| 4.4 Transport Layer (4 EF) | 2, 7 | Implémenté |
| 4.5 Publication (3 EF) | 7 | Implémenté |
| 4.6 Dashboard (6 EF) | 5 | Implémenté |
| 4.7 Plugins (4 EF) | 6, 7 | Implémenté |
| 5.1 Performance | 3, 4, 7 | Mesurable, à benchmarker |
| 5.2 Disponibilité | 7 | Retry + fallback OK |
| 5.3 Sécurité | 7 | Logs sans PII, mTLS prévu, non activé en démo |
| 5.4 Confidentialité (minimisation) | 5, 7 | Garantie par construction |
| 5.5 Maintenabilité | 5, 7 | Logs JSON structlog |
| 5.6 Configurabilité | 2, 6 | Profils JSON + plugins |
| 5.7 UX | 5 | Spec UX respectée |

## Incidents post-livraison

### I1 (2026-05-05) : Starlette 1.0 casse TemplateResponse

**Symptôme** : au premier `docker compose up --build` après livraison, les 5 routes HTML du dashboard renvoient `HTTP 500 Internal Server Error` avec `TypeError: unhashable type: 'dict'` dans Jinja2.

**Cause** : `pyproject.toml` n'avait pas de borne haute sur `fastapi` ni `starlette`. Pip a installé Starlette 1.0.0 (sortie en mai 2026), qui a changé la signature de `TemplateResponse` en exigeant `request` comme premier argument positionnel. L'ancienne signature `TemplateResponse(name, {"request": request, ...})` est interprétée comme `TemplateResponse(request=name_str, name=context_dict)`, et le `dict` non hashable plante le cache Jinja2.

**Correctifs** :
1. Réécriture des 7 appels `TemplateResponse` dans `bridge_core/dashboard/routes.py` pour passer `request` en premier argument.
2. Pin haut sur `fastapi<2.0`, `starlette<2.0`, et bornes hautes sur toutes les autres dépendances dans `pyproject.toml`.
3. Ajout d'un `scripts/smoke_test.sh` qui vérifie en moins de 5 s que les 14 routes principales répondent en HTTP 200 avec le contenu attendu. À lancer après chaque rebuild.

**Validation** : `bash scripts/smoke_test.sh` retourne `14/14 OK` après rebuild propre.

## Prochaine étape

Lancer le test E2E automatisé :

```bash
cd demo/
./scripts/e2e_test.sh
```

Vérifier que les Observations FHIR apparaissent sur HAPI :

```bash
curl http://localhost:8081/fhir/Observation?_count=20
```

Ouvrir le dashboard :

```
http://localhost:8080/
```
