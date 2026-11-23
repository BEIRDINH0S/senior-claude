# À tester en recette

Alimenté pendant le développement, à chaque changement de comportement (hook de commit du plugin recette).
Chaque entrée devient un cas de test (colonne Cas), ou est marquée « hors recette » avec la raison.
Risque : haut, moyen, bas.

| Date | Changement | Réf. | Exigence | À vérifier en recette | Risque | Cas |
|---|---|---|---|---|---|---|
| 2026-11-04 | Remplacement du fournisseur SMS (API v2) | !131 | EX-003, EX-004 | Annulation et rappel envoient bien le SMS ; panne du fournisseur gérée sans bloquer l'annulation | haut | CT-004, CT-005 |
| 2026-11-08 | Message d'erreur de connexion unifié | !134 | EX-001 | Même message pour un compte inexistant et un mot de passe faux | moyen | CT-002 |
| 2026-11-12 | Verrou sur le créneau à la création (anti double réservation) | !138 | EX-002 | Deux réservations simultanées du même créneau : une seule réussit | haut | CT-003, CT-007 |
| 2026-11-15 | Migration de schéma : table rendez_vous partitionnée par mois | !141 | EX-006 | La sauvegarde de la nuit se restaure et l'agenda s'affiche | haut | CT-008 |
| 2026-11-18 | Refactoring du module d'export (aucun changement de comportement) | !144 | EX-005 | Export identique à la version précédente | bas | CT-006 |
| 2026-11-19 | Mise à jour de la bibliothèque de logs (pino 9 → 10) | !145 | — | Aucun comportement visible ; couvert par les tests automatisés | bas | hors recette : sans impact fonctionnel |
