# Spécification UX du Dashboard

> Document directeur pour le **Sprint 5** de la démo. Le dashboard doit aider le cerveau à comprendre vite, agir sûrement, et s'approprier l'outil sans documentation.

## Principe directeur

> **Charge cognitive minimale, information dense, hiérarchie visuelle claire.**

Le dashboard est utilisé par deux profils :
- **Technicien biomédical / OT** : surveille le parc, configure les profils, traite les anomalies.
- **Auteur du projet (démo)** : montre les flux en live au jury sans naviguer.

Les deux ont besoin de **comprendre l'état global en 3 secondes** et **trouver la donnée pertinente en 2 clics**.

## Principes UX retenus

### 1. Loi de proximité (Gestalt)
Grouper visuellement les éléments liés. Un équipement est une **carte unique** qui rassemble nom, statut, dernière comm, compteur, contexte d'erreur. Pas d'éparpillement entre tableaux.

### 2. Loi de similarité
Mêmes couleurs pour mêmes types de statuts, partout. Vert = nominal, orange = anomalie, rouge = déconnecté, gris = inconnu. Aucune autre signification de couleur dans l'interface.

### 3. Loi de Hick-Hyman (limiter les choix)
Maximum 5 actions principales visibles à un instant donné. Le reste est accessible via menus contextuels ou pages dédiées.

### 4. Chunking 7±2
L'écran ne présente jamais plus de 7 éléments distincts au premier niveau visuel. Au-delà, regroupement, pagination ou repli.

### 5. Affordances claires
Boutons d'action en `bridgeteal` (couleur primaire), boutons destructifs en `bridgealert`, désactivés en gris. Pas de lien-bouton ambigu.

### 6. Feedback immédiat
Chaque action utilisateur déclenche un retour visuel en moins de 200 ms. WebSocket pour les statuts temps réel. Toast de confirmation ou d'erreur après chaque modification.

### 7. Reconnaissance plutôt que rappel
Les codes LOINC, identifiants équipements, formats de profil sont toujours accompagnés d'une libellé humain. Tooltip au survol pour les sigles.

## Architecture des écrans

### Écran 1 : Vue d'ensemble (page d'accueil `/`)

**Objectif** : voir l'état complet en 3 secondes.

```
┌─────────────────────────────────────────────────────────────────┐
│  IoT Edge Bridge                       [Logo]  [Configuration]  │
│  Dashboard de supervision                                        │
├─────────────────────────────────────────────────────────────────┤
│  Vue d'ensemble                                                  │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │ ●  4 équipements connectés                                  │ │
│  │ ●  127 messages traités sur les 60 dernières minutes        │ │
│  │ ●  0 message en quarantaine                                 │ │
│  │ ●  2 plugins chargés                                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Équipements (4)                                                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│  │ Philips    │ │ Masimo     │ │ Welch Allyn│ │ Drager     │    │
│  │ MX450      │ │ Radical-7  │ │ CP150      │ │ Evita V500 │    │
│  │ ● Vert     │ │ ● Vert     │ │ ● Orange   │ │ ● Rouge    │    │
│  │ TCP HL7v2  │ │ MQTT       │ │ Fichier    │ │ RS-232     │    │
│  │ 42 msg/h   │ │ 38 msg/h   │ │ 12 anomalies│ │ Inactif    │    │
│  │ il y a 3 s │ │ il y a 5 s │ │ il y a 2 m │ │ il y a 8 m │    │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
│                                                                  │
│  ┌─ Activité récente ────────────────────────────────────────┐  │
│  │ 12:34:51  philips-mx450  Observation publiee (HTTP 201)   │  │
│  │ 12:34:48  masimo-radical7  Observation publiee (HTTP 201) │  │
│  │ 12:34:40  welchallyn-cp150  Valeur hors plage, quarantaine│  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [Légende :  ● Nominal  ● Anomalie  ● Déconnecté  ● Inconnu  ]  │
└─────────────────────────────────────────────────────────────────┘
```

**Composants** :
- **Bandeau de compteurs globaux** (4 chiffres clés en haut).
- **Grille de cartes équipement** (1 carte par dispositif, 4 colonnes sur desktop, 2 sur tablette, 1 sur mobile).
- **Flux d'activité récente** (10 derniers événements, sans donnée patient).
- **Légende permanente** des couleurs en bas.

**Interactions** :
- Clic sur une carte → page détail équipement.
- Refresh automatique via WebSocket (pas de bouton refresh).
- Filtrage par statut (4 boutons-pastilles en haut).

### Écran 2 : Détail équipement (`/devices/{id}`)

**Objectif** : comprendre pourquoi un statut a changé en 5 secondes.

Quatre panneaux empilés :
1. **En-tête** : nom équipement, statut, dernière communication, profil JSON utilisé (lien vers config).
2. **Métriques temps réel** : 4 mini-graphiques sparkline (latence p95, débit messages/min, taux erreur, taux quarantaine) sur 60 min.
3. **Timeline d'événements** : chronologie scrollable des 50 derniers événements techniques (connexion, déconnexion, erreur de format, valeur hors plage, retry réussi). Aucune donnée patient.
4. **Alertes ouvertes** : encadré rouge si rouge, orange si orange, avec contexte indicatif (ex. "n'émet plus depuis 8 min" ou "12 valeurs hors plage de plausibilité sur 100 dernières trames").

**Interactions** :
- Bouton "Renvoyer un test" (envoie un ping au simulateur).
- Bouton "Voir les logs filtrés" (lien vers `/logs?device=...`).
- Bouton "Configurer" (lien vers `/config/{id}`).

### Écran 3 : Configuration profils (`/config`)

**Objectif** : modifier un profil JSON sans connaître la syntaxe JSON.

