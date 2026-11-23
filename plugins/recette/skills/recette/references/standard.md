# Le standard recette

> **Une recette sert à décider d'une mise en production sur des preuves, pas sur une impression.** Ce qu'il faudra vérifier est noté **au fil du développement**. Ce qui fera dire « go » est fixé **avant** d'exécuter. Les cas peuvent être rejoués par n'importe qui, chaque résultat a sa preuve, la décision s'appuie sur les chiffres, et les réserves sont écrites, datées et signées.

Ce standard s'appuie sur le syllabus ISTQB **Foundation Level v4.0** (2023, noté *CTFL*), le syllabus ISTQB / CFTL **Tests d'acceptation** (2019, noté *AcT*) et la norme **ISO/IEC/IEEE 29119-3**. Les références de section sont données entre crochets.

## Sommaire
1. Vocabulaire
2. Les étapes, du développement au PV
3. Arborescence et formats
4. Alimenter la recette au fil du développement (`a-tester.md`)
5. La stratégie : types de recette, risques, critères
6. Exigences et critères d'acceptation
7. Concevoir les cas : techniques
8. Écrire un bon cas de test
9. Exécution, preuves, confirmation et régression
10. Anomalies : sévérité, priorité, contenu
11. Go / no-go
12. PV et rapport de fin de recette
13. Règles vérifiées par le script
14. Sources

---

## 1. Vocabulaire

