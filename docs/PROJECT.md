# Projet IoT Edge Bridge — Charte de coordination

> Document de référence partagé par toute l'équipe d'agents `bridge-*`.
> Toute décision structurante est consignée ici. Mis à jour au fil du projet.

## 1. Identité du projet

- **Titre** : Passerelle d'Interopérabilité Edge (IoT Bridge) pour l'intégration de dispositifs médicaux Legacy au BIHR.
- **Auteur** : Noël Junior Yando Fotso
- **Cours** : TS6 — Technologies de la Santé
- **Établissement** : EPHEC Brussels
- **Enseignant** : Matthieu OLIVIERS
- **Année** : 2025-2026
- **Date prévisionnelle de remise** : 2 mars 2027

## 2. Vision (à reprendre dans les 3 livrables)

> **À gauche : le chaos.**
> Des dispositifs IoT médicaux et logiciels hétérogènes, non interopérables, dont les sorties (protocoles série temps réel, XML propriétaires, CSV, JSON, BLE legacy…) ne peuvent pas remonter automatiquement dans le parcours de soin.
>
> **Au milieu : la passerelle.**
> Un *bridge* **configurable et multi-couches** qui absorbe ces flux disparates, les normalise, les uniformise, les sécurise.
>
> **À droite : l'ordre.**
> Des dispositifs interopérables, supervisés, et dont les informations arrivent au DPI/BIHR dans un format standardisé (FHIR R4 + KMEHR + SNOMED-CT/LOINC).

### Finalités (ce que la solution sert)

1. **Améliorer la prise en charge du patient** (complétude du dossier, continuité, traçabilité).
2. **Faciliter la prise de décision** des personnels soignants (aide à la décision, données fiables et horodatées).
3. **Aider au suivi des équipements** (état de connexion, certificats, anomalies — rôle des techniciens biomédicaux).
4. **Donner une vision claire à l'OT** (Operational Technology / parc machine hospitalier).

## 3. Livrables (tous en LaTeX)

| # | Livrable | Fichier | Statut | Responsable principal |
|---|---|---|---|---|
| 1 | **Rapport académique** | `rapport.tex` | Squelette + ch.1 rédigé (à muscler) | `bridge-redacteur` |
| 2 | **Pitch (10 min) + démo séparée (5 min)** | `pitch.tex` (Beamer) + scénario démo | À refaire totalement | `bridge-pitch` |
| 3 | **Cahier des charges *de la démo*** | `cdc.tex` | À créer — guide ma propre implémentation | `bridge-cdc` |

Support transverse : `bridge-architecte` (cohérence technique), `bridge-latex` (mise en forme et diagrammes).

## 4. Nature de la passerelle (PRINCIPE FONDATEUR)

**Aucune décision n'est verrouillée a priori.** La passerelle est conçue comme un **framework configurable** capable de s'adapter à plusieurs cas selon les besoins.

### Couches d'absorption supportées (côté entrée)

| Type | Cas d'usage typiques | Exemples |
|---|---|---|
| **Protocole série temps réel** | Équipements critiques temps réel | RS-232, RS-485, USB-série, CAN bus |
| **Bluetooth legacy / BLE** | Glucomètres, balances, oxymètres portables | Bluetooth Classic, BLE GATT |
| **Réseau propriétaire** | Moniteurs en réseau, pompes IP | TCP brut, UDP, HL7 v2 over MLLP |
| **Fichiers** | Spiromètres, équipements export batch | XML (propriétaires ou non), CSV, JSON |
| **OCR (dernier recours)** | Dispositifs sans sortie numérique | Capture d'écran |

### Couches de sortie (côté plateforme)

- **HL7 FHIR R4** (REST/JSON) — pivot principal vers DPI moderne et BIHR.
- **HL7 v2 ORU^R01** (MLLP) — pour DPI legacy hospitaliers.
- **KMEHR** (XML) — pour l'eHealthBox et les hubs régionaux belges.
- **DICOM** — hors scope direct mais framework extensible.

### Architecture interne (à instancier en CDC)