- Liste des profils avec statut "chargé" / "erreur de validation" / "désactivé".
- Édition guidée par formulaire (champs : ID, canal, langue, mapping LOINC, plages plausibilité). Pas d'éditeur JSON brut au premier niveau.
- Bouton "Vue avancée" pour basculer en éditeur JSON brut (pour utilisateurs experts).
- Validation Pydantic en direct, surlignage des erreurs.
- Bouton "Recharger" qui déclenche le hot-reload sans redémarrage.

### Écran 4 : Logs (`/logs`)

**Objectif** : tracer un problème ou une activité spécifique.

- Filtres : équipement, niveau (info/warn/error), période (live, 1h, 24h, 7j).
- Tableau dense, 50 lignes par page.
- Recherche full-text dans les messages techniques.
- Bouton "Exporter JSON" (pour partage ou archivage).
- **Aucune valeur clinique affichée**, vérifié par grep automatisé sur les codes LOINC à la sérialisation.

### Écran 5 : Plugins (`/plugins`)

**Objectif** : visualiser le catalogue communautaire et son état.

- Liste des plugins chargés (manifest, statut, codes LOINC déclarés).
- Bouton "Recharger" pour scan manuel du dossier `plugins/`.
- Détail d'un plugin : manifeste TOML affiché, métriques (messages traités, erreurs).
- Section "Plugins en erreur" si la validation a échoué.

## Charte visuelle

### Palette (cohérente avec les livrables LaTeX)

| Couleur | Hex | Usage |
|---|---|---|
| `bridgeblue` | `#1F3A68` | Titres, liens, en-têtes de tableaux |
| `bridgeteal` | `#0FA4AF` | Boutons primaires, accents, hover |
| `bridgegreen` | `#2E7D32` | Statut nominal |
| `bridgewarn-amber` | `#F59E0B` | Statut anomalie (orange) |
| `bridgealert` | `#C62828` | Statut déconnecté, alertes destructives |
| `bridgegray` | `#4A4A4A` | Texte secondaire, bordures |
| `bridgesoft` | `#F2F6FB` | Fond doux, zébrures |
| `bridgeinfo-soft` | `#E3F4F4` | Encadrés informatifs |

### Typographie

- **Police** : Inter ou Fira Sans (sans-serif lisible) chargée localement (pas de CDN externe).
- **Hiérarchie** : 4 tailles maximum (titre page 24px, titre section 18px, corps 14px, métadonnées 12px).
- **Pas d'italique** dans les contenus actifs (réservé aux légendes).
- **Lignes de 65 caractères max** dans les blocs de texte longs.

### Composants

- **Cartes** : ombre douce, bordure 1px en `bridgegray-soft`, coins arrondis 6px.
- **Boutons** : padding 8px 16px, fonte semi-bold, transition couleur 150ms.
- **Badges statut** : pastille colorée 10px + libellé court.
- **Tooltips** : fond sombre, texte blanc, apparition au survol après 300ms.
- **Toasts** : coin inférieur-droit, auto-dismiss après 4 s, fermable manuellement.

## Accessibilité

- Contraste WCAG AA minimum (texte sur fond pâle ≥ 4.5:1).
- Navigation clavier complète (Tab, Enter, Escape).
- Indicateurs de statut **avec couleur ET icône ET texte** (pas que la couleur, pour daltoniens).
- Tous les éléments interactifs ont un `aria-label`.
- Polices > 12px partout.

## Comportement temps réel

- **WebSocket** sur `/ws` : push des événements à toutes les pages.
- **Heartbeat** côté client : si la connexion WS est perdue, bandeau "Connexion perdue, reconnexion..." en haut.
- **Refresh fallback** : polling toutes les 10 s si WS indisponible.

## Stack technique (Sprint 5)

- **FastAPI** + **Jinja2** (rendu serveur).
- **HTMX** : interactions partielles (pas de SPA lourd).
- **Alpine.js** (optionnel, pour les widgets interactifs côté client).
- **Tailwind CSS** ou CSS custom léger (pas de framework JS lourd).
- **WebSocket FastAPI** natif pour le push temps réel.

## Onboarding

À la première visite :
1. Bandeau d'accueil "Bienvenue sur le Bridge. Cliquez ici pour un tour rapide."
2. Tour guidé en 4 étapes (vue d'ensemble → carte équipement → détail → configuration), 1 popover à la fois.
3. Bouton "Skip" toujours présent.
4. Tour réafichable depuis `/help`.

## Anti-pattern explicites (à NE JAMAIS faire)

| Anti-pattern | Pourquoi pas |
|---|---|
| Afficher une valeur clinique d'un patient | Viole la règle de minimisation |
| Encadré rouge sans texte explicatif | Anxiogène sans valeur informative |
| Plus de 5 actions au premier niveau | Loi de Hick |
| Couleurs autres que la palette | Confusion |
| Animations > 300 ms | Ralentit la perception |
| Modal bloquante pour confirmation triviale | Friction inutile |
| Texte technique sans tooltip explicatif | Exclusion des non-experts |

## Critères de recette du dashboard

À cocher avant de marquer le sprint 5 terminé :
- [ ] Vue d'ensemble visible et complète en moins de 3 s sur localhost.
- [ ] Refresh des statuts sans rechargement de page (WebSocket).
- [ ] Édition d'un profil JSON via formulaire guidé fonctionnelle.
- [ ] Aucune valeur LOINC dans les logs ni le DOM rendu (vérifié par grep).
- [ ] Navigation clavier complète testée.
- [ ] Contraste WCAG AA validé sur les couleurs principales.
- [ ] Tour guidé fonctionnel à la première visite.
- [ ] Tooltip sur tous les sigles (LOINC, FHIR, MLLP, etc.).
