---
id: CT-008
titre: Restauration de la base depuis la sauvegarde de la nuit après migration 1.4.0
exigences: EX-006
priorite: haute
type: exploitation
---
## Objectif
Prouver qu'on sait revenir en arrière sur les données si la mise en production tourne mal (prérequis de la MEP).

## Préconditions
- Version 1.4.0 déployée en recette, migration de schéma appliquée.
- Sauvegarde CNPG de la nuit du 23/11/2026 terminée (`kubectl get backups -n rdv-recette`).

## Données
- Cluster source : `rdv-pg` (namespace `rdv-recette`) ; nombre de rendez-vous relevé avant : requête `select count(*) from rendez_vous;`
- Procédure suivie : `docs/procedures/restauration-pitr.md` (dépôt GitOps)

## Étapes
| # | Action | Résultat attendu |
|---|---|---|
| 1 | Relever le nombre de rendez-vous sur `rdv-pg` | Un nombre N est relevé et noté dans la preuve |
| 2 | Créer le cluster `rdv-pg-restore` depuis la sauvegarde de la nuit, en suivant la procédure | Le cluster passe à l'état « Cluster in healthy state » en moins de 30 minutes |
| 3 | Compter les rendez-vous sur `rdv-pg-restore` | Le nombre est égal à N (aucun rendez-vous créé après la sauvegarde) |
| 4 | Pointer l'app de recette vers `rdv-pg-restore` et ouvrir l'agenda du 24/11/2026 | L'agenda affiche les 12 rendez-vous attendus, sans erreur |