```
┌─────────────────┐
│  Adapter Layer  │  ← drivers série, BLE, file-watcher, TCP listener…
└────────┬────────┘
         │ (raw frames / files)
┌────────▼────────┐
│  Parser Layer   │  ← profils par dispositif (config JSON), décodage, conversions d'unités
└────────┬────────┘
         │ (objet normalisé)
┌────────▼────────┐
│  Mapper Layer   │  ← codification SNOMED-CT/LOINC, construction ressources FHIR
└────────┬────────┘
         │ (FHIR / HL7v2 / KMEHR)
┌────────▼────────┐
│ Transport Layer │  ← mTLS, retry, file de repli locale
└────────┬────────┘
         │
         ▼
   eHealth / DPI / BIHR
```

> Chaque couche est **un point d'extension** (plug-in). C'est ce qui rend le bridge configurable.

## 5. Statut de la passerelle (positionnement clarifié)

> **La passerelle est un middleware transparent et configurable. Pas un dispositif médical (DM).**

- **Transparent** côté dispositif : capture passive, ne modifie ni firmware ni câblage interne.
- **Configurable** : on déclare en JSON ce qu'on reçoit et ce qu'on émet ; aucune modification de code pour ajouter un nouveau dispositif.
- **Pas de prétention au statut DM** : on consomme des sorties existantes et on les normalise. Outil d'intégration IT, conscient des contraintes santé (RGPD, capture passive MDR-friendly), mais pas un DM IIa.

### Philosophie produit — 3 questions, 2 phases

**Phase 1 — Handshake technique** (géré par le développeur, profils livrés avec la passerelle)
1. *« Quel est ton canal de communication ? »* → TCP/IP, RS-232, BLE, fichier déposé, MQTT, USB…
2. *« Quelle langue parles-tu ? Comment structures-tu tes données ? »* → HL7 v2, JSON propriétaire, XML, ASCII brut, MEDIBUS, MIB…