| Terme | Sens |
|---|---|
| **MOA** / métier | ceux qui expriment le besoin et **prononcent** la recette (signent le PV). Idéalement, ce sont les utilisateurs visés qui recettent [CTFL 2.2.1] |
| **MOE** / équipe projet | ceux qui réalisent et préparent la recette, avec le métier [AcT 1.2] |
| **Recette** (test d'acceptation) | valider que le système répond aux besoins métier et démontrer qu'il est prêt à être déployé [CTFL 2.2.1] |
| **Critère d'acceptation** | une condition mesurable, vraie ou fausse, attachée à une exigence ou une user story. Elle dit **quoi** tester, pas comment [AcT 1.1.2] |
| **Test de confirmation** | rejouer les cas qui ont échoué à cause d'une anomalie, une fois celle-ci corrigée [CTFL 2.2.3] |
| **Test de régression** | vérifier qu'un changement n'a rien cassé ailleurs. Le périmètre se décide après une analyse d'impact, et ces tests sont de bons candidats à l'automatisation [CTFL 2.2.3] |
| **VABF** / **VSR** | dans les marchés publics : vérification d'aptitude au bon fonctionnement (avant mise en service), puis vérification de service régulier (en conditions réelles, souvent sur un site pilote) |
| **Réserve** | une anomalie acceptée temporairement, listée dans le PV avec une échéance de correction |
| **PV de recette** | le procès-verbal qui prononce la recette : avec ou sans réserves, partielle, ou refusée |

## 2. Les étapes, du développement au PV

```
Développement ──▶ a-tester.md ──▶ Stratégie (risques, critères) ──▶ Exigences + critères d'acceptation ──▶ Cas
   (chaque changement note ce qu'il faudra vérifier)                                                         │
PV signé ◀── Go/no-go ◀── Anomalies ◀── Campagne (exécution + preuves) ◀──────────────────────────────────────┘
                              │ correction ──▶ test de confirmation + régression
```
- **Tester tôt** : les critères d'acceptation et les cas se conçoivent pendant l'analyse des exigences, pas après le développement [AcT 1.2.3 ; CTFL 2.1.5].
- Les **critères de sortie** sont fixés **avant** l'exécution. Les fixer après, c'est ajuster la règle au résultat [CTFL 5.1.3].
- Une anomalie corrigée est **re-testée** (test de confirmation) avant d'être fermée. Les cas critiques sont rejoués (régression) [CTFL 2.2.3].
- Chaque version livrée en recette donne lieu à **une campagne**, identifiée par sa version (gestion de configuration) [CTFL 5.4].

## 3. Arborescence et formats

La recette vit **dans le repo**, en Markdown, versionnée et relue en MR comme le code. Les livrables de test sont des éléments de configuration [CTFL 5.4].

```
recette/
├── a-tester.md                  alimenté au fil du dev : changement → ce qu'il faudra vérifier → cas
├── strategie.md                 périmètre, types de recette, risques, environnement, données, rôles, critères
├── exigences.md                 ID | Exigence | Critères d'acceptation | Priorité | Source
├── cas/
│   ├── _template.md
│   └── CT-001-connexion-valide.md
├── anomalies.md                 ID | Titre | Sévérité | Priorité | Cas | Statut | Échéance | Ticket
├── .recette.json                (facultatif) périmètre « code » du hook
└── campagnes/
    └── 2026-11-24-v1.4.0/
        ├── campagne.md          version, environnement, tableau d'exécution
        ├── preuves/             captures, logs, exports
        └── pv.md                généré par le script, complété et signé par des humains
```
Les en-têtes `---` en haut des fichiers sont des métadonnées simples `clé: valeur` (listes séparées par des virgules). Le script les lit ; ne pas y mettre de YAML imbriqué.

## 4. Alimenter la recette au fil du développement (`a-tester.md`)

Reconstituer de mémoire, la veille de la recette, ce qui a changé depuis trois mois garantit des oublis. Chaque changement de comportement note **au moment où il est fait** ce qu'il faudra vérifier :

```markdown
| Date | Changement | Réf. | Exigence | À vérifier en recette | Risque | Cas |
|---|---|---|---|---|---|---|
| 2026-11-12 | Verrou sur le créneau à la création | !138 | EX-002 | Deux réservations simultanées : une seule réussit | haut | |
```
- **Changement** : du point de vue de l'utilisateur, pas du code.
- **À vérifier** : ce qu'il faudra observer, cas d'erreur compris. C'est la matière des futurs cas.
- **Risque** : haut, moyen ou bas (probabilité × impact pour l'utilisateur) [CTFL 5.2.1]. Il oriente la priorité.
- **Cas** : vide au départ. Rempli (`CT-004`) quand l'entrée devient un cas, ou « hors recette : raison » si elle ne demande pas de vérification en recette.
- Une entrée sans cas au moment du PV apparaît dans le PV, rubrique « Changements sans cas de test » : c'est un risque résiduel.

**Le hook du plugin** (`hooks/recette_gate.py`) applique cette règle aux agents. Un commit qui change du code applicatif dans un repo doté de `recette/` doit modifier `a-tester.md` (ou un cas). Sinon, son message doit porter `Recette: sans impact (raison)`, ce qui laisse une trace dans l'historique. Tests, doc, fichiers de lock et CI n'entrent pas en compte, et le périmètre se règle dans `recette/.recette.json`.

## 5. La stratégie (`strategie.md`)

| Section | Contenu |
|---|---|
| **Périmètre** | fonctionnalités et version recettées |
| **Hors périmètre** | ce qui n'est **pas** testé, et pourquoi. Le PV n'engage pas sur ces points |
| **Types de recette** (recommandé) | parmi les formes d'acceptation [CTFL 2.2.1] : **utilisateur (UAT)** ; **exploitation (OAT)** : sauvegarde et restauration, reprise après sinistre, installation et retour arrière, supervision, gestion des utilisateurs ; **contractuelle ou réglementaire** (RGPD, accessibilité, clauses du contrat) ; **alpha / bêta**. Et les caractéristiques **non fonctionnelles** concernées, selon l'ISO 25010 : performance, compatibilité, utilisabilité, fiabilité, sécurité, maintenabilité, portabilité [CTFL 2.2.2 ; AcT 4] |
| **Risques produit** | les risques identifiés, avec leur probabilité et leur impact. Ils déterminent l'étendue, les techniques, la priorité et l'effort de test [CTFL 5.2.3]. Pour chacun, le ou les cas qui le couvrent |
| **Environnement** | où l'on teste. **Aussi proche de la prod que possible** : même configuration, mêmes intégrations ou des bouchons documentés [CTFL 2.2.1, intégration système] |
| **Données de test** | jeux fictifs ou anonymisés. Jamais de données personnelles réelles |
| **Rôles** | qui prépare, qui exécute, qui arbitre les anomalies (testeur et analyste métier ensemble [AcT 5.2.1]), **qui signe** |
| **Critères d'entrée** | ressources disponibles (personnes, outils, environnement, données), livrables de test prêts, qualité initiale (tests de fumée passés) [CTFL 5.1.3] |
| **Critères de sortie** | en clair, **et** dans l'en-tête pour le script : couverture, anomalies non résolues, cas exécutés et réussis [CTFL 5.1.3] |

En-tête (valeurs par défaut si absentes) :
```
go_bloquantes_max: 0              # anomalies bloquantes ouvertes tolérées
go_majeures_max: 0                # anomalies majeures ouvertes tolérées (en réserve)
go_taux_reussite_min: 95          # % de cas OK parmi les cas exécutés
go_priorite_haute_executee: 100   # % des cas de priorité haute exécutés
go_couverture_exigences_min: 100  # % des exigences couvertes par au moins un cas exécuté
```
Arrêter faute de temps ou de budget peut être acceptable, **si les parties prenantes ont revu et accepté le risque** de déployer sans tests supplémentaires [CTFL 5.1.3]. On l'écrit alors dans la stratégie ou le PV, avec la date et l'auteur de la décision.

## 6. Exigences et critères d'acceptation (`exigences.md`)

```markdown
| ID | Exigence | Critères d'acceptation | Priorité | Source |
|---|---|---|---|---|
| EX-003 | Annuler un rendez-vous confirmé libère le créneau et prévient le patient | Statut « Annulé » ; créneau de nouveau libre ; SMS contenant « annulé », la date et l'heure, envoyé dans la minute | haute | US-21 |
```
- **Les critères d'acceptation** sont **précis, mesurables, concis**. Chacun permet de dire si l'objet testé y satisfait ou non. Ils ne contiennent **pas de détail technique de la solution**, et ils couvrent aussi le **non fonctionnel** [AcT 2.1]. Ils s'écrivent **ensemble**, métier et testeurs, le plus tôt possible [AcT 1.1.2, 2.1].
- Des exigences vagues produisent des tests faux : les ambiguïtés se lèvent **avant** d'écrire les cas [AcT 1.1.3]. Pour les user stories, appliquer INVEST ; pour les exigences, l'ISO/IEC/IEEE 29148 [AcT 1.1.3].
- **Traçabilité** : exigence ↔ critère ↔ cas ↔ résultat ↔ anomalie. Une traçabilité bidirectionnelle permet l'analyse de couverture [AcT 5.2.3 ; CTFL 1.4.4]. **Chaque exigence est couverte par au moins un cas**, sinon elle passe explicitement hors périmètre.

## 7. Concevoir les cas : techniques

Les cas se **dérivent des critères d'acceptation** [AcT 1.1.2, 2.2.1] avec :

| Technique | Pour | Réf. |
|---|---|---|
| **Partitions d'équivalence** | une valeur par classe de comportement (valide, invalide, chaque catégorie) | CTFL 4.2.1 |
| **Valeurs limites** | les bornes et leurs voisins immédiats (0, 1, max, max+1) | CTFL 4.2.2 |
| **Tables de décision** | les combinaisons de règles métier (tarifs, droits, conditions) | CTFL 4.2.3 ; AcT 3.2 |
| **Transitions d'états** | les cycles de vie (rendez-vous : à confirmer → confirmé → annulé ; transitions interdites) | CTFL 4.2.4 |
| **Processus métier** | les parcours de bout en bout, chemins principaux et alternatifs | AcT 2.2.1, 3 |
| **Basés sur les risques** | l'ordre et la profondeur des tests suivent le niveau de risque | AcT 2.2.1 ; CTFL 5.1.5 |
| **Tests exploratoires** | des sessions **limitées dans le temps**, guidées par une **charte** (but, cible, portée, durée, profil d'utilisateur simulé), idéalement en binôme. Elles **complètent** les cas scriptés, elles ne les remplacent pas | AcT 2.3.1 ; CTFL 4.4.2 |
| **Supposition d'erreurs, check-lists** | l'expérience : double clic, retour arrière, session expirée, champ collé avec des espaces | CTFL 4.4.1, 4.4.3 |
| **Gherkin** (Étant donné / Quand / Alors) | un format lisible par tous et automatisable. Il correspond à Préconditions / Action / Résultat attendu | AcT 2.2.2 |

**Prioriser** l'exécution : par risque, puis par priorité des exigences. Un cas dont dépend un cas plus prioritaire passe avant lui [CTFL 5.1.5].

## 8. Écrire un bon cas de test (`cas/CT-NNN-titre.md`)

```markdown
---
id: CT-004
titre: Annuler un rendez-vous confirmé envoie un SMS au patient
exigences: EX-003
priorite: haute
type: fonctionnel
---
## Objectif
## Préconditions
## Données
## Étapes
| # | Action | Résultat attendu |
|---|---|---|
| 1 | Cliquer sur « Annuler » de la ligne 10:30, puis confirmer | Le statut passe à « Annulé » ; message « Rendez-vous annulé, SMS envoyé » |
```
- **Exécutable par quelqu'un d'autre** : préconditions et données explicites ; pas de « se connecter » sans dire avec quel compte.
- **Un résultat attendu par étape, observable** : une valeur, un libellé exact, un état, une entrée de journal. « Ça fonctionne », « l'écran s'affiche correctement » ou « OK » ne sont pas des résultats attendus.
- **Un cas = un objectif.** Couvrir les **cas négatifs** autant que les positifs.
- **Les cas couvrent les critères d'acceptation, les processus, les règles et les risques métier** [AcT 5.2.3].
- **Le type** : `fonctionnel`, `non-regression`, `securite`, `performance`, `utilisabilite`, `compatibilite`, `fiabilite`, `exploitation`, `reglementaire`, `exploratoire`, `technique`.
- **Une session exploratoire** (`type: exploratoire`) remplace Préconditions / Données / Étapes par une **Charte** (but, cible, profil, pistes, **durée**). Les **Constats** sont remplis pendant la session.

## 9. Exécution, preuves, confirmation et régression (`campagnes/…/campagne.md`)

```markdown
---
version: 1.4.0
environnement: recette — https://recette.rdv.example.fr (build 1.4.0-rc2)
debut: 2026-11-24
fin: 2026-11-25
---
## Exécution
| Cas | Statut | Testeur | Date | Anomalie | Preuve |
|---|---|---|---|---|---|
| CT-004 | KO | Camille R. | 2026-11-24 | AN-001 | [capture](preuves/CT-004.png) |
```
- **Statuts** : `OK`, `KO`, `bloqué` (impossible à exécuter : autre anomalie, environnement), `non exécuté`.
- **Un KO référence toujours une anomalie** : il faut un rapport d'anomalie pour chaque défaut [CTFL 5.5].
- **Une preuve par cas exécuté** : capture, log, export, enregistrement. Elle montre le **résultat obtenu**.
- La **version testée** et l'**environnement** sont identifiés sans ambiguïté [CTFL 5.4].
- On n'**ajuste pas** un résultat attendu pendant l'exécution pour le faire coller à ce qu'on observe.
- **Après une correction** : le test de confirmation rejoue le cas en entier. Puis on rejoue les cas de régression choisis par analyse d'impact [CTFL 2.2.3].
- **Le suivi de la campagne** : un point d'avancement régulier (période, avancement, obstacles et contournements, métriques, risques nouveaux, prochaine étape) [CTFL 5.3.2], écrit **sans jargon technique** pour le métier [AcT 5.2.2].

## 10. Anomalies (`anomalies.md`)

Le registre :
```markdown
| ID | Titre | Sévérité | Priorité | Cas | Statut | Échéance | Ticket |
|---|---|---|---|---|---|---|---|
| AN-001 | Aucun SMS envoyé à l'annulation ; contournement : appel du patient | majeure | haute | CT-004 | en correction | 2026-12-04 | #482 |
```
- **Sévérité** = le degré d'impact sur les parties prenantes ou les exigences. **Priorité** = l'urgence de la correction. **Ce sont deux champs distincts** [CTFL 5.5] : une faute de frappe sur la page d'accueil est de sévérité mineure, mais de priorité haute.

| Sévérité | Définition | Effet sur le go |
|---|---|---|
| **bloquante** | une fonction essentielle est inutilisable sans contournement ; perte ou corruption de données ; faille de sécurité | no-go tant qu'elle est ouverte |
| **majeure** | une fonction importante est dégradée, avec un contournement | go possible **en réserve** si la stratégie le permet |
| **mineure** | une gêne sans impact métier | go possible, en réserve |

- L'**impact métier** s'analyse **à deux**, testeur et analyste métier : quels chemins de processus sont touchés, quelles règles métier sont mal appliquées [AcT 5.2.1].
- **Statuts** : `ouverte`, `différée`, `en correction`, `corrigée` (en attente du test de confirmation), `réouverte`, `fermée` (confirmée), `rejetée`, `doublon` [CTFL 5.5]. Une anomalie compte comme ouverte tant qu'elle n'est ni fermée, ni rejetée, ni doublon.
- **Le rapport d'anomalie complet**, dans le ticket ou dans un fichier lié [CTFL 5.5] :
  - un identifiant, un titre qui résume ;
  - la date, l'auteur et son rôle ;
  - l'objet testé (version) et l'environnement ;
  - le contexte (cas, données, technique) ;
  - les étapes pour reproduire, avec logs, captures ou enregistrements ;
  - l'attendu et l'obtenu ;
  - la sévérité, la priorité, le statut, les références.

## 11. Go / no-go

Le script calcule la proposition à partir des critères de la stratégie :

| Proposition | Quand |
|---|---|
| **NO-GO** | un critère de sortie n'est pas respecté : bloquantes, majeures, taux de réussite, cas de priorité haute non exécutés, couverture des exigences |
| **GO AVEC RÉSERVES** | les critères sont respectés, mais des majeures ou mineures restent ouvertes : elles deviennent des réserves, avec échéance |
| **GO** | les critères sont respectés et aucune anomalie n'est ouverte |

Les décideurs choisissent ensuite parmi les issues prévues par [AcT 5.2.2] :
- **mise en service telle quelle** ;
- **sous réserve** : les défauts connus qui ont un contournement sont **communiqués aux utilisateurs et au support** ;
- **partielle** : une fonctionnalité qui présente un risque important est **exclue du déploiement**, ou désactivée ;
- **rejet** : jusqu'à correction et re-test des défauts critiques. Le déploiement est reporté ou remplacé par une alternative.

Le script **propose**, les humains **décident** et signent. Une décision différente de la proposition se justifie par écrit.

Les prérequis d'exploitation font partie du go : rollback écrit et testé, sauvegarde juste avant la MEP, checklist de mise en production revue (plugin ops-doc), communication.

## 12. PV et rapport de fin de recette

`check_recette.py --pv` génère, dans le dossier de la campagne, un document qui combine le **rapport de fin de test** [CTFL 5.3.2 ; AcT 5.2.2] et le **PV** :
- l'identification : application, version, environnement, période ;
- le **bilan** et les **métriques** : cas prévus, OK, KO, bloqués, non exécutés, taux de réussite, couverture des exigences ;
- l'**évaluation au regard des critères de sortie** ;
- les **anomalies non corrigées** et les **réserves** avec leurs échéances ;
- les **changements sans cas de test** (issus d'`a-tester.md`) ;
- les **écarts par rapport au plan**, les **obstacles et contournements**, les **risques résiduels**, les **enseignements** : à compléter par l'équipe ;
- la décision proposée, la décision prise (GO, GO avec réserves, GO partiel, NO-GO), sa justification ;
- les prérequis de MEP et les signatures.

Le rapport doit être **clair, cohérent, complet**, et contenir tout ce qui étaye la décision [AcT 5.2.3].

**Piège** : un PV « sans réserve » signé alors que des anomalies restent ouvertes vaut acceptation définitive, et fait perdre tout recours sur ces anomalies. Le script le signale (`PV-INCOHERENT`).

## 13. Règles vérifiées par le script

`scripts/check_recette.py` (bibliothèque standard). **ERREUR** = non conforme, **AVERTISSEMENT** = à corriger, **INFO**.

| Code | Niveau | Règle |
|---|---|---|
| `STRUCT` | erreur | `strategie.md`, `exigences.md` ou `cas/` absent |
| `STRAT-SECTION` | erreur | section obligatoire absente de la stratégie |
| `STRAT-RISQUES` | avertissement | pas de section « Risques produit » |
| `STRAT-CRITERES` | avertissement | critère `go_*` absent de l'en-tête (valeur par défaut utilisée) |
| `EXIG-DOUBLON` / `EXIG-PRIORITE` | erreur | identifiant d'exigence en double / priorité invalide |
| `CAS-CHAMP` | erreur | champ d'en-tête manquant ou invalide (`id`, `titre`, `exigences`, `priorite`, `type`) |
| `CAS-ID-FICHIER` | avertissement | l'`id` ne correspond pas au nom du fichier |
| `CAS-EXIGENCE-INCONNUE` | erreur | le cas couvre une exigence inexistante |
| `CAS-SECTION` | erreur | section `Préconditions`, `Données`, `Étapes` (ou `Charte` pour une session exploratoire) absente |
| `CAS-CHARTE` | avertissement | charte exploratoire sans but ou sans durée |
| `CAS-ETAPES` | erreur | aucune étape dans le tableau |
| `CAS-ATTENDU-VIDE` | erreur | une étape sans résultat attendu |
| `CAS-ATTENDU-VAGUE` | avertissement | résultat attendu non vérifiable |
| `CAS-DONNEES-VIDES` | avertissement | section Données vide |
| `EXIGENCE-NON-COUVERTE` | erreur | une exigence n'a aucun cas |
| `ANO-SEVERITE` / `ANO-STATUT` | erreur | sévérité ou statut invalide |
| `ANO-PRIORITE` | avertissement / erreur | pas de colonne Priorité / valeur invalide |
| `ANO-CAS-INCONNU` | avertissement | anomalie rattachée à un cas inexistant |
| `ANO-SANS-ECHEANCE` | avertissement | anomalie ouverte sans échéance |
| `A-TESTER-NON-TRAITE` | avertissement | entrée d'`a-tester.md` sans cas ni mention « hors recette » |
| `A-TESTER-CAS-INCONNU` | erreur | entrée qui renvoie à un cas inexistant |
| `A-TESTER-RISQUE` | avertissement | risque invalide (haut, moyen, bas) |
| `CAMP-CHAMP` | erreur | `version` ou `environnement` absent de la campagne |
| `CAMP-CAS-INCONNU` | erreur | ligne d'exécution pour un cas inexistant |
| `CAMP-STATUT` | erreur | statut d'exécution invalide |
| `CAMP-KO-SANS-ANOMALIE` | erreur | KO sans anomalie référencée |
| `CAMP-ANOMALIE-INCONNUE` | erreur | anomalie référencée absente d'`anomalies.md` |
| `CAMP-PREUVE-MANQUANTE` | avertissement | cas OK ou KO sans preuve |
| `CAMP-PREUVE-INTROUVABLE` | erreur | lien de preuve vers un fichier absent |
| `CAMP-CAS-ABSENT` | info | cas existant absent de la campagne |
| `PV-INCOHERENT` | erreur | PV « GO sans réserve » coché avec des anomalies ouvertes |

## 14. Sources

- ISTQB, *Certified Tester Foundation Level Syllabus v4.0* (2023) : §1.4.4 traçabilité ; §2.2.1 niveaux de test et formes d'acceptation ; §2.2.2 types de test, ISO 25010 ; §2.2.3 confirmation et régression ; ch. 4 techniques ; §5.1.3 critères d'entrée et de sortie ; §5.1.5 priorisation ; §5.2 risques ; §5.3.2 rapports de test ; §5.4 gestion de configuration ; §5.5 gestion des défauts. https://www.istqb.org/certifications/certified-tester-foundation-level
- ISTQB / CFTL, *Syllabus de niveau fondation : Tests d'acceptation*, version 2019 FR : §1.1.2 critères et tests d'acceptation ; §1.2 analyse métier ; §1.2.3 ATDD et BDD ; §2.1 rédaction des critères ; §2.2 conception, Gherkin ; §2.3 exploratoire et bêta ; ch. 4 non fonctionnel ; §5.2 analyse des défauts, rapports, assurance qualité. https://www.cftl.fr
- ISO/IEC/IEEE 29119-3:2021, *Software testing — Test documentation* (modèles : plan, cas, rapport d'incident, rapport de fin de test). https://www.iso.org/standard/79429.html
- OpenClassrooms, *Préparez votre cahier de recette* : https://openclassrooms.com/fr/courses/7365126-concevez-une-strategie-de-test/8214294-preparez-votre-cahier-de-recette
- marche-public.fr, *Vérifications : mises en garde* (VABF, VSR, PV pré-remplis) : https://www.marche-public.fr/Verifications/Marches-publics-Verifications-Mises-en-garde.htm
