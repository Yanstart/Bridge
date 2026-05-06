# IoT Edge Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009485.svg)](https://fastapi.tiangolo.com/)
[![FHIR R4](https://img.shields.io/badge/HL7-FHIR%20R4-bf1a2f.svg)](https://hl7.org/fhir/R4/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)

Passerelle d'interopérabilité Edge pour l'intégration de **dispositifs médicaux Legacy** au **BIHR** (Belgian Integrated Health Record).

> Un middleware **transparent et configurable** qui transforme les flux propriétaires (RS-232, BLE, fichiers XML, HL7 v2) en standards modernes (**FHIR R4**, codification **LOINC**), sans toucher au matériel certifié.

Projet de fin d'année **TS6 Technologies de la Santé** — EPHEC Brussels — 2025-2026.

| Auteur | Encadrant |
|---|---|
| Noël Junior Yando Fotso | Matthieu OLIVIERS |

---

## Vision

```
À gauche : le chaos               Au milieu : la passerelle         À droite : l'ordre
─────────────────────              ─────────────────────              ─────────────────────
 Moniteur Philips    ─┐                                            ┌─▶ HAPI FHIR R4
 Glucomètre Masimo   ─┤            ┌──────────────┐                ├─▶ DPI hospitalier
 ECG Welch Allyn     ─┼─trames─▶   │  Adapter     │                ├─▶ MetaHub / BIHR
 Pompe Dräger        ─┤            │  Parser      │ ─Bundle FHIR─▶ └─▶ Clinicien
 Logiciel Legacy XYZ ─┤            │  Mapper      │
 Export CSV maison   ─┘            │  Transport   │
                                   └──────────────┘
                              configurable par profils JSON
                                + plugins communautaires
```

## Livrables

| Document | Pages | Fichier |
|---|---|---|
| Cahier des charges | 66 | [`pdf/cdc.pdf`](pdf/cdc.pdf) |
| Rapport académique | 14 | [`pdf/rapport.pdf`](pdf/rapport.pdf) |
| Pitch Beamer | 15 | [`pdf/pitch.pdf`](pdf/pitch.pdf) |
| Démonstration dockerisée | — | [`demo/`](demo/) |

## Lancer la démo en 3 commandes

```bash
git clone https://github.com/Yanstart/Bridge.git
cd Bridge/demo
docker compose up -d --build
```

Puis ouvrir :

- Dashboard : http://localhost:8080/
- HAPI FHIR : http://localhost:8081/fhir/Observation?_count=20

Pour valider que tout fonctionne :

```bash
bash scripts/smoke_test.sh        # 14 routes vérifiées en moins de 5 s
bash scripts/e2e_test.sh          # test E2E complet (~3 min)
```

## Architecture

| Couche | Rôle | Implémentations |
|---|---|---|
| **Adapter** | Capture des trames depuis le canal physique | TCP MLLP, MQTT, file-watcher, RS-232 (TCP simulé) |
| **Parser** | Décodage selon le profil JSON du dispositif | HL7 v2, JSON, MEDIBUS ASCII, CSV (plugin) |
| **Mapper** | Codification LOINC + génération FHIR R4 | Bundle transaction Patient + Device + Observations |
| **Transport** | Émission vers la cible avec retry + fallback | HAPI FHIR, log_only, retry exponentiel, file SQLite WAL |
| **Dashboard** | Supervision OT, configuration profils | FastAPI + HTMX + WebSocket, no PII |
| **Plugin Manager** | Chargement de modules tiers | importlib, hot-reload, isolation d'erreurs |

## Documentation

| Document | Contenu |
|---|---|
| [`docs/PROJECT.md`](docs/PROJECT.md) | Charte projet, vision, décisions techniques, charte de style |
| [`docs/GUIDE_REDACTION.md`](docs/GUIDE_REDACTION.md) | Mapping cours TS6 vers projet, chapitre par chapitre |
| [`docs/EQUIPMENTS.md`](docs/EQUIPMENTS.md) | Datasheets des 8 équipements de référence |
| [`docs/DASHBOARD_UX.md`](docs/DASHBOARD_UX.md) | Spécification UX du dashboard |
| [`implémentation.md`](implémentation.md) | Journal des 7 sprints d'implémentation |

## Structure du dépôt

```
Bridge/
├── docs/        Documentation projet (Markdown)
├── src/         Sources LaTeX (préambule, biblio, figures, 3 squelettes)
├── pdf/         PDFs livrables finaux
├── demo/        Code de la démonstration dockerisée
│   ├── bridge/        Cœur Python (4 couches + dashboard + plugin manager)
│   ├── simulators/    4 simulateurs (Philips, Masimo, Welch Allyn, Dräger)
│   ├── profiles/      Profils JSON par dispositif
│   ├── plugins/       Plugins communautaires (1 exemple livré)
│   ├── volumes/       Volumes Docker (data, drop, mosquitto)
│   └── scripts/       Tests automatisés (smoke + E2E)
├── archive/     Sources originales du projet
├── Makefile     Compilation des trois livrables LaTeX
└── README.md    Ce fichier
```

## Compilation des livrables LaTeX

Prérequis : MiKTeX ou TeX Live, avec `latexmk` et `biber`.

```bash
make all              # compile rapport + pitch + cdc
make rapport          # uniquement le rapport
make pitch
make cdc
make clean            # supprime les auxiliaires LaTeX
```

Les PDFs finaux sont automatiquement copiés dans `pdf/`.

## Conformité

- **Standards** : HL7 v2, HL7 FHIR R4, LOINC, IHE PCD, MEDIBUS, ISO 13606/13608/27001/27799.
- **Réglementaire** : MDR 2017/745 (capture passive), RGPD (minimisation par construction).
- **Belgique** : alignement Plan d'action interfédéral eSanté 2025-2027, BIHR, MetaHub.
- **Statut juridique** : middleware d'intégration IT (non-DM), simplification de la chaîne de responsabilité.

## License

[MIT](LICENSE) — utilisation libre avec attribution.

## Crédits

Encadrement académique : Matthieu OLIVIERS, EPHEC Brussels.
Standards et données : HL7 International, IHE, KCE, INAMI, AFMPS, OMS.
