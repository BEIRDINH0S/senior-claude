---
id: CT-004
titre: Annuler un rendez-vous confirmé libère le créneau et envoie un SMS
exigences: EX-003
priorite: haute
type: fonctionnel
---
## Objectif
L'annulation libère le créneau et prévient le patient par SMS.

## Préconditions
- Connecté avec le compte secrétariat ; rendez-vous du 24/11/2026 à 10:30 (Inès Moreau, « Première visite ») au statut « Confirmé ».

## Données
- Compte : `secretariat.recette@example.org`
- Téléphone du patient dans le jeu fictif : 06 55 44 33 22

## Étapes
| # | Action | Résultat attendu |
|---|---|---|
| 1 | Agenda du 24/11/2026, cliquer sur « Annuler » de la ligne 10:30, puis confirmer | Le statut passe à « Annulé » ; message « Rendez-vous annulé, SMS envoyé » |
| 2 | Ouvrir `/admin/sms-log` | Une entrée vers 06 55 44 33 22 contenant « annulé » et « 24/11 à 10:30 », horodatée de l'annulation |
| 3 | Revenir à l'agenda, cliquer sur « + Nouveau rendez-vous » à 10:30 | Le créneau 10:30 est proposé comme libre |
