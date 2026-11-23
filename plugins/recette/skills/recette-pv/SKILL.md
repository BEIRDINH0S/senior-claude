---
name: recette-pv
description: >
  Fait le bilan d'une campagne de recette : vérifie le cahier (conformité, traçabilité, preuves), calcule
  le go / no-go proposé à partir des critères de sortie fixés dans la stratégie, liste les réserves avec
  leurs échéances, et génère le PV de recette à faire signer (décision, prérequis de mise en production,
  signatures MOA / MOE), en signalant les incohérences comme un PV « sans réserve » avec des anomalies
  ouvertes. À utiliser pour « fais le PV de recette », « bilan de la campagne », « on est go pour la MEP ? »,
  « comité go / no-go », « vérifie le cahier de recette ».
---

# recette-pv

Lis `../recette/references/standard.md`, sections 9 et 10, à partir du dossier de ce skill.

## 1. Vérifier

```bash
python3 <dossier de ce skill>/../recette/scripts/check_recette.py recette/ --campagne <nom>
```
- **Des erreurs** (KO sans anomalie, preuve introuvable, exigence non couverte, statut invalide) : le bilan serait faux. Liste-les, et fais-les corriger (recette-run ou recette-plan) avant de produire le PV. Si l'utilisateur insiste pour un PV quand même, mentionne les erreurs en tête du PV.
- **Relis aussi ce que le script ne voit pas** :
  - les preuves montrent-elles vraiment le résultat attendu ? Ouvre deux ou trois captures au hasard ;
  - la sévérité des anomalies ouvertes est-elle cohérente avec leur description ? Une « mineure » qui bloque une fonction essentielle est une bloquante mal classée ;
  - les cas `non exécuté` ou `bloqué` de priorité haute ont-ils une raison écrite ?

## 2. Le go / no-go

Le script le calcule à partir des critères de l'en-tête de `strategie.md` :
- **NO-GO** : un critère n'est pas respecté. Dis lequel, et ce qu'il faudrait pour passer : corriger telle anomalie, exécuter tels cas.
- **GO AVEC RÉSERVES** : les critères sont respectés, mais des anomalies majeures ou mineures restent ouvertes. Chacune devient une réserve et **doit avoir une échéance** (`ANO-SANS-ECHEANCE` sinon).
- **GO** : aucune anomalie ouverte.

Tu présentes la proposition et ses raisons, sans plaider pour un go. Si l'utilisateur veut un go malgré un critère non respecté, c'est possible, mais c'est une **décision humaine justifiée par écrit** dans le PV, pas une modification des seuils après coup. Ne modifie jamais les critères de la stratégie pour faire passer une campagne.

## 3. Le PV

```bash
python3 <dossier de ce skill>/../recette/scripts/check_recette.py recette/ --campagne <nom> --pv
```
- Il écrit `pv.md` dans le dossier de la campagne. S'il existe déjà, il écrit `pv.proposition.md` : un PV en cours de signature n'est jamais écrasé.
- Relis le PV généré. Ajoute si besoin un paragraphe « Points d'attention » : contournements à communiquer au support, fonctionnalités désactivées, risques connus.
- **Les cases de décision et les signatures restent vides** : c'est au métier de les remplir. Ne coche rien à sa place.
- Les prérequis de MEP : si le repo suit le plugin **ops-doc**, renvoie vers `docs/checklist-production.md` et `docs/procedures/deploiement-rollback.md`.
- Export pour signature, si demandé : `pandoc pv.md -o PV-recette-vX.Y.Z.docx` (ou `.pdf`), avec le modèle du client s'il en impose un.

## 4. Après signature

Relance le script : `PV-INCOHERENT` signale un PV coché « GO sans réserve » alors que des anomalies restent ouvertes. Ce PV vaudrait acceptation définitive, et ferait perdre tout recours sur ces anomalies.

## Rendre la main

En quelques lignes :
- la décision proposée et pourquoi (les critères, avec leurs valeurs) ;
- les réserves et leurs échéances ;
- ce qu'il reste à faire : signatures, prérequis de MEP, cas reportés à la prochaine campagne ;
- le chemin du PV.
