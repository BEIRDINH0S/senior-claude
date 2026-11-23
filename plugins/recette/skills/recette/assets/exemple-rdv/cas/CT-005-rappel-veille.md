---
id: CT-005
titre: Le rappel SMS part la veille à 18 h
exigences: EX-004
priorite: moyenne
type: fonctionnel
---
## Objectif
Les patients ayant rendez-vous le lendemain reçoivent un rappel.

## Préconditions
- Horloge de l'environnement de recette avancée au 23/11/2026 17:59 (`make horloge-recette T=2026-11-23T17:59`).

## Données
- Les 12 rendez-vous du 24/11/2026 du jeu fictif (dont 2 annulés)

## Étapes
| # | Action | Résultat attendu |
|---|---|---|
| 1 | Attendre 18:00 (heure simulée), puis ouvrir `/admin/sms-log` | 10 SMS « Rappel : rendez-vous demain 24/11 à HH:MM » horodatés 18:00, un par rendez-vous non annulé |
| 2 | Vérifier les 2 rendez-vous annulés | Aucun rappel envoyé pour eux |
