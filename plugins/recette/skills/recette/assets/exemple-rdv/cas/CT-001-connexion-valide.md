---
id: CT-001
titre: Connexion d'un praticien avec des identifiants valides
exigences: EX-001
priorite: haute
type: fonctionnel
---
## Objectif
Un praticien accède à son agenda après connexion.

## Préconditions
- Navigateur sans session ouverte sur rdv.

## Données
- Compte : `praticien.recette@example.org` (mot de passe : coffre, entrée « recette rdv »)

## Étapes
| # | Action | Résultat attendu |
|---|---|---|
| 1 | Ouvrir https://recette.rdv.example.fr | Le formulaire « Connexion » s'affiche avec les champs E-mail et Mot de passe |
| 2 | Saisir l'e-mail et le mot de passe du compte, cliquer sur « Se connecter » | L'agenda du jour s'affiche, titre « Agenda du jour », avec l'adresse du compte en haut à droite |
