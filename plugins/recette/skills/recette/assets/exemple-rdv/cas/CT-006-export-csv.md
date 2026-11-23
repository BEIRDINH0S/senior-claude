---
id: CT-006
titre: Export CSV de l'agenda du jour
exigences: EX-005
priorite: basse
type: fonctionnel
---
## Objectif
L'export contient les rendez-vous affichés.

## Préconditions
- Connecté avec le compte secrétariat, agenda du 24/11/2026 affiché.

## Données
- Agenda du 24/11/2026 du jeu fictif (12 rendez-vous)

## Étapes
| # | Action | Résultat attendu |
|---|---|---|
| 1 | Cliquer sur « Exporter » | Un fichier `agenda-2026-11-24.csv` est téléchargé |
| 2 | Ouvrir le fichier | 13 lignes (en-tête + 12) ; colonnes heure, patient, motif, statut ; séparateur « ; » ; encodage UTF-8 (accents corrects) |
