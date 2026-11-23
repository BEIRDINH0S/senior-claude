# Alerte : NomDeLAlerte

> Le nom du fichier = le nom de l'alerte dans la `PrometheusRule`. Le `runbook_url` de l'alerte pointe ici.

| | |
|---|---|
| **Sévérité** | critical / warning |
| **Expression** | `la PromQL de l'alerte` |
| **Défini dans** | `alerts/xxx.yaml` |

## Signification
Ce qui est mesuré, en une phrase. Ce que ça veut dire concrètement.

## Impact
Ce que vivent les utilisateurs **maintenant**. Ce qui se passe si on ne fait rien pendant 1 h, puis 24 h.

## Diagnostic
Du plus probable au moins probable. Des commandes et des requêtes à copier-coller.

1. ...
2. ...

## Remédiation
Par cause identifiée au diagnostic.

### Cause A
1. ...

### Cause B
1. ...

## Vérifier que c'est résolu
Ce qui doit être vrai pour clôturer (l'alerte repasse en `resolved`, plus une vérification côté utilisateur).

## Escalade
Qui appeler, et à partir de quand.

## Historique
- AAAA-MM-JJ : déclenchée, cause X, lien vers le post-mortem
