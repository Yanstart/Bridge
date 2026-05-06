# Guide de rédaction — Passerelle d'Interopérabilité Edge (IoT Bridge)
## Mapping de ton projet aux 7 chapitres du cours TS6

> **Principe directeur** : chaque chapitre du rapport doit montrer que tu as **mobilisé une notion précise du cours** pour résoudre **un problème concret** de ton projet. Pas de placage théorique : pour chaque concept cité, une application au projet.

---

## Vue d'ensemble — comment ton projet active les 7 chapitres

| Ch. | Question que ton projet doit traiter | Ressource clé à activer |
|---|---|---|
| 1 | Pourquoi ce projet **maintenant**, dans quel cadre ? | Plan eSanté 2025-2027, BIHR, OMS 2.x |
| 2 | Quelle **architecture applicative** côté hôpital et passerelle ? | Pyramide d'architecture, DPI |
| 3 | Comment **traduire** legacy → standards modernes ? | HL7 v2, FHIR, IHE, KMEHR, SNOMED |
| 4 | Quelle **architecture technique** pour transporter les données ? | OSI, supports, sécurité réseau |
| 5 | Que **captent** ces dispositifs legacy et comment ? | Typologie capteurs, protocoles physiques |
| 6 | Comment **déployer, faire adopter, évaluer** la passerelle ? | mHealth M1/M2/M3, 7 facteurs adoption |
| 7 | Comment **protéger** les données et **encadrer** les responsabilités ? | RGPD, CIA, ETEE, gouvernance |

---

## Chapitre 1 — Introduction & contexte (déjà rédigé : à muscler)

### Ce que tu as déjà
- Définition e-health (KCE) ✓
- Catégorie OMS 2.0 ✓
- Problématique legacy (MDR, durée de vie, RS-232) ✓
- Choix de FHIR ✓

### À ajouter pour gagner en solidité
1. **Référence explicite à la stratégie belge** : cite le *Plan d'action interfédéral eSanté 2025-2027* et l'INAMI comme organisation responsable du BIHR. Tu te positionnes ainsi comme une **brique d'exécution** d'une stratégie nationale.
2. **Justification du chiffre « 0% au stade 4 »** : précise la source (HIMSS EMRAM ? KCE 362 ? rapport sectoriel ?). Si tu n'as pas de source ferme, remplace par « la majorité des hôpitaux échantillonnés ne disposent pas encore d'une intégration automatisée des dispositifs médicaux ».
3. **Une phrase sur la finalité clinique** : ta passerelle ne sert pas la technique, elle sert *la qualité et la continuité des soins, la médecine prédictive, et la réduction de la charge administrative* (vocabulaire du cours).
4. **Nettoyer le formatage** : les `** Cycle**` et `Locked Config»` — il faut une mise en forme propre.

---

## Chapitre 2 — Applications mobiles et plateformes de santé connectée

### Question structurante
> *Où ta passerelle se situe-t-elle dans la pyramide d'architecture, et avec quelles applications elle dialogue ?*

### Concepts du cours à activer
- **Pyramide à 4 niveaux** : Métier → Fonctionnel → Applicatif → Technique
- **DPI hospitalier** : 8 fonctionnalités clés, principe *only once*
- **Continuum d'intelligence des données** : donnée brute → information → connaissance → décision

### Contenu spécifique à ton projet
1. **Positionnement dans la pyramide** :
   - *Métier* : amélioration de la qualité des soins via complétude des données patient.
   - *Fonctionnel* : automatisation du processus « capture → DPI » qui aujourd'hui est manuel (saisie soignant).
   - *Applicatif* : ta passerelle est un **middleware** qui s'insère entre les **applications dispositifs** (côté équipement) et le **DPI hospitalier** + **MetaHub/BIHR** (côté plateforme).
   - *Technique* : matériel edge (Raspberry Pi, NUC industriel, gateway dédiée) + stack logicielle.

2. **Interface de monitoring (mentionnée dans ton plan)** :
   - Tableau de bord pour le **technicien biomédical** : état des dispositifs connectés, file de messages, erreurs de mapping.
   - Alertes : dispositif déconnecté, certificat expiré, échec d'envoi FHIR.
   - C'est une **app de supervision**, pas une app patient.

3. **Continuum des données illustré sur ton projet** :
   - *Donnée* : trame RS-232 brute « 0x32 0x35 0x6D ... »
   - *Information* : « SpO₂ = 96 % à 14:23 »
   - *Connaissance* : « SpO₂ stable sur 24h, dans les normes »
   - *Décision* : « pas d'alerte clinique requise »

