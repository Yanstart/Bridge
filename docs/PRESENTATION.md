# Mode d'emploi presentation

Comment projeter `pdf/pitch.pdf` le jour J, naviguer entre les slides, et
afficher les notes orateur sur un second ecran.

## Boutons de navigation cliquables

En bas a droite de chaque slide, trois boutons cliquables (en bleu bridge) :

| Bouton | Action | Compatible |
|---|---|---|
| `⮘` | Slide precedente | Tous lecteurs PDF qui supportent les liens (Acrobat, Chrome, Edge, Firefox, SumatraPDF...) |
| `⛶` | Bascule plein ecran | Adobe Acrobat Reader/Pro uniquement |
| `⮚` | Slide suivante  | Tous lecteurs PDF qui supportent les liens |

Le numero de slide courant et le total sont affiches a droite des boutons (`12/18`).

> **Si le bouton plein ecran ne fait rien :** ton lecteur n'est pas Acrobat. Utilise alors `Ctrl+L` (Acrobat), `F11` (Chrome/Edge), ou les fleches du clavier (toujours disponibles).

## Generer les deux PDFs

```bash
make pitch          # PDF de projection (slides seules)
make pitch-notes    # PDF dual-ecran (slide a gauche + notes a droite)
```

Resultat dans `pdf/` :

- `pitch.pdf` : **a projeter** sur le grand ecran. 18 slides 16:9, plein ecran automatique a l'ouverture.
- `pitch-notes.pdf` : pour **toi**, sur ton portable. Chaque page contient la slide (gauche) et tes notes orateur (droite). Genere par `pgfpages` avec `show notes on second screen=right`.

## Trois modes de projection

### A. Adobe Acrobat Reader (le plus simple, Windows)

1. Ouvre `pdf/pitch.pdf` dans Acrobat (s'ouvre en plein ecran automatiquement).
2. Si pas en plein ecran : `Ctrl+L`.
3. Sortie plein ecran : `Esc`.

**Navigation :**

| Touche                  | Action                          |
|-------------------------|---------------------------------|
| Fleche droite, Espace, PageDn | Slide suivante           |
| Fleche gauche, BackSpace, PageUp | Slide precedente      |
| Home / End              | Premiere / derniere slide       |
| Esc                     | Quitter le plein ecran          |
| Ctrl+L                  | Toggle plein ecran              |
| Ctrl+- / Ctrl++         | Zoom (utile pour pointer)       |

Pour les **notes orateur** sur un second ecran : ouvre `pitch-notes.pdf` dans une **deuxieme fenetre Acrobat** sur ton ecran prive, plein ecran. Les deux PDFs avancent **manuellement** (tu navigues les deux en parallele). Pas ideal mais ca marche.

### B. pdfpc (presenter console, recommande)

[pdfpc](https://pdfpc.github.io/) est l'outil pro pour presenter les PDFs Beamer. Il **lit nativement** les notes Beamer (le `\note{...}` que j'ai mis sous chaque frame).

**Installation Windows :** WSL, ou via Chocolatey `choco install pdfpc`. Sur Linux : `apt install pdfpc`.

**Lancement :**

```bash
pdfpc pdf/pitch.pdf
```

pdfpc detecte deux ecrans automatiquement :

- **Ecran projecteur** : la slide en grand
- **Ton ecran portable** : slide courante + slide suivante + notes + minuteur + horloge

**Navigation :**

| Touche                  | Action                                |
|-------------------------|---------------------------------------|
| Fleche droite, Espace   | Slide suivante                        |
| Fleche gauche           | Slide precedente                      |
| g                       | Aller a une slide (saisie numero)     |
| b                       | Black out (ecran noir, ressaisir tout)|
| f                       | Frozen (gele l'image projetee)        |
| s                       | Start/stop minuteur                   |
| r                       | Reset minuteur                        |
| q ou Esc                | Quitter                               |

### C. Beamer en mode "show notes on second screen"

Si tu n'as ni pdfpc ni Acrobat, tu peux ouvrir `pitch-notes.pdf` dans n'importe quel lecteur PDF. Chaque page mesure le double en largeur (slide + notes cote a cote). Tu projettes seulement **la moitie gauche** de l'ecran sur le projecteur (en dragguant la fenetre PDF a cheval entre tes deux ecrans).

## Liens cliquables et bookmarks

Le PDF a ete genere avec `hyperref` :

- `pdfpagemode=FullScreen` : ouvre directement plein ecran.
- `pdfstartview=Fit` : adapte au mieux la fenetre.
- `bookmarksopen=true` : Acrobat affiche par defaut le sommaire dans le panneau gauche (utile pour sauter a une slide).

## Sources des logos officiels

Le pitch utilise les logos officiels des standards, de la stack et des fabricants
de dispositifs. Tous proviennent de sources officielles :

| Logo | Source | Licence |
|---|---|---|
| HL7, FHIR, LOINC, IHE, Python, Docker, FastAPI, SQLite, Philips, Masimo, Welch Allyn, Drager | Wikimedia Commons | Domaine public / fair use trademark |
| FHIR (variant) | `hl7.org/fhir/assets/images/fhir-logo-www.png` | HL7 trademark, usage informatif |
| LOINC | `loinc.org/wp-content/uploads/2016/07/loinc-logo-tmp.png` | Regenstrief trademark |
| HAPI FHIR | `hapifhir.io/hapi-fhir/images/logos/small-logo.png` | HAPI project (Apache 2.0) |
| HTMX | Wikimedia Commons | Bigsky Software trademark |

Les fichiers sont stockes dans `src/figures/logos/`. Aucun logo n'est modifie ;
ils sont inclus a leur taille native via la macro `\offlogo{nom.png}` qui les
contraint dans une boite de 18 mm x 5 mm en preservant le ratio.

L'usage de ces logos dans un travail academique illustrant les standards et
technologies cites releve du fair use (illustration, pas d'endossement).

## Avant la presentation : checklist

- [ ] `pdf/pitch.pdf` ouvre bien en plein ecran sur le projecteur de la salle.
- [ ] La couleur passe (le bleu `bridgeblue` n'est pas delave par le video-projecteur).
- [ ] Mes notes (`pitch-notes.pdf` ou pdfpc) sont sur **mon** ecran, pas sur le projecteur.
- [ ] Le **demo Docker** est lance et fonctionne (smoke test passe).
- [ ] Le **chrome** ouvert sur `http://localhost:8080/` (dashboard) et `http://localhost:8081/fhir/Observation?_count=20` (HAPI).
- [ ] Le **terminal** pret avec `bash demo/scripts/e2e_test.sh` au cas ou je veux le relancer pendant la demo.

## Pendant la presentation

- **Slide F13 "Place a la demo"** = je passe Alt+Tab vers le navigateur Docker.
- **Slide F14 "L'histoire que je vous ai racontee"** = retour au PDF pour conclure.
- Garde **5 min** de marge sur la demo : prefere couper la demo plus tot que de manquer la conclusion.