**Phase 2 — Configuration métier** (gérée par l'admin via le dashboard)

3. *« Une fois la connexion établie et la compréhension faite : qu'est-ce qu'on configure en sortie pour envoyer à la DB / au DPI / au BIHR ? »*
   → choix de la cible (HAPI FHIR, eHealthBox, hub régional…), choix du mapping (LOINC), enrichissements (identité patient, contexte clinique).

Cette séparation handshake/config est un **principe directeur** que les 3 livrables doivent illustrer.

### Dashboard — rôle clarifié

Le dashboard sert à **configurer le middleware** et à **superviser l'OT**, pas à montrer des données patient.

| Volet | Contenu |
|---|---|
| **Configuration** | CRUD des profils JSON par équipement (canal, langue, mapping de sortie) |
| **Supervision OT** | Liste des équipements connectés ; statut couleur (vert / orange / rouge) ; dernière communication ; nombre de messages traités |
| **Anomalies** | Si statut change → contexte indicatif **lié à l'équipement** (ex. "n'émet plus depuis 5 min", "valeurs hors plage de plausibilité 12 fois sur les 100 dernières trames", "certificat expiré"). |
| **Alertes mail** | Notifications **non personnelles** : identifiant équipement, type d'erreur, horodatage, contexte technique. **Jamais de donnée patient.** |

> **Principe de minimisation** : le dashboard ne consulte pas les valeurs cliniques traduites des patients. Il regarde *les flux*, pas *le contenu*. Les valeurs partent vers le DPI/BIHR ; les techniciens BM/OT voient *que* ça circule, pas *ce qui* circule.

## 6. Contraintes

### Réglementaires (à respecter, pas à contourner)
- **MDR 2017/745** : la passerelle est en lecture seule côté dispositif (capture passive) → ne modifie pas le DM, ne perd pas le marquage CE.
- **RGPD** + AR belges (loi 22 août 2002 droits du patient, loi 30 juillet 2018 protection des données).

### Tech stack confirmée
- **Langage** : **Python** (FastAPI).
- **Persistence locale** : SQLite (mode WAL, chiffré applicatif).
- **Dashboard** : web léger (FastAPI + HTMX).
- **Démo** : tout **dockerisé en local** (`docker compose up`).
- **Compilation LaTeX** : XeLaTeX + biber.

### Démo — équipements simulés (4 conteneurs)

| # | Famille | Modèle de référence | Canal | Sortie native | Finalité |
|---|---|---|---|---|---|
| 1 | Moniteur multiparamétrique | Philips IntelliVue MX450 / GE B105 / Mindray BeneView | **TCP/IP** | HL7 v2 ORU^R01 over MLLP | Prise en charge patient |
| 2 | Glucomètre/oxymètre portable | Masimo Radical-7 / Roche Accu-Chek | **BLE simulé via MQTT** | JSON propriétaire | Décision soignante |
| 3 | Spiromètre/ECG ambulatoire | Vyaire MicroLab / Welch Allyn CP150 | **Fichier XML déposé** | XML propriétaire | Suivi patient |
| 4 | Pompe / ventilateur | B. Braun Infusomat / Dräger Evita V500 | **RS-232 simulé (socat)** | Trame ASCII | Vision OT, suivi équipement |

Chaque équipement = un conteneur Docker émettant des données conformes à sa datasheet réelle.

## 6. Public et ton de chaque livrable

| Livrable | Public | Ton |
|---|---|---|
| Rapport | Matthieu OLIVIERS (jury TS6) | Académique, sourcé, **structuré par les 7 chapitres du cours** ; chaque chapitre = un concept du cours mobilisé pour résoudre un problème concret du projet |
| Pitch (10 min + démo) | Camarades TS6 | Pédagogique ; le cours est le fil conducteur ; **démo écran** au cœur du pitch |
| CDC | Moi-même (auteur) — pour guider l'implémentation de la démo | Prescriptif et réaliste pour un MVP démontrable, exigences testables, archi configurable lisible |

## 7. Règle de concision

> *Le plus dur sera de rester concis sans juste supprimer du contenu, mais en étant précis.*

- **Densité, pas longueur** : chaque phrase doit porter une information.
- **Visuels en annexe** : les schémas détaillés vivent en annexe ; le corps du texte garde une vue d'ensemble.
- **Pas d'enrobage rhétorique** : pas de "dans un monde toujours plus connecté…".
- **Tableaux > listes à puces** quand on compare ou qu'on structure du quantitatif.

## 7bis. Charte de style éditoriale (impérative)

Règles à respecter dans les trois livrables et dans toute production rédactionnelle des agents.

1. **Pas de tiret cadratin**, caractère `—` (U+2014). Le remplacer par `:`, `,`, des parenthèses, ou un point.
2. **Pas de tiret demi-cadratin**, caractère `–` (U+2013), sauf dans les plages de pages ou de dates en bibliographie.
3. **Phrases simples**. Une idée par phrase. Sujet, verbe, complément. Pas de subordonnées en cascade.
4. **Voix active** par défaut. Voix passive uniquement quand l'agent est inconnu ou non pertinent.
5. **Densité**. Chaque phrase porte une information. Aucun délayage.
6. **Visuels**. Préférer un tableau, un schéma TikZ ou un diagramme à un paragraphe quand le contenu est comparatif ou structuré.
7. **Listes courtes**. Maximum 5 éléments. Au-delà, basculer en tableau.
8. **Pas d'emojis** dans les fichiers livrables (`.tex`, `.bib`, `.pdf`).
9. **Termes techniques anglais conservés** (FHIR, mTLS, BIHR, BLE, MQTT, SpO2, HL7, etc.).

### Vérifications automatisables

- Recherche du caractère `—` dans tous les `.tex` produits, doit retourner zéro résultat.
- Aucune phrase de plus de 30 mots dans le corps du texte (à l'exception des énoncés d'exigences MoSCoW qui suivent un format réglé).
- Aucune liste à puces de plus de 5 éléments dans le corps du texte.



> Source de vérité : le **Guide de rédaction** (voir `GUIDE_REDACTION.md`).

| Ch. | Question structurante côté projet | Concepts du cours à activer |
|---|---|---|
| 1 | Pourquoi ce projet maintenant, dans quel cadre ? | Plan eSanté 2025-2027, BIHR, OMS 2.x, MDR |
| 2 | Quelle architecture applicative côté hôpital et passerelle ? | Pyramide d'architecture, DPI, continuum donnée→info→connaissance |
| 3 | **(Cœur)** Comment traduire legacy → standards modernes ? | HL7 v2, FHIR, IHE-PCD, KMEHR, SNOMED-CT, LOINC, MetaHub belges |
| 4 | Quelle architecture technique pour transporter les données ? | OSI, supports, sécurité réseau, ETEE, mTLS, SDN/NFV (ouverture) |
| 5 | Que captent ces dispositifs et avec quels protocoles ? | Typologie capteurs (mécanique/biopotentiel/optique/pression/chimique), méthodes de capture passives |
| 6 | Comment déployer, faire adopter, évaluer la passerelle ? | mHealth M1/M2/M3 (adapté DM), 7 facteurs adoption, statut DM IIa |
| 7 | Comment protéger les données et encadrer les responsabilités ? | RGPD, CIA + traçabilité, ETEE, APD, AIPD, gouvernance, éthique |

## 8bis. Structure du dépôt

```
Bridge/
├── README.md              # Présentation, structure, instructions de compilation
├── Makefile               # Cibles : all, rapport, pitch, cdc, clean, distclean
├── .gitignore             # Ignore auxiliaires LaTeX, PDFs intermédiaires, caches
├── .claude/               # Configuration Claude Code (settings.local.json)
│
├── docs/                  # Documentation projet (Markdown)
│   ├── PROJECT.md
│   ├── GUIDE_REDACTION.md
│   └── EQUIPMENTS.md
│
├── archive/               # Sources originales (.docx, .pptx)
├── pdf/                   # PDFs livrables finaux (cdc, rapport, pitch)
├── demo/                  # Code de la démo Docker (à coder)
│
└── src/                   # Sources LaTeX
    ├── bridge-preamble.tex    # Préambule LaTeX partagé
    ├── references.bib         # Bibliographie biblatex (35 entrées)
    ├── cdc.tex                # Squelette racine du CDC
    ├── rapport.tex            # Squelette racine du rapport
    ├── pitch.tex              # Pitch Beamer (autonome)
    ├── cdc/                   # 17 sections du CDC + glossaire
    ├── rapport/               # 10 sections du rapport
    └── figures/               # 5 figures TikZ partagées
```

Convention : tout le LaTeX est isolé dans `src/`. La compilation se fait via `latexmk -cd src/<fichier>.tex` (ou `make`), ce qui change le répertoire de travail vers `src/` pour résoudre les chemins relatifs. Les PDFs finaux sont automatiquement copiés dans `pdf/` à chaque `make`.

## 9. Conventions communes (3 livrables)

- **Palette** : bridgeblue `#1F3A68`, bridgeteal `#0FA4AF`, gris `#4A4A4A`, accent erreur `#C62828`.
- **Compilation** : `latexmk -xelatex -shell-escape <fichier>.tex`.
- **Bibliographie** : `references.bib` partagé, biblatex/biber, style IEEE.
- **Fonts** : Fira Sans (pitch), Source Serif Pro (rapport, CDC).
- **Diagrammes** : TikZ inline pour archi simple ; Mermaid exporté (PDF) pour flowchart complexe ; PlantUML pour UML détaillé.
- **Préambule partagé** : `bridge-preamble.tex` importable.

## 10. Bibliographie de référence (à consolider au fil de l'eau)

- KCE Reports (notamment KCE 362 — DPI hospitalier)
- OMS 2023 — *Classification of digital health interventions v2.0*
- Règlement (UE) 2017/745 (MDR), 2017/746 (IVDR), 2016/679 (RGPD)
- HL7 FHIR R4 — `hl7.org/fhir/R4/`
- IHE — Patient Care Device (PCD), Device Enterprise Communication (DEC)
- eHealth.fgov.be — services de base, ETEE, BIHR, MetaHub, KMEHR
- mhealthbelgium.be — pyramide M1/M2/M3
- Plan d'action interfédéral eSanté 2025-2027
- e-santewallonie.be/rgpd/ (fiches 1 à 9)
- INAMI, AFMPS
- Livres blancs : seca, GE, Philips, Mindray, MITRE
- ISO 13606 (architecture EHR), 13608 (sécurité comm.), 27001/27799 (SI santé)

## 11. Glossaire minimal (à étendre dans le CDC)

| Sigle | Signification |
|---|---|
| AFMPS | Agence Fédérale des Médicaments et Produits de Santé (Belgique) |
| AIPD / DPIA | Analyse d'Impact relative à la Protection des Données |
| APD | Autorité de Protection des Données |
| BIHR | Belgian Integrated Health Record |
| BLE | Bluetooth Low Energy |
| BM | Biomédical (technicien) |
| CIA | Confidentialité, Intégrité, Disponibilité |
| DEC | Device Enterprise Communication (profil IHE) |
| DM | Dispositif Médical |
| DMI / DPI | Dossier Médical / Patient Informatisé |
| DPO | Data Protection Officer |
| EHDS | European Health Data Space |
| ETEE | End-to-End Encryption (services eHealth) |
| FHIR | Fast Healthcare Interoperability Resources (HL7) |
| IHE | Integrating the Healthcare Enterprise |
| INS / NISS | Identifiant National de Santé / Numéro d'Identification |
| KMEHR | Kind Messages for Electronic Healthcare Record (standard belge) |
| LOINC | Logical Observation Identifiers Names and Codes |
| MDR | Medical Device Regulation (UE 2017/745) |
| mTLS | Mutual Transport Layer Security |
| OT | Operational Technology / parc opérationnel |
| PCD | Patient Care Device (profil IHE) |
| RSW | Réseau Santé Wallon |
| SDN/NFV | Software-Defined Networking / Network Function Virtualization |

## 12. Plan d'attaque retenu

1. **CDC d'abord** — il consolide les exigences pour la démo et fixe l'architecture configurable.
2. **Rapport** ensuite — il s'appuie sur le CDC pour les chapitres 3, 4, 6, 7.
3. **Pitch** en dernier — vitrine, pioche dans les visuels du rapport et du CDC, intègre la démo écran.

## 12bis. Roadmap fonctionnelle (au-delà de la démo)

Évolutions pensées en amont pour montrer que la solution n'est pas un POC fermé. À mentionner dans la conclusion du rapport, dans la section "Évolutions futures" du CDC, et en slide d'ouverture du pitch.

### F1. Plugins de traduction communautaires *(évolution majeure)*

Le parc d'équipements médicaux dans le monde est si vaste qu'aucune équipe ne peut produire nativement tous les profils. La passerelle expose une **API plugin** pour que la communauté écrive et publie ses propres règles de traduction.

**Mécanisme** :
- Un plugin = un paquet (Python wheel ou dossier déclaratif) contenant : un manifeste (`plugin.toml`), un ou plusieurs profils JSON (canal + langue + mapping), et optionnellement du code Python pour les décodages exotiques.
- À l'amorçage, la passerelle scanne un répertoire `plugins/` (ou un registre distant), valide les manifestes, charge les profils.
- Auto-discovery : un nouveau plugin déposé est détecté à chaud (file-watcher) ; le dashboard affiche son statut (chargé / erreur / désactivé).
- Validation : chaque plugin déclare les codes LOINC qu'il émet, ce qui permet à la passerelle de **refuser** un plugin qui ne respecte pas le contrat.

**Effet attendu** :
- Un fabricant ou un hôpital qui dispose d'un équipement non couvert nativement écrit son plugin et le publie.
- Communauté open source : registre public, plugins contribués, gouvernance (revue de code, qualité des mappings LOINC).
- La passerelle devient un **standard de fait** par effet de catalogue.

**Inspiration** :
- Modèle Home Assistant / HACS (catalogue d'intégrations communautaires).
- Modèle Telegraf / Logstash (plugins entrée + sortie).
- Modèle WordPress / npm pour la gouvernance.

**Statut dans la démo** : la **mécanique de chargement** est implémentée (un plugin minimal est livré comme exemple). Le **registre communautaire** est mentionné en perspective.

### F2. (Autres évolutions futures à formaliser plus tard)

- Anomaly detection en bord (IA légère sur les flux pour pré-flagger des aberrations).
- Orchestration SDN d'un parc de gateways (cf. ouverture conclusion rapport).
- Fédération européenne EHDS (European Health Data Space).
- Adapter pour DICOM (imagerie point-of-care).

## 13. Décisions à clarifier au fil du projet (non-bloquantes)

- [ ] Datasheets précises à utiliser comme appui documentaire (URLs/PDF Philips, Masimo, B. Braun, Vyaire…) — à rechercher.
- [ ] Stockage des journaux : SQLite local + export ? Niveau de rétention ?
- [ ] Démo (15 min) : enregistrée (vidéo intégrée Beamer) ou live (`docker compose up` projeté) ? Recommandation : **live** car tout dockerisé local est robuste.
- [x] Statut DM : **non DM**, middleware d'intégration. (cf. § 5)
- [x] Stack démo : **Docker Compose, tout en local, 4 simulateurs**. (cf. § 6)

## 13bis. Note de reprise après redémarrage (2026-05-04)

> Le coordinateur a redémarré Claude Code pour charger les agents `bridge-*`. Deux agents tournaient en background au moment du redémarrage et ont été interrompus. Leur travail sur disque est préservé mais leur rapport de fin a été perdu.

### À inspecter au retour (avant de relancer quoi que ce soit)

1. **Infrastructure LaTeX** (agent infra-LaTeX) — vérifier l'existence et la qualité de :
   - `bridge-preamble.tex`
   - `rapport.tex`, `pitch.tex`, `cdc.tex`
   - `references.bib`
   - `Makefile`
   - Dossiers `rapport/`, `cdc/`, `figures/`
   - Tester la compilation des 3 squelettes (au moins celle du squelette vide)

2. **CDC v1 sections 0-7** (agent CDC) — vérifier l'existence et la qualité de :
   - `cdc/00-page-garde.tex`
   - `cdc/01-contexte.tex` (vision chaos→ordre, BIHR, plan eSanté 2025-2027)
   - `cdc/02-perimetre.tex` (in/out scope, RACI)
   - `cdc/03-solution.tex` (vision produit, use cases, archi 4 vues)
   - `cdc/04-exigences-fonctionnelles.tex` (~33 EF par couche Adapter/Parser/Mapper/Transport/Publication/Dashboard/Plugins)
   - `cdc/05-exigences-non-fonctionnelles.tex` (~8-10 ENF mesurables)
   - `cdc/06-contraintes.tex` (réglementaires + techniques + organisationnelles)
   - `cdc/07-architecture-technique.tex` (schéma, composants, stack Python, profils JSON, plugins)

3. **Compléter** ce qui manque ou redémarrer ce qui n'a pas été produit.

### Ensuite

- Avec les agents `bridge-*` chargés, lancer la suite : sections 8-17 du CDC, puis le rapport, puis le pitch.



- **2026-05-04** — Création initiale.
- **2026-05-04** — Refonte : passerelle configurable multi-couches, stack Python, CDC pour la démo, pitch 10 min + démo écran, vision narrative "chaos → ordre".
- **2026-05-04** — Précisions : passerelle = **middleware non-DM, transparent et configurable** (entrée/sortie déclarative). Démo = **15 min totale** (10 pitch + 5 démo séparée). Démo = **tout dockerisé local**, 4 conteneurs simulant des équipements représentatifs (moniteur Philips/GE TCP, glucomètre Masimo BLE/MQTT, spiromètre Vyaire fichier XML, pompe B. Braun RS-232). Datasheets réelles à utiliser comme source.
- **2026-05-04** — Philosophie produit reformulée en **3 questions / 2 phases** : handshake technique (canal + langue) géré par le développeur, configuration métier (destination de sortie) gérée par l'admin. Dashboard = **outil de config + supervision OT, pas un visualiseur de vitals patient**. Principe de **minimisation** : alertes et logs ne contiennent **aucune donnée personnelle**, uniquement des informations techniques liées à l'équipement.
