# Figures du projet IoT Edge Bridge

Repertoire des illustrations a produire pour les trois livrables (rapport, pitch, CDC).
Toute figure est livree au format vectoriel (PDF ou SVG) et incluse via `\includegraphics`.

## Figure 1 - Architecture chaos vers ordre

Schema narratif en trois zones (gauche : chaos des dispositifs heterogenes ; centre : passerelle multi-couches ; droite : ordre BIHR/DPI/FHIR). TikZ inline preferable.

## Figure 2 - Pipeline 4 couches Adapter/Parser/Mapper/Transport

Diagramme en blocs verticaux representant les quatre couches internes de la passerelle, avec types de donnees echanges entre couches. TikZ inline.

## Figure 3 - Topologie Docker Compose de la demo

Vue logique des conteneurs (4 simulateurs, bridge, dashboard, broker MQTT, listener MLLP). Mermaid exporte en PDF acceptable.

## Figure 4 - Diagramme de sequence trame Philips

Sequence MLLP : moniteur Philips IntelliVue, listener TCP, parser HL7 v2, mapper FHIR, publication BIHR. Mermaid sequence ou TikZ.

## Figure 5 - Capture dashboard supervision

Maquette PNG haute resolution (300 DPI minimum) de l'interface de supervision OT.