### Sources / standards à citer
- KCE Report 362 (DPI hospitalier)
- Architecture H+ ou OMNIPRO (DPI cités dans le cours)

---

## Chapitre 3 — Intégration des dispositifs connectés (chapitre cœur de ton projet)

### Question structurante
> *Comment traduire les sorties propriétaires de dispositifs legacy en standards d'interopérabilité acceptés par le BIHR ?*

### Concepts du cours à activer (5 standards à expliquer)
- **HL7 v2** (messages ORU pour résultats d'observation, segments MSH/PID/OBR/OBX)
- **HL7 FHIR** (ressources, REST, JSON)
- **DICOM** (imagerie)
- **SNOMED-CT** (terminologie clinique, concepts/relations)
- **KMEHR** (standard belge, transactions sur eHealth Platform)
- **IHE** : profils d'intégration coordonnés
- **Hubs & MetaHub belges** : Cozo, ARH, VZN, RSW, RSB

### Contenu spécifique à ton projet
1. **Les trois couches d'interopérabilité** (à mobiliser par ta passerelle) :
   - **Technique** : capture (RS-232, USB, Ethernet, BLE legacy, fichier CSV/XML)
   - **Syntaxique** : structuration en HL7 v2 ORU^R01 puis transformation en ressources FHIR (Patient, Device, Observation, DiagnosticReport)
   - **Sémantique** : codification des observations en **SNOMED-CT** ou **LOINC** (ex : « pression artérielle systolique » = LOINC 8480-6)

2. **Architecture de mapping** (cœur technique du chapitre 3) :
   ```
   [Dispositif legacy] → [Adaptateur protocole] → [Parser propriétaire]
       → [Mapper sémantique SNOMED/LOINC] → [Sérialiseur FHIR]
       → [Client API REST authentifié] → [eHealth Platform / DPI]
   ```

3. **Workflow d'intégration au paysage belge** :
   - Identification patient via **NISS / eID** (services de base eHealth)
   - Soumission au **DPI hospitalier** via API FHIR locale
   - Publication conditionnelle au **MetaHub** via le hub régional (RSW pour Wallonie)
   - Consultable in fine via **MaSanté.be** (portail patient)

4. **Profils IHE pertinents** à citer :
   - **PCD (Patient Care Device)** : profil dédié à l'intégration des dispositifs médicaux dans l'EHR — *à creuser, c'est exactement ton sujet*
   - **DEC (Device Enterprise Communication)** : transmet les données vitales du dispositif au système d'information

### Sources / standards à citer
- hl7.org/fhir (ressources Device, Observation, Patient, DeviceMetric)
- ihe.net (profils PCD, DEC)
- ehealth.fgov.be/standards/kmehr/en/transactions

---

## Chapitre 4 — Architecture technologique

### Question structurante
> *Quelle architecture réseau et quels protocoles assurent un transport déterministe, fiable et sécurisé entre la passerelle et les systèmes consommateurs ?*

### Concepts du cours à activer
- **Modèle OSI** (7 couches) — pour situer chaque protocole utilisé
- **Mesures réseau** : latence, débit, bande passante
- **Compromis selon usage** : un télémonitoring chronique ≠ un bloc opératoire
- **Supports** : Ethernet, WiFi, fibre, 5G
- **Sécurité** : TLS, VPN, segmentation, chiffrement bout-en-bout

### Contenu spécifique à ton projet
1. **Stack OSI de ta passerelle** (à présenter en tableau) :

| Couche | Côté dispositif (legacy) | Côté plateforme (moderne) |
|---|---|---|
| 7 Application | Format propriétaire / CSV / HL7 v2 | HL7 FHIR (REST) |
| 6 Présentation | ASCII / binaire propriétaire | JSON / OAuth 2.0 |
| 5 Session | — / SIP éventuel | HTTPS persistante |
| 4 Transport | Série / TCP brut | **TCP + TLS 1.3** |
| 3 Réseau | — / IPv4 local | IPv4/IPv6 routée |
| 2 Liaison | RS-232, RS-485, Bluetooth Classic | Ethernet, WiFi WPA3 |
| 1 Physique | DB-9, USB, ondes 2,4 GHz | Cat 6, fibre, 5G |

   → Ta passerelle est exactement un **traducteur de pile** : elle absorbe une pile « pauvre » et émet sur une pile « riche ».

2. **Choix d'architecture edge** (justification) :
   - Pourquoi *edge* et pas tout cloud ? Latence, souveraineté des données, robustesse en cas de coupure WAN, conformité RGPD (minimisation).
   - Pourquoi *gateway physique* et pas software-only ? Compatibilité matérielle (ports série), isolation des dispositifs critiques.

3. **Sécurité réseau** (à articuler avec chap. 7) :
   - **Segmentation** : VLAN dédié dispositifs médicaux ; ta passerelle est le seul point de sortie.
   - **Chiffrement en transit** : TLS 1.3 avec mTLS (authentification mutuelle) vers le DPI.
   - **Chiffrement bout-en-bout** : services **ETEE** d'eHealth (ETKDepot, KGSS) si destinataire connu/inconnu.
   - **Authentification** : certificat eHealth de l'institution.

4. **SDN dans ton projet** (ta marque personnelle) :
   - Si tu veux donner une touche orientée réseaux : argumente comment une approche **SDN/NFV** permettrait d'orchestrer un parc de passerelles dans un grand hôpital (provisioning, mises à jour, micro-segmentation dynamique). Cela montre que tu vois plus loin que l'unitaire.

### Sources / standards à citer
- Plate-forme eHealth – services ETEE (cours, slide cryptage end-to-end)
- ISO 13608 / 27799

---

## Chapitre 5 — Capteurs et dispositifs de mesure

### Question structurante
> *Quels types de dispositifs ta passerelle doit-elle prendre en charge, quelles grandeurs physiques mesurent-ils, et quelles méthodes de capture utiliser sans intrusion matérielle ?*

### Concepts du cours à activer
- **Définition canonique** : capteur = transformateur grandeur physique → signal électrique
- **Typologie par grandeur physique** : mécanique, électrique/biopotentiel, optique, pression, chimique, température
- **Tableau « mesure → capteur → bénéfice santé »**

### Contenu spécifique à ton projet
1. **Cible matérielle prioritaire** (à choisir 3-4 familles, pas tout) :

| Famille de dispositif | Grandeur(s) | Sortie typique legacy | Bénéfice clinique |
|---|---|---|---|
| Moniteur multiparamétrique | ECG, SpO₂, TA, FR, T° | RS-232, HL7 v2 propriétaire | Continuité des paramètres vitaux au DPI |
| Pompe à perfusion | Débit, volume injecté | Série binaire, parfois CAN bus | Traçabilité médicamenteuse |
| Spiromètre | Volumes/débits respiratoires | USB, fichiers XML | Suivi BPCO/asthme |
| Glucomètre de chevet | Glycémie | Bluetooth Classic, USB | Glycémies horodatées au dossier |
| Balance médicale (ex: seca) | Poids, IMC | Série, BLE legacy | Nutrition, dialyse |

2. **Méthodes de capture sans intrusion matérielle** (le « non-invasif » côté équipement) :
   - **Capture passive sur port série** : sniffer série déclenché à l'événement, sans modifier le dispositif → pas de perte du marquage CE.
   - **Tap réseau passif** : si dispositif déjà sur Ethernet propriétaire (TAP en SPAN, lecture d'export FTP/SMB).
   - **Lecture de fichiers exportés** : surveillance d'un dossier réseau où le dispositif dépose ses CSV/XML.
   - **OCR sur écran** *(dernier recours)* : pour dispositifs sans aucune sortie numérique. Cite-le mais montre-en les limites (fiabilité).

3. **Lien explicite avec le DPI** : « Les résultats des examens sur dispositifs médicaux se retrouvent dans le DPI » — c'est exactement la phrase du cours, et c'est le mandat de ta passerelle.

### Sources à citer
- Livres blancs constructeurs (seca, GE, Philips, Mindray)
- Documentation IHE-PCD

---

## Chapitre 6 — Implémentation, adoption, évaluation

### Question structurante
> *Comment déployer ta passerelle dans un hôpital, en faire adopter l'usage, et prouver qu'elle apporte de la valeur ?*

### Concepts du cours à activer
- **Pyramide mHealth.belgium M1 / M2 / M3** (note : c'est conçu pour les apps, mais tu peux l'adapter à ton dispositif)
- **7 facteurs d'adoption réussie**
- **Méthodes d'évaluation** : clinique, organisationnelle, médico-économique

### Contenu spécifique à ton projet
1. **Phases d'implémentation** (à présenter chronologiquement) :
   - Phase 0 : audit du parc dispositifs hospitaliers, identification des familles cibles
   - Phase 1 : POC sur un service (ex : USI ou pneumo) avec un seul type de dispositif
   - Phase 2 : extension à 3-5 familles, intégration au DPI test
   - Phase 3 : pilote multisite, raccord au MetaHub
   - Phase 4 : industrialisation et passage en production

2. **Conformité dispositif médical** *(point critique de ton sujet)* :
   - Ta passerelle est-elle elle-même un **dispositif médical** au sens MDR 2017/745 ? **Probablement classe IIa** si elle traite des données utilisées pour le diagnostic. À discuter explicitement, c'est ce qui te distingue d'un projet IT classique.
   - Elle nécessite donc : marquage CE, dossier technique, surveillance post-commercialisation.
   - Référence : cite l'AFMPS (Agence belge des médicaments et produits de santé).

3. **Les 7 facteurs d'adoption appliqués à ta passerelle** :

| Facteur | Application concrète |
|---|---|
| Compréhension/formation | Formation des techniciens biomédicaux et IT hospitaliers |
| Interopérabilité | Cœur de ton projet, FHIR + KMEHR |
| Engagement parties prenantes | Co-conception avec biomédicaux, médecins, infirmiers, DPO |
| Accessibilité/UX | Tableau de bord supervision simple |
| Support/maintenance | Mises à jour OTA, monitoring centralisé |
| Conformité | MDR, RGPD, certifications eHealth |
| Intégration aux flux | Pas de saisie manuelle ajoutée pour les soignants |

4. **Évaluation** (KPIs concrets) :
   - **Technique** : taux de transmission réussie, latence bout-en-bout, taux d'erreur de mapping.
   - **Organisationnel** : minutes/jour économisées sur la saisie manuelle, taux de re-saisie évité.
   - **Clinique** : complétude du dossier patient (% de paramètres vitaux automatiquement présents), délai entre mesure et disponibilité au médecin.
   - **Médico-économique** : coût d'acquisition + intégration vs coût d'un parc neuf de dispositifs nativement connectés. **C'est ton argument-massue** : la passerelle évite de jeter 15 ans d'investissement matériel.

### Sources à citer
- mhealthbelgium.be/fr/pyramide-de-validation
- INAMI, AFMPS

---

## Chapitre 7 — Éthique, sécurité et confidentialité

### Question structurante
> *Comment garantir confidentialité, intégrité, disponibilité, traçabilité et conformité légale tout au long du cycle de vie des données qui transitent par ta passerelle ?*

### Concepts du cours à activer
- **Triade CIA** : Confidentialité, Intégrité, Disponibilité (+ traçabilité)
- **RGPD** : consentement, minimisation, conservation, notification de fuite
- **Cycle de vie de la donnée** : écriture, lecture, modification, conservation, destruction
- **Services ETEE** d'eHealth Platform
- **Matrice d'accès, relation thérapeutique** (concepts belges)

### Contenu spécifique à ton projet
1. **Cartographie des risques de ta passerelle** (à organiser en tableau STRIDE ou simple liste) :

| Risque | Surface | Mesure |
|---|---|---|
| Interception sur LAN hospitalier | Couche 2-3 | VLAN dédié, mTLS sortie |
| Compromission de la passerelle | OS gateway | OS minimal, signatures, lecture seule rootfs |
| Injection de fausses observations | API FHIR | Authentification par certificat eHealth |
| Fuite de données en transit | Internet | Chiffrement TLS 1.3 + ETEE |
| Perte d'intégrité du mapping | Logique applicative | Tests unitaires, validation FHIR avant émission |
| Indisponibilité | Coupure réseau | Buffering local avec rejeu, file persistante |

2. **Conformité RGPD** (check-list e-santé Wallonie, déjà dans le cours) :
   - Registre des traitements (la passerelle traite des données de santé, donc *catégorie particulière*, art. 9 RGPD)
   - Analyse d'impact (AIPD/DPIA) : recommandée vu le risque
   - Contrat de sous-traitance avec l'éditeur de la passerelle
   - Procédure de notification de fuite à l'**APD** (72 h)
   - Information du patient et matrice d'accès

3. **Question éthique spécifique à ta passerelle** :
   - **Qualité des données et responsabilité clinique** : si le mapping introduit une erreur (ex : mauvaise unité), qui est responsable ? Le fabricant du dispositif ? L'éditeur de la passerelle ? L'hôpital ? Discute la chaîne de responsabilité.
   - **Consentement** : le patient consent-il spécifiquement au passage de ses données via une passerelle tierce ? (Réponse : couvert par le consentement général au DPI hospitalier, mais à mentionner dans la politique de confidentialité.)
   - **Risque de surveillance excessive** : avec la facilité de capture, ne va-t-on pas vers une « datafication » du patient au-delà du strict besoin clinique ? Argument de **minimisation**.

4. **Gouvernance** :
   - Rôles : *responsable de traitement* = l'hôpital ; *sous-traitant* = l'éditeur de la passerelle.
   - DPO de l'hôpital impliqué dès la conception (*privacy by design*, art. 25 RGPD).

### Sources à citer
- e-santewallonie.be/rgpd/ (fiches 1 à 9)
- ehealth.fgov.be (services ETEE)
- ISO 27001 / 27799 / 13608

---

## Conclusion suggérée

Ta conclusion devrait articuler trois niveaux :

1. **Niveau technique** : tu as démontré qu'une passerelle edge multi-protocoles peut transformer le parc legacy en source FHIR-native sans toucher au matériel certifié.
2. **Niveau systémique** : ta solution adresse un goulet d'étranglement national identifié par le plan eSanté 2025-2027 et accélère le passage des hôpitaux belges aux stades supérieurs de maturité numérique.
3. **Niveau prospectif** : ouvre sur le **scaling SDN** d'un parc de gateways, l'intégration de l'**IA en bord** (anomaly detection sur signaux vitaux avant transmission), et la **fédération des hubs** au niveau européen (EHDS – European Health Data Space).

---

## Annexe — Suggestions pour la Figure B (architecture technique)

Ton schéma devrait faire apparaître **5 zones** de gauche à droite, séparées par les frontières de confiance :

```
┌──────────────┐  ┌─────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────┐
│ Dispositifs  │  │ Passerelle  │  │ Réseau hôpital│  │ Plateforme   │  │ MetaHub  │
│  legacy      │  │  Edge       │  │  (LAN sécur.) │  │  eHealth     │  │ + DPI    │
│              │  │             │  │               │  │              │  │          │
│ Moniteur     │  │ - Adaptateur│  │ TLS 1.3 mTLS  │  │ ETEE / KGSS  │  │ FHIR API │
│ Pompe        │──│   protocole │──│   over WiFi   │──│ Auth certif. │──│ KMEHR    │
│ Spiro.       │  │ - Mapper    │  │   ou Eth.     │  │ eHealth      │  │          │
│ Glucomètre   │  │   SNOMED    │  │               │  │              │  │ Hub RSW  │
│              │  │ - Buffer    │  │               │  │              │  │          │
│ RS-232/USB/  │  │ - Sérial.   │  │               │  │              │  │          │
│ BLE/CSV      │  │   FHIR      │  │               │  │              │  │          │
└──────────────┘  └─────────────┘  └───────────────┘  └──────────────┘  └──────────┘
   Couche 1-7        Application       Couche 4 TLS       Couche 7 FHIR    Niveau métier
   propriétaires      traduction       chiffrement       authentif. forte   continuité
```

Annote chaque flèche avec **le format/protocole** qui transite (CSV, HL7v2, FHIR JSON, KMEHR XML…).

---

## Check-list de qualité avant rendu

- [ ] Chaque chapitre cite **au moins un concept précis** du cours (avec nom : « pyramide d'architecture », « profil IHE PCD », « services ETEE »…)
- [ ] Chaque concept cité est **appliqué** à ton projet (pas juste défini)
- [ ] Les standards (FHIR, HL7, SNOMED, KMEHR, DICOM, IHE) apparaissent à des **endroits différenciés** (chap. 3 ≠ chap. 4 ≠ chap. 7)
- [ ] Le **MDR 2017/745** est traité au chap. 6 (conformité dispositif médical) en plus du chap. 1
- [ ] Le **RGPD** + services **ETEE** + **APD** apparaissent au chap. 7
- [ ] Le **BIHR** + **MetaHub** + **plan eSanté 2025-2027** sont nommés
- [ ] La **figure A** (processus métier) et la **figure B** (architecture technique) sont distinctes — l'une montre le « quoi » côté soin, l'autre le « comment » côté technique
- [ ] Bibliographie : sources citées du cours (KCE 362, eHealth Platform, e-santé Wallonie, mhealthbelgium) **et** sources externes vérifiables (HL7.org, IHE.net, INAMI)
- [ ] Formatage docx propre (ni `**` parasites, ni guillemets cassés)
