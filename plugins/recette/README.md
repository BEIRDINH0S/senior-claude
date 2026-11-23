# recette

> **Une recette sert à décider d'une mise en production sur des preuves, pas sur une impression.**

Par défaut, une IA écrit des « tests » du genre « vérifier que la connexion fonctionne » : pas de données, pas de résultat attendu vérifiable, aucun lien avec les exigences, un « OK » sans preuve, et un « prêt pour la prod » décidé à la place du métier. Ce plugin encode la pratique d'une vraie recette et la fait vérifier par un script. Le standard s'appuie, section par section, sur le **syllabus ISTQB Foundation Level v4.0**, le **syllabus ISTQB / CFTL Tests d'acceptation** et l'**ISO/IEC/IEEE 29119-3**, ainsi que sur l'usage français (MOA / MOE, VABF / VSR).

## Au fil du développement : `a-tester.md` et le hook

Ce qu'il faudra vérifier en recette se note **au moment où le changement est fait**, pas de mémoire la veille de la recette :
```markdown
| Date | Changement | Réf. | Exigence | À vérifier en recette | Risque | Cas |
| 2026-11-12 | Verrou sur le créneau à la création | !138 | EX-002 | Deux réservations simultanées : une seule réussit | haut | |
```
Le **hook de commit** du plugin l'impose aux agents. Un commit qui change du code applicatif dans un repo doté de `recette/` doit modifier `a-tester.md` (ou un cas). Sinon, son message doit porter `Recette: sans impact (raison)`, ce qui laisse une trace dans l'historique. Tests, doc, fichiers de lock et CI ne déclenchent rien, et le périmètre se règle dans `recette/.recette.json`. Au moment du PV, les entrées jamais transformées en cas apparaissent comme risques résiduels.

## Le cahier de recette, dans le repo

```
recette/
├── a-tester.md             alimenté au fil du dev (hook de commit)
├── strategie.md            périmètre, types de recette (UAT, exploitation…), risques produit,
│                           environnement, données, rôles, critères d'entrée et de SORTIE
├── exigences.md            EX-001… avec critères d'acceptation, priorité et source
├── cas/CT-001-….md         préconditions, données, étapes avec résultat attendu OBSERVABLE
├── anomalies.md            AN-001… sévérité (impact) ET priorité (urgence), statut, échéance
└── campagnes/2026-11-24-v1.4.0/
    ├── campagne.md         version et environnement constatés, OK / KO / bloqué + preuve par cas
    ├── preuves/            captures annotées, logs, réponses d'API
    └── pv.md               PV généré, complété et signé par des humains
```

## Les skills

| Skill | Pour |
|---|---|
| **recette** | Le standard, les modèles, un exemple complet, le script, et la tenue d'`a-tester.md` pendant le dev |
| **recette-plan** | Stratégie (types de recette, risques), exigences et critères d'acceptation, cas dérivés par technique (partitions, limites, tables de décision, états, sessions exploratoires) ; transforme `a-tester.md` en cas |
| **recette-run** | Exécuter la campagne (agent-browser pour le web), observer, prouver, ouvrir et qualifier les anomalies, re-tester |
| **recette-pv** | Vérifier, calculer le go / no-go, produire le PV, détecter un PV « sans réserve » incohérent |

## Le script

```bash
python3 plugins/recette/skills/recette/scripts/check_recette.py recette/ --campagne 2026-11-24-v1.4.0 --pv
```
```
**CONFORME** : 0 erreur(s), 0 avertissement(s), 0 info(s)

## Go / no-go : campagne `2026-11-24-v1.4.0` (v1.4.0)
**Décision proposée : GO AVEC RÉSERVES**
- ✔ Anomalies bloquantes ouvertes : 0 (seuil ≤ 0)
- ✔ Anomalies majeures ouvertes : 1 (seuil ≤ 1)
- ✔ Taux de réussite des cas exécutés : 85.7 % (seuil ≥ 80 %)
- ✔ Cas de priorité haute exécutés : 100 % (6/6) (seuil ≥ 100 %)
- ✔ Exigences couvertes par un cas exécuté : 83 % (5/6) (seuil ≥ 80 %)
- Anomalies ouvertes : AN-001 (majeure), AN-002 (mineure)
```
Il vérifie 33 règles :
- **la traçabilité** : chaque exigence est couverte ;
- **la qualité des cas** : pas de résultat attendu vide ou vague, comme « ça fonctionne » ;
- **la campagne** : un KO a son anomalie, chaque cas exécuté a une preuve, et les preuves existent ;
- **les anomalies** : priorité distincte de la sévérité, et une échéance pour chaque anomalie ouverte ;
- **la stratégie** : analyse des risques produit, et le suivi d'`a-tester.md`.

Il **propose** la décision et génère un document qui combine le rapport de fin de recette et le PV : bilan, critères, réserves, changements sans cas, écarts, obstacles, risques résiduels, enseignements, décision (dont le GO partiel), prérequis de MEP, signatures. La décision reste humaine. Bibliothèque standard Python uniquement.

Voir l'[exemple complet](skills/recette/assets/exemple-rdv/), avec son [PV](skills/recette/assets/exemple-rdv/campagnes/2026-11-24-v1.4.0/pv.md).

## Avec les autres plugins

- **doc-screenshots** : les captures annotées servent de preuves.
- **ops-doc** : la checklist de mise en production et la procédure de rollback font partie des prérequis de MEP.

## Installation

```
/plugin marketplace add BEIRDINH0S/senior-claude
/plugin install recette@senior-claude
```

## Licence

[MIT](../../LICENSE)
