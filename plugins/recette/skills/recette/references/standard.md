# Le standard recette

> **Une recette sert à décider d'une mise en production sur des preuves, pas sur une impression.** On fixe avant de commencer ce qui est testé et ce qui fera dire « go » ; on exécute des cas que n'importe qui peut rejouer ; on garde la preuve de chaque résultat ; on décide avec les chiffres, et les réserves sont écrites, datées et signées.

## Sommaire
1. Le vocabulaire
2. Les étapes d'une recette
3. Arborescence et formats
4. La stratégie
5. Les exigences et la traçabilité
6. Écrire un bon cas de test
7. L'exécution et les preuves
8. Les anomalies
9. Le go / no-go
10. Le PV de recette
11. Règles vérifiées par le script
12. Sources

---

## 1. Le vocabulaire

| Terme | Sens |
|---|---|
| **MOA** / métier | ceux qui expriment le besoin et **prononcent** la recette (signent le PV) |
| **MOE** / équipe projet | ceux qui réalisent et préparent la recette |
| **Recette fonctionnelle** (ou d'acceptation, UAT) | le métier vérifie que l'application répond au besoin exprimé |
| **Recette technique** | exploitation, performance, sécurité, sauvegarde/restauration, supervision |
| **Non-régression** | rejouer les cas critiques déjà validés pour vérifier qu'ils marchent toujours |
| **VABF** / **VSR** | dans les marchés publics : vérification d'aptitude au bon fonctionnement (recette avant mise en service), puis vérification de service régulier (en conditions réelles, souvent sur un site pilote) |
| **Réserve** | une anomalie acceptée temporairement, listée dans le PV avec une échéance de correction |
| **PV de recette** | le procès-verbal qui prononce la recette : avec ou sans réserves, ou refus |

## 2. Les étapes d'une recette

```
Stratégie ─▶ Exigences ─▶ Cas de test ─▶ Campagne (exécution + preuves) ─▶ Anomalies ─▶ Go/no-go ─▶ PV signé ─▶ MEP
   ▲ critères fixés AVANT                                                     │ corrections + re-test
   └──────────────────────────────────────────────────────────────────────────┘
```
- Les **critères de sortie** sont fixés **avant** l'exécution. Les fixer après, c'est ajuster la règle au résultat.
- Une anomalie corrigée est **re-testée** (le cas est rejoué) avant d'être fermée. Une correction non vérifiée reste ouverte.
- Chaque nouvelle version livrée en recette = une **nouvelle campagne** ; les cas critiques des versions précédentes y sont rejoués (non-régression).

## 3. Arborescence et formats

La recette vit **dans le repo**, en Markdown, versionnée et relue en MR comme le code.

```
recette/
├── strategie.md                 périmètre, environnement, données, rôles, critères (en-tête YAML)
├── exigences.md                 tableau : ID | Exigence | Priorité | Source
├── cas/
│   ├── _template.md
│   └── CT-001-connexion-valide.md
├── anomalies.md                 tableau : ID | Titre | Sévérité | Cas | Statut | Échéance | Ticket
└── campagnes/
    └── 2026-11-24-v1.4.0/
        ├── campagne.md          version, environnement, tableau d'exécution
        ├── preuves/             captures, logs, exports
        └── pv.md                généré par le script, complété et signé par des humains
```

Les en-têtes `---` en haut des fichiers sont des métadonnées simples `clé: valeur` (listes séparées par des virgules). Le script les lit ; ne pas y mettre de YAML imbriqué.

## 4. La stratégie (`strategie.md`)

Sections obligatoires :

| Section | Ce qu'elle dit |
|---|---|
| **Périmètre** | les fonctionnalités et versions recettées |
| **Hors périmètre** | ce qui n'est **pas** testé, et pourquoi. C'est ce que le PV n'engage pas |
| **Environnement** | où l'on teste : URL, version, **aussi proche de la prod que possible** (même configuration, même type de base, mêmes intégrations ou des bouchons documentés) |
| **Données de test** | quels jeux de données, comment on les obtient. **Jamais de données personnelles réelles** : données fictives ou anonymisées |
| **Rôles** | qui prépare, qui exécute, qui arbitre les anomalies, **qui signe** |
| **Critères d'entrée** | ce qui doit être vrai pour commencer (version livrée et déployée, tests automatisés verts, données en place, notes de version) |
| **Critères de sortie** | ce qui fait dire go / no-go, en clair, **et** dans l'en-tête (pour le script) |

Critères dans l'en-tête (valeurs par défaut si absents) :
```
go_bloquantes_max: 0          # anomalies bloquantes ouvertes tolérées
go_majeures_max: 0            # anomalies majeures ouvertes tolérées (en réserve)
go_taux_reussite_min: 95      # % de cas OK parmi les cas exécutés
go_priorite_haute_executee: 100   # % des cas de priorité haute exécutés
```

## 5. Les exigences et la traçabilité (`exigences.md`)

```markdown
| ID | Exigence | Priorité | Source |
|---|---|---|---|
| EX-001 | Un praticien se connecte avec son e-mail et son mot de passe | haute | US-12 |
```
- Une exigence = un besoin vérifiable, formulé du point de vue de l'utilisateur.
- **Chaque exigence est couverte par au moins un cas.** Une exigence non couverte n'est pas recettée : soit on écrit le cas, soit on la déclare hors périmètre.
- La colonne Source renvoie au ticket, à la user story ou au paragraphe de spécification d'où elle vient.

## 6. Écrire un bon cas de test (`cas/CT-NNN-titre.md`)

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
| 1 | Ouvrir l'agenda du 24/11/2026 | La ligne 10:30 « Première visite » est affichée, statut « Confirmé » |
| 2 | Cliquer sur « Annuler » de la ligne 10:30, puis confirmer | Le statut passe à « Annulé » ; un message « Rendez-vous annulé, SMS envoyé » s'affiche |
| 3 | Consulter le journal d'envoi SMS (bouchon) | Un SMS vers 06 55 44 33 22 contenant « annulé » et « 24/11 10:30 » est présent |
```
Les règles :
- **Exécutable par quelqu'un d'autre** : préconditions et données explicites ; pas de « se connecter » sans dire avec quel compte.
- **Un résultat attendu par étape, observable et vérifiable** : une valeur, un libellé exact, un état, un message. « Ça fonctionne », « l'écran s'affiche correctement », « OK » ne sont pas des résultats attendus : deux testeurs ne conclueraient pas la même chose.
- **Un cas = un objectif.** Un cas qui vérifie cinq choses donne un KO dont on ne sait pas d'où il vient.
- **Les cas négatifs comptent autant que les positifs** : mot de passe faux, champ vide, droits insuffisants, double clic, valeur limite.
- **Priorité** : haute (bloquant pour le métier si ça casse), moyenne, basse. Les cas de priorité haute forment le socle de non-régression.
- **Type** : fonctionnel, non-regression, securite, performance, technique.

## 7. L'exécution et les preuves (`campagnes/<date>-v<version>/campagne.md`)

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
- **Statuts** : `OK`, `KO`, `bloqué` (impossible à exécuter à cause d'une autre anomalie ou de l'environnement), `non exécuté`.
- **Un KO référence toujours une anomalie.** Un KO sans anomalie est un problème perdu.
- **Une preuve par cas exécuté** : capture annotée (plugin doc-screenshots), log, export, réponse d'API. La preuve montre le **résultat obtenu**, pas l'action.
- On teste la **version notée** dans l'en-tête, sur l'environnement noté. Une correction livrée pendant la campagne change la version : on le note.
- On n'**ajuste pas** un résultat attendu pendant l'exécution pour qu'il colle à ce qu'on observe. Si l'attendu était faux, on corrige le cas (MR) et on le rejoue.

## 8. Les anomalies (`anomalies.md`)

```markdown
| ID | Titre | Sévérité | Cas | Statut | Échéance | Ticket |
|---|---|---|---|---|---|---|
| AN-001 | Aucun SMS envoyé à l'annulation | majeure | CT-004 | ouverte | 2026-12-01 | #482 |
```
| Sévérité | Définition | Effet |
|---|---|---|
| **bloquante** | une fonction essentielle est inutilisable, sans contournement ; perte ou corruption de données ; faille de sécurité | **no-go** tant qu'elle est ouverte |
| **majeure** | une fonction importante est dégradée, un contournement existe | go possible **en réserve** si la stratégie le permet, avec échéance |
| **mineure** | gêne sans impact sur le métier (libellé, mise en page) | go possible, en réserve avec échéance |

Statuts : `ouverte`, `en correction`, `corrigée` (livrée, **à re-tester**), `fermée` (re-testée et vérifiée), `rejetée` (pas une anomalie, avec justification). Pour le go / no-go, une anomalie est **ouverte** tant qu'elle n'est ni fermée ni rejetée.

La sévérité se juge sur l'**impact métier**, pas sur la difficulté de correction. C'est le métier qui arbitre en cas de désaccord.

## 9. Le go / no-go

Calculé par le script à partir des critères de la stratégie :

| Décision proposée | Quand |
|---|---|
| **NO-GO** | une bloquante ouverte au-delà du seuil, **ou** trop de majeures ouvertes, **ou** taux de réussite sous le seuil, **ou** cas de priorité haute non exécutés |
| **GO AVEC RÉSERVES** | critères respectés, mais des anomalies majeures ou mineures restent ouvertes : elles deviennent des **réserves**, chacune avec une échéance |
| **GO** | critères respectés, aucune anomalie ouverte |

Le script **propose** ; ce sont des humains (le métier) qui **décident** et signent. Une décision contraire à la proposition est possible : elle se justifie par écrit dans le PV.

Avant la MEP, le go suppose aussi les prérequis d'exploitation : procédure de rollback écrite et testée, sauvegarde faite juste avant, checklist de mise en production revue (plugin ops-doc), communication aux utilisateurs.

## 10. Le PV de recette

Généré par `check_recette.py --pv` dans le dossier de la campagne, puis complété et signé :
- identification : application, version, environnement, période ;
- bilan chiffré : cas prévus, OK, KO, bloqués, non exécutés, taux de réussite, couverture des exigences ;
- anomalies ouvertes par sévérité, et **la liste des réserves** avec leur échéance ;
- chaque critère de sortie, respecté ou non ;
- la décision proposée, la décision prise (cases à cocher), la justification si elle diffère ;
- les prérequis de MEP ;
- les signatures (métier, équipe projet), avec nom, date et fonction.

**Piège classique** : un PV « sans réserve » signé alors que des anomalies restent ouvertes. Il vaut acceptation définitive et fait perdre tout recours sur ces anomalies. Le script le signale (`PV-INCOHERENT`).

## 11. Règles vérifiées par le script

`scripts/check_recette.py` (bibliothèque standard). **ERREUR** = non conforme, **AVERTISSEMENT** = à corriger, **INFO**.

| Code | Niveau | Règle |
|---|---|---|
| `STRUCT` | erreur | `strategie.md`, `exigences.md` ou `cas/` absent |
| `STRAT-SECTION` | erreur | section obligatoire absente de la stratégie |
| `STRAT-CRITERES` | avertissement | critère `go_*` absent de l'en-tête (valeur par défaut utilisée) |
| `EXIG-DOUBLON` / `EXIG-PRIORITE` | erreur | identifiant d'exigence en double / priorité invalide |
| `CAS-CHAMP` | erreur | champ d'en-tête manquant (`id`, `titre`, `exigences`, `priorite`) |
| `CAS-ID-FICHIER` | avertissement | l'`id` ne correspond pas au nom du fichier |
| `CAS-EXIGENCE-INCONNUE` | erreur | le cas couvre une exigence qui n'existe pas |
| `CAS-SECTION` | erreur | section `Préconditions`, `Données` ou `Étapes` absente |
| `CAS-ETAPES` | erreur | aucune étape dans le tableau |
| `CAS-ATTENDU-VIDE` | erreur | une étape sans résultat attendu |
| `CAS-ATTENDU-VAGUE` | avertissement | résultat attendu non vérifiable (« ça fonctionne », « OK », « s'affiche correctement »…) |
| `CAS-DONNEES-VIDES` | avertissement | section Données vide |
| `EXIGENCE-NON-COUVERTE` | erreur | aucune exigence sans cas |
| `ANO-SEVERITE` / `ANO-STATUT` | erreur | sévérité ou statut invalide |
| `ANO-CAS-INCONNU` | avertissement | anomalie rattachée à un cas qui n'existe pas |
| `ANO-SANS-ECHEANCE` | avertissement | anomalie ouverte sans échéance (elle ne peut pas devenir une réserve) |
| `CAMP-CHAMP` | erreur | `version` ou `environnement` absent de la campagne |
| `CAMP-CAS-INCONNU` | erreur | ligne d'exécution pour un cas qui n'existe pas |
| `CAMP-STATUT` | erreur | statut d'exécution invalide |
| `CAMP-KO-SANS-ANOMALIE` | erreur | KO sans anomalie référencée |
| `CAMP-ANOMALIE-INCONNUE` | erreur | anomalie référencée absente d'`anomalies.md` |
| `CAMP-PREUVE-MANQUANTE` | avertissement | cas OK ou KO sans preuve |
| `CAMP-PREUVE-INTROUVABLE` | erreur | lien de preuve vers un fichier absent |
| `CAMP-CAS-ABSENT` | info | cas existant qui n'apparaît pas dans la campagne |
| `PV-INCOHERENT` | erreur | PV « sans réserve » alors que des anomalies sont ouvertes |

## 12. Sources

- ISO/IEC/IEEE 29119-3:2021, *Software testing — Test documentation* (spécification de cas de test, rapport de fin de test) : https://www.iso.org/standard/79429.html
- ISTQB, *Certified Tester Foundation Level Syllabus* (techniques de test, gestion des anomalies, critères de sortie) : https://www.istqb.org/certifications/certified-tester-foundation-level
- OpenClassrooms, *Préparez votre cahier de recette* : https://openclassrooms.com/fr/courses/7365126-concevez-une-strategie-de-test/8214294-preparez-votre-cahier-de-recette
- marche-public.fr, *Vérifications : mises en garde* (VABF, VSR, PV pré-remplis) : https://www.marche-public.fr/Verifications/Marches-publics-Verifications-Mises-en-garde.htm
