# IoT Edge Bridge

Passerelle d'interopérabilité Edge pour l'intégration de dispositifs médicaux Legacy au BIHR.

Projet de fin d'année **TS6 Technologies de la Santé** — EPHEC Brussels — 2025-2026.

Auteur : **Noël Junior Yando Fotso**.
Encadrant : **Matthieu OLIVIERS**.

---

## Structure du dépôt

```
Bridge/
├── docs/        Documentation projet (PROJECT, GUIDE_REDACTION, EQUIPMENTS)
├── src/         Sources LaTeX (3 livrables, préambule partagé, biblio, figures)
├── pdf/         PDFs livrables finaux (cdc, rapport, pitch)
├── archive/     Sources originales (.docx, .pptx)
├── demo/        Code de la démo Docker (en cours)
├── .claude/     Configuration Claude Code (settings.local.json)
├── Makefile     Cibles : all, rapport, pitch, cdc, clean, distclean
├── .gitignore
└── README.md    Ce fichier
```

### Dossier `src/`

```
src/
├── bridge-preamble.tex      Préambule LaTeX partagé (rapport, cdc)
├── references.bib           Bibliographie biblatex (35 entrées)
├── cdc.tex                  Squelette racine du CDC
├── rapport.tex              Squelette racine du rapport
├── pitch.tex                Pitch Beamer (autonome)
├── cdc/                     17 sections du CDC + glossaire
├── rapport/                 Intro + 7 chapitres + conclusion + annexes
└── figures/                 5 figures TikZ partagées
```

## Livrables

| Livrable | Pages | Fichier |
|---|---|---|
| Cahier des charges | 66 | `pdf/cdc.pdf` |
| Rapport académique | 14 | `pdf/rapport.pdf` |
| Pitch Beamer | 15 | `pdf/pitch.pdf` |

## Compilation

Prérequis : MiKTeX ou TeX Live, avec `latexmk` et `biber`.

```bash
make all              # compile les 3 livrables
make rapport          # compile uniquement le rapport
make pitch            # compile uniquement le pitch
make cdc              # compile uniquement le CDC
make clean            # supprime les auxiliaires LaTeX dans src/
make distclean        # supprime aussi les PDFs intermédiaires de src/
```

Les PDFs finaux sont automatiquement copiés dans `pdf/` après chaque compilation réussie.

## Démo

La démo dockerisée du middleware (4 simulateurs + bridge Python + HAPI FHIR + MQTT broker) sera implémentée dans `demo/`. Elle est lancée par `docker compose up`.

## Documentation projet

- [PROJECT.md](docs/PROJECT.md) : charte projet, vision, décisions, équipe, charte de style.
- [GUIDE_REDACTION.md](docs/GUIDE_REDACTION.md) : mapping cours TS6 vers projet, chapitre par chapitre.
- [EQUIPMENTS.md](docs/EQUIPMENTS.md) : datasheets des 8 équipements de référence.
