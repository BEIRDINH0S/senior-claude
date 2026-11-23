---
id: CT-002
titre: Un mot de passe faux est refusé sans révéler si le compte existe
exigences: EX-001
priorite: haute
type: securite
---
## Objectif
Le message d'erreur est le même pour un compte existant et un compte inexistant (pas d'énumération des comptes).

## Préconditions
- Navigateur sans session ouverte.

## Données
- Compte existant : `praticien.recette@example.org`, mot de passe `faux-mdp-123`
- Compte inexistant : `personne@example.org`, mot de passe `faux-mdp-123`

## Étapes
| # | Action | Résultat attendu |
|---|---|---|
| 1 | Se connecter avec le compte existant et le mot de passe faux | Message « E-mail ou mot de passe incorrect » ; on reste sur le formulaire |
| 2 | Se connecter avec le compte inexistant | Exactement le même message « E-mail ou mot de passe incorrect » |
