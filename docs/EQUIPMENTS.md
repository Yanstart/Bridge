# Datasheets equipements - Projet IoT Edge Bridge

> Document de reference pour le simulateur Docker et les exemples du rapport.
> Toutes les sources sont verifiables (URLs cliquables). Date : 2026-05-04.
> Codes LOINC retenus : SpO2 = 59408-5, FC = 8867-4, PA sys = 8480-6, PA dia = 8462-4, glycemie = 2339-0, FEV1 = 20150-9.

---

## A. Moniteurs multiparametriques

### A.1 Philips IntelliVue MX450
- **Source primaire** : [Philips - page produit MX450](https://www.usa.philips.com/healthcare/product/HC866062/intellivue-mx450-patient-monitor) ; [Technical Data Sheet 866062 (PDF)](https://www.biyomar.com/uploads/katalog/monitor-cihazlari/philips-mx-450.pdf) ; [Service manual MX400/450/500/550 (Internet Archive)](https://archive.org/details/manual_Philips_MX400_MX450_MX500_MX550_IntelliVue_Service_Manual).
- **Interfaces physiques** : Ethernet (LAN filaire IntelliVue Clinical Network), Wi-Fi 802.11 via "Bedside Adapter" optionnel, USB, port Smart Hopping (telemetrie US). WLAN et IIT (IntelliVue Instrument Telemetry) sont mutuellement exclusifs.
- **Protocoles applicatifs** : protocole proprietaire **IntelliVue LAN (UDP/IP)** vers le central iX. **HL7 v2 sortant** non genere par le moniteur lui-meme : il faut passer par l'**IntelliVue Information Center iX** qui expose vital signs HL7 outbound, ADT, lab, wave/strip export ([Tech Data Sheet PIIC iX](https://www.biyomar.com/uploads/katalog/monitor-cihazlari/piic-ix.pdf)).
- **Format de sortie typique** : HL7 v2.x ORU^R01 emis par le PIIC iX (segments MSH/PID/PV1/OBR/OBX). Signaux bruts via protocole IntelliVue Data Export proprietaire (souvent reverse-engineered cf. mdpnp/IntelliVue).
- **Pour notre simulateur Docker** : excellent candidat **canal TCP/IP + HL7 v2** ; on simulera des messages ORU^R01 emis "comme si" par le PIIC iX, sur un MLLP listener (port 2575).
- **Codes LOINC pertinents** : SpO2 59408-5, FC 8867-4, PA sys 8480-6, PA dia 8462-4, FR 9279-1, T 8310-5.
- **Notes / limites** : la connectivite HL7 reelle est **payante** (option PIIC iX + interface HL7). Pas de HL7 natif sur le moniteur. UDP IntelliVue non documente publiquement.

### A.2 GE Healthcare CARESCAPE B105
- **Source primaire** : [GE HealthCare - page produit B105/B125 (US)](https://www.gehealthcare.com/products/patient-monitoring/patient-monitors/b105-and-b125-patient-monitors) ; [Brochure B105/B125 (PDF)](https://landing1.gehealthcare.com/rs/005-SHS-767/images/Ge_B1X5_cover_brochure_2018_V11_V2A_Web_compressed.pdf) ; [Brochure VSP 2.0 B105 (PDF)](https://www.biomedicalengineeringcompany.com/public/storage/products/1588154164B105brochure.pdf).
- **Interfaces physiques** : Ethernet (CARESCAPE Network MC ou IX), Wi-Fi optionnel, USB pour service, port serie ancillaires.
- **Protocoles applicatifs** : reseau proprietaire **GE Unity / CARESCAPE Network** ; export **HL7 v2** disponible via option de licence "Network For HL7 Only" (ref produit 2104310-115). Compatible **IHE PCD** via GE CARESCAPE Gateway.
- **Format de sortie typique** : HL7 v2.4/2.6 ORU^R01 (vital signs) emis par la passerelle CARESCAPE (segments MSH/PID/PV1/OBR/OBX, conforme profil IHE PCD-01 Device Observation Reporter).
- **Pour notre simulateur Docker** : alternative interessante au MX450 pour le **canal TCP/IP + HL7 v2**, meme schema. On peut documenter une trame PCD-01 generique dans le rapport.
- **Codes LOINC pertinents** : memes que MX450 (SpO2, FC, PA sys/dia, FR, T).
- **Notes / limites** : licence HL7 separee. Specifications IHE PCD detaillees non publiees librement, fournies par GE sous NDA. Brochure publique reste superficielle sur les protocoles.

---

## B. Glucometre / oxymetre portables (cible : Bluetooth, simule en MQTT)

### B.3 Masimo Radical-7
- **Source primaire** : [Masimo techdocs - Radical-7](https://techdocs.masimo.com/products/device/radical-7/) ; [Operator's Manual LAB-5475 (PDF)](https://techdocs.masimo.com/globalassets/techdocs/pdf/lab-5475j_master.pdf) ; [Catalogue MedicalExpo](https://pdf.medicalexpo.com/pdf/masimo/radical-7/71074-112851.html).
- **Interfaces physiques** : **Wi-Fi 802.11** integre, **Bluetooth** integre, **Ethernet** (sur station d'accueil/dock), **RS-232** serial sur dock, USB service, sortie analogique. Le module radio est embarque.
- **Protocoles applicatifs** : sortie serielle Masimo proprietaire (trames ASCII delimitees), **HL7 v2** via Masimo Patient SafetyNet / Iris gateway, **IHE PCD** supporte par Masimo Iris. Bluetooth utilise principalement pour pairing avec Root / Patient SafetyNet.
- **Format de sortie typique** : trame serielle Masimo ASCII contenant SpO2, PR, PI, PVI ; transformee en ORU^R01 par la passerelle.
- **Pour notre simulateur Docker** : tres bon candidat **canal BLE -> MQTT**. On simule un capteur SpO2 publiant `topic= devices/radical7/<sn>/spo2` toutes les secondes au format JSON `{spo2:97, pr:72, pi:5.4, ts:...}`.
- **Codes LOINC pertinents** : SpO2 59408-5, FC 8867-4, indice de perfusion 61006-3.
- **Notes / limites** : protocole serial proprietaire ; specs Bluetooth non publiees en clair (stack Masimo). On simule donc la **semantique** des donnees, pas la couche radio reelle.

### B.4 Roche Accu-Chek Inform II
- **Source primaire** : [Roche - page produit Accu-Chek Inform II](https://diagnostics.roche.com/us/en/products/instruments/accu-chek-inform-ii-system-ins-809.html) ; [Operator's Manual v8 (PDF)](https://diagnostics.roche.com/content/dam/diagnostics/us/en/products/a/accu-chek-inform-ii/toolkit/AC_Inform_II_Operators_Manual_V8_08424705001_05_EN_USA.pdf) ; [Brochure Cardinal Health (PDF)](https://www.cardinalhealth.com/content/dam/corp/web/documents/literature/accu-chek-inform-II-system-brochure.pdf).
- **Interfaces physiques** : **Wi-Fi (WLAN, certifie Wi-Fi Alliance)** integre au lecteur, **Ethernet** via Base Unit Hub (dock), pas de Bluetooth grand public confirme dans la doc Roche. Liaison vers le dock par contacts dores.
- **Protocoles applicatifs** : **POCT1-A2** (standard ASTM/CLSI POCT1-A2 pour glucometres) sortant vers le middleware ; **HL7 v2** vers SIH via cobas IT 1000 / cobas infinity POC. Pas de protocole IHE PCD direct.
- **Format de sortie typique** : message POCT1-A2 (XML enveloppe) puis ORU^R01 HL7 vers le LIS/SIH (OBX glycemie LOINC 2339-0).
- **Pour notre simulateur Docker** : candidat **canal BLE -> MQTT** simule. Le Inform II "vrai" est Wi-Fi, mais comme les glucometres recents (CoaguChek, GlucoMen) utilisent BLE, on garde le canal BLE en illustrant cette **classe** d'equipements POC.
- **Codes LOINC pertinents** : glycemie 2339-0 (Glucose mass/volume in Blood), 2345-7 (serum), HbA1c 4548-4.
- **Notes / limites** : Bluetooth non explicitement documente dans la version actuelle. Le module SpaceCom-equivalent est le **Base Unit Hub**. Verifier sur la fiche reglementaire UE pour la version exacte deployee.

---

## C. Spirometre / ECG ambulatoire (cible : fichiers XML / SCP)

### C.5 Vyaire MicroLab (spirometre)
- **Source primaire** : [Vyaire - MicroLab Spirometer](https://intl.vyaire.com/products/microlab-spirometer) ; [Operating Manual MicroLab8 Rev 1.6 (PDF)](https://intl.vyaire.com/sites/intl/files/2019-05/085-73WW-Rev-1.6-MicroLab8-Operating-Part1.pdf) ; [Williams Medical - SPCS](https://www.wms.co.uk/Equipment/Diagnostic/Spirometry-,-Respiratory-&-COPD/Vyaire-Spirometry-PC-Software-(SPCS)/p/W33511).
- **Interfaces physiques** : **USB** (port mini-USB sur l'appareil) et **port serie RS-232** vers PC executant le logiciel SPCS.
- **Protocoles applicatifs** : protocole proprietaire Vyaire/CareFusion entre MicroLab et SPCS ; export depuis SPCS en **PDF, CSV, Excel, MS Word**. Pas d'export XML/SCP-spirometry natif documente publiquement (le standard PFT XML existe via SDX/Pulmolink mais pas confirme sur MicroLab).
- **Format de sortie typique** : rapport PDF par patient + base SQLite / Access locale du SPCS. Pour le simulateur, on **emulera un export CSV** representant FEV1, FVC, PEF, FEV1/FVC.
- **Pour notre simulateor Docker** : bon candidat **canal "fichier"** : on depose un CSV (ou un XML maison conforme PFT) dans un volume monte, le bridge le parse et le pousse en HL7 ORU^R01.
- **Codes LOINC pertinents** : FEV1 20150-9, FVC 19868-9, PEF 19935-6, FEV1/FVC 19926-5.
- **Notes / limites** : SCP est un standard **ECG**, pas spirometrie - on a confondu dans l'enonce. La sortie reelle MicroLab est PDF/CSV, pas XML. A documenter clairement dans le rapport.

### C.6 Welch Allyn / Hillrom CP150 (ECG 12 derivations)
- **Source primaire** : [Hillrom - CP150 Directions for Use 80023839 (PDF)](https://www.hillrom.com/content/dam/hillrom-aem/us/en/sap-documents/LIT/80023/80023839LITPDF.pdf) ; [Service manual 80024175 (PDF)](https://www.hillrom.ca/content/dam/hillrom-aem/us/en/sap-documents/LIT/80024/80024175LITPDF.pdf) ; [Spec sheet (McKesson PDF)](https://imgcdn.mckesson.com/CumulusWeb/Click_and_learn/CP150_SpecSheet_US.pdf).
- **Interfaces physiques** : **USB-A** (clef USB pour export), **USB-B** (PC), **Ethernet RJ45** integre, Wi-Fi optionnel via dongle. Imprimante thermique integree.
- **Protocoles applicatifs** : **export SCP-ECG** (ISO/IEEE 11073-91064:2009) ou **MDC** selectionnable ; export **PDF** vers cle USB ; **DICOM Modality Worklist** + **DICOM ECG Waveform** ; integration native avec **CardioPerfect Workstation** (protocole Welch Allyn proprietaire) ; conformance statement HL7 disponible.
- **Format de sortie typique** : fichier SCP-ECG binaire (sections 0..11 par standard EN 1064:2005+A1:2007), PDF rapport 12 derivations, DICOM SOP Class "12-lead ECG Waveform Storage" 1.2.840.10008.5.1.4.1.1.9.1.1.
- **Pour notre simulateur Docker** : **meilleur candidat** pour le **canal "fichier"** dans la demo : on parse un SCP-ECG ou un PDF/XML annexe et on le mappe vers HL7 ORU^R01^R01 (segments OBX avec waveform encoded ou simple summary).
- **Codes LOINC pertinents** : ECG 12-lead study 11524-6, FC 8867-4, intervalle PR 8625-6, QT 8634-8, QRS 8633-0.
- **Notes / limites** : SCP-ECG est binaire, pas XML. Pour un parsing simple en Python on peut utiliser la lib `python-ecg-scp` ou exporter d'abord en PDF/DICOM. La conformance statement detaillee (Welch Allyn part 80022899) est sous NDA.

---

## D. Pompe a perfusion / ventilateur (cible : RS-232)

### D.7 B. Braun Infusomat Space
- **Source primaire** : [B. Braun Infusomat Space (catalogue)](https://catalogs.bbraun.com/en-01/p/PRID00001229/infusomat-space) ; [Instructions for Use US (PDF)](https://www.bbraunusa.com/content/dam/catalog/bbraun/bbraunProductCatalog/S/AEM2015/en-us/b154/infusomat-space-largevolumepumpifu-softwareuitemnumbers8713051u8.pdf) ; [Service Manual SpaceStation/SpaceCom (PDF)](http://www.frankshospitalworkshop.com/equipment/documents/infusion_pumps/service_manuals/B.Braun_Space_Station_-_Service_manual.pdf).
- **Interfaces physiques** : pompe seule = bus **CAN proprietaire** (pas de RS-232 directement sur la pompe) ; via le module **SpaceCom** (battery pack ou SpaceStation), on expose **Ethernet RJ45** + **RS-232** + Wi-Fi. SpaceCom = embedded Linux sur PowerPC.
- **Protocoles applicatifs** : protocole proprietaire B. Braun ; passerelle SpaceCom -> hopital via **HL7 v2** (commande/observation), **DERS** (Drug Error Reduction System) pour bibliotheques de medicaments, support partiel **IHE PCD-03 PIV (Point-of-care Infusion Verification)** dans les hopitaux integres a Onlineuite.
- **Format de sortie typique** : trames serial Space proprietaires (frames CAN encapsulees), exportees en HL7 ORU^R01 / RDS^O13 par OnlineSuiteCompass ou Spaceplus.
- **Pour notre simulateur Docker** : excellent candidat **canal RS-232** (a simuler via `socat -d -d pty,raw,echo=0 pty,raw,echo=0`). On invente une trame texte plausible "VOL=12.5 mL RATE=20 mL/h DRUG=NaCl" et on la transforme en HL7.
- **Codes LOINC pertinents** : volume infuse 8579-7 (mL), debit infusion 76004-9, drogue administree (RxNorm + LOINC 18610-6).
- **Notes / limites** : RS-232 est sur le **SpaceCom**, pas sur la pompe nue. Le protocole exact est sous NDA fabricant. On simule donc une **trame inspiree** (pas une trame Space reelle).

### D.8 Drager Evita Infinity V500 (interface MEDIBUS)
- **Source primaire** : [Drager - Supplement IfU SW 2.n (PDF)](https://www.draeger.com/Content/Documents/Products/IfU_SP_Evita_Infinity_V500_SW_2.n_EN_9054353.pdf) ; [MEDIBUS Protocol for Drager Devices 9028329 (Scribd)](https://www.scribd.com/document/577534892/Medibus-9028329) ; [implementation Java mdpnp](https://github.com/mdpnp/mdpnp/blob/master/devices/draeger/src/main/java/org/mdpnp/devices/draeger/medibus/Medibus.java) ; [implementation Node.js xenon](https://github.com/wokai/xenon).
- **Interfaces physiques** : ports **RS-232** conformes EIA RS-232 (CCITT V.24/V.28) pour MEDIBUS ; egalement USB, DVI, Ethernet (mais MEDIBUS reste serie).
- **Protocoles applicatifs** : **Drager MEDIBUS** (legacy) ou **MEDIBUS.X** (nouveau, basee XML/ASCII profile-based). Doc officielle "Drager RS-232 MEDIBUS Protocol Definition" reference 9028258 ; "MEDIBUS.X Profile Definition: Technical Specification".
- **Format de sortie typique** : MEDIBUS legacy = caracteres ASCII, trames delimitees par STX/ETX, checksum 2 octets, ICC (cmd) + arguments. Settings serial : **19200 8E1** (legacy) ou **9600 8E1** (MEDIBUS.X). Trame typique : `<ESC>R<arg>...<CR>` pour requete realtime data, reponse avec champs FiO2, PEEP, Vt, Pmax, RR, MV.
- **Pour notre simulateur Docker** : **meilleur candidat** pour le **canal RS-232** dans la demo, car le protocole est **bien documente publiquement** (specs PDF + implementations open source mdpnp/xenon). On peut implementer un parser realiste.
- **Codes LOINC pertinents** : FiO2 19994-3, PEEP 20077-4, volume tidal 76530-3, FR 9279-1, pression crete 76270-8.
- **Notes / limites** : MEDIBUS != HL7 ; il faut une couche de mapping. Cest justement ce que fait notre Bridge. La spec officielle Drager 9028258 n'est pas en libre acces sur draeger.com, mais des copies circulent (cf. lien Scribd) et l'implementation reference open-source mdpnp est suffisante pour la demo.

---

## Synthese - recommandation pour la demo

Pour couvrir les 4 canaux d'entree du Bridge avec **un equipement par canal**, en privilegiant ceux dont la documentation publique est la plus solide :

| Canal d'entree           | Equipement retenu                | Pourquoi celui-la                                                                      | Format mappe -> HL7 v2  |
|--------------------------|----------------------------------|----------------------------------------------------------------------------------------|-------------------------|
| **TCP/IP + HL7 v2**      | **Philips IntelliVue MX450**     | Cas d'usage le plus repandu en hopital ; HL7 sortant via PIIC iX bien documente.       | ORU^R01 (vital signs)   |
| **BLE -> MQTT (simule)** | **Masimo Radical-7**             | Wi-Fi/BT integre, semantique SpO2 simple, LOINC 59408-5 evident, demo visuelle claire. | ORU^R01 (SpO2/FC)       |
| **Fichier (XML/SCP)**    | **Welch Allyn CP150**            | Export SCP-ECG normalise (ISO 11073-91064) + DICOM ECG, parsing realiste.              | ORU^R01 (ECG study)     |
| **RS-232**               | **Drager Evita Infinity V500**   | Protocole MEDIBUS publiquement documente + implementations open source de reference.   | ORU^R01 (resp settings) |

Les 4 autres equipements (B105, Accu-Chek, MicroLab, Infusomat) sont conserves dans le rapport comme **alternatives** et pour montrer la diversite du parc, mais ne seront pas implementes dans le simulateur Docker en priorite.
