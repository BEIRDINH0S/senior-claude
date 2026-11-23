---
application: rdv
go_bloquantes_max: 0
go_majeures_max: 1
go_taux_reussite_min: 80
go_priorite_haute_executee: 100
---
# Stratégie de recette : rdv v1.4.0

## Périmètre
Version 1.4.0 : connexion, création et annulation de rendez-vous, envoi du SMS d'annulation, rappel automatique la veille, export CSV de l'agenda (notes de version : `CHANGELOG.md` § 1.4.0).

## Hors périmètre
- Paiement en ligne : non livré dans cette version.
- Charge au-delà de 50 utilisateurs simultanés : campagne de performance séparée, prévue en 1.5.
- Application mobile : hors projet.

## Environnement
Recette : https://recette.rdv.example.fr, build `1.4.0-rc2`, même chart Helm et même version de PostgreSQL (CNPG) qu'en prod. Le fournisseur SMS est **bouchonné** : les SMS sont écrits dans un journal consultable sur `/admin/sms-log` au lieu d'être envoyés.

## Données de test
Jeu fictif `seed-recette.sql` (5 praticiens, 40 patients aux noms et téléphones inventés), rechargé avant chaque campagne par `make seed-recette`. Comptes de test : `praticien.recette@example.org`, `secretariat.recette@example.org` (mots de passe dans le coffre de l'équipe, entrée « recette rdv »).

## Rôles
| Rôle | Qui |
|---|---|
| Préparation des cas | Équipe projet (Camille R.) |
| Exécution | Camille R., avec agent-browser pour les captures |
| Arbitrage des anomalies | Responsable métier du cabinet + équipe projet |
| Signature du PV (métier) | Responsable du cabinet |

## Critères d'entrée
- [x] Version 1.4.0-rc2 déployée en recette
- [x] Tests automatisés verts sur cette version (pipeline #1287)
- [x] Jeu de données rechargé
- [x] Notes de version disponibles

## Critères de sortie (go / no-go)
Aucune anomalie bloquante ouverte. Au plus une majeure ouverte, avec un contournement documenté et une échéance. Au moins 80 % des cas exécutés réussis. Tous les cas de priorité haute exécutés.

## Planning
| Étape | Date |
|---|---|
| Livraison en recette | 2026-11-23 |
| Exécution | 2026-11-24 → 2026-11-25 |
| Comité go / no-go | 2026-11-26 |
| MEP | 2026-11-30 |
