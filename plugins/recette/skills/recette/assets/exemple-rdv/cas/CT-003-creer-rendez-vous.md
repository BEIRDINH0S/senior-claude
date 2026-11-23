---
id: CT-003
titre: Création d'un rendez-vous sur un créneau libre
exigences: EX-002
priorite: haute
type: fonctionnel
---
## Objectif
Le secrétariat crée un rendez-vous et il apparaît dans l'agenda.

## Préconditions
- Connecté avec le compte secrétariat ; le créneau du 24/11/2026 à 15:00 est libre pour le Dr Martin.

## Données
- Compte : `secretariat.recette@example.org`
- Patient : Léa Robin (jeu fictif), motif « Suivi »

## Étapes
| # | Action | Résultat attendu |
|---|---|---|
| 1 | Agenda du 24/11/2026, cliquer sur « + Nouveau rendez-vous » | Le formulaire de création s'ouvre, date pré-remplie au 24/11/2026 |
| 2 | Choisir 15:00, Dr Martin, patient Léa Robin, motif « Suivi », valider | Message « Rendez-vous créé » ; une ligne 15:00 Léa Robin, statut « À confirmer », apparaît dans l'agenda |
