---
application: NOM-APP
go_bloquantes_max: 0
go_majeures_max: 0
go_taux_reussite_min: 95
go_priorite_haute_executee: 100
---
# Stratégie de recette : NOM-APP

## Périmètre
Fonctionnalités et version recettées (liens vers les tickets / notes de version).

## Hors périmètre
Ce qui n'est PAS testé dans cette recette, et pourquoi. Le PV ne couvre pas ces points.

## Environnement
URL, version déployée, configuration ; écarts avec la prod (intégrations bouchonnées, volumétrie…).

## Données de test
Jeux de données fictifs ou anonymisés, comptes de test (sans mot de passe ici), comment les réinitialiser.

## Rôles
| Rôle | Qui |
|---|---|
| Préparation des cas | |
| Exécution | |
| Arbitrage des anomalies | |
| Signature du PV (métier) | |

## Critères d'entrée
- [ ] Version livrée et déployée sur l'environnement de recette
- [ ] Tests automatisés verts sur cette version
- [ ] Données de test en place
- [ ] Notes de version disponibles

## Critères de sortie (go / no-go)
Les seuils de l'en-tête, en clair : aucune anomalie bloquante ouverte ; au plus N majeures ouvertes, en réserve avec échéance ;
au moins 95 % des cas exécutés réussis ; 100 % des cas de priorité haute exécutés.

## Planning
| Étape | Date |
|---|---|
| Livraison en recette | |
| Exécution | |
| Comité go / no-go | |
| MEP | |
