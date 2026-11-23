# recette

> **Une recette sert à décider d'une mise en production sur des preuves, pas sur une impression.**

Par défaut, une IA écrit des « tests » du genre « vérifier que la connexion fonctionne » : pas de données, pas de résultat attendu vérifiable, aucun lien avec les exigences, un « OK » sans preuve, et un « prêt pour la prod » décidé à la place du métier. Ce plugin encode la pratique d'une vraie recette (ISO/IEC/IEEE 29119-3, ISTQB, usage MOA / MOE et VABF / VSR) et la fait vérifier par un script.

## Le cahier de recette, dans le repo

```
recette/
├── strategie.md            périmètre, hors périmètre, environnement, données, rôles,
│                           critères d'entrée et de SORTIE (fixés avant l'exécution)
├── exigences.md            EX-001… avec priorité et source (ticket, story)
├── cas/CT-001-….md         préconditions, données, étapes avec résultat attendu OBSERVABLE
├── anomalies.md            AN-001… sévérité bloquante / majeure / mineure, statut, échéance
└── campagnes/2026-11-24-v1.4.0/
    ├── campagne.md         version et environnement constatés, OK / KO / bloqué + preuve par cas
    ├── preuves/            captures annotées, logs, réponses d'API
    └── pv.md               PV généré, complété et signé par des humains
```

## Les skills

| Skill | Pour |
|---|---|
| **recette** | Le standard, les modèles, un exemple complet et le script |
| **recette-plan** | Stratégie, exigences et cas de test à partir des specs, des tickets et du code ; questions au métier sur les critères |
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
- ✔ Taux de réussite des cas exécutés : 80.0 % (seuil ≥ 80 %)
- ✔ Cas de priorité haute exécutés : 100 % (4/4) (seuil ≥ 100 %)
- Anomalies ouvertes : AN-001 (majeure), AN-002 (mineure)
```
Il vérifie 25 règles :
- **la traçabilité** : chaque exigence est couverte ;
- **la qualité des cas** : pas de résultat attendu vide ou vague, comme « ça fonctionne » ;
- **la campagne** : un KO a son anomalie, chaque cas exécuté a une preuve, et les preuves existent ;
- **les anomalies** : chaque anomalie ouverte a une échéance.

Il **propose** la décision et génère le PV : bilan, critères, réserves, prérequis de MEP, signatures. La décision reste humaine. Bibliothèque standard Python uniquement.

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
