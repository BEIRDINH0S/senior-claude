# Anomalies

Sévérité = impact métier (bloquante, majeure, mineure). Priorité = urgence de correction (haute, moyenne, basse). Statut : ouverte, différée, en correction, corrigée (à re-tester), réouverte, fermée, rejetée, doublon.
Le détail de chaque anomalie (étapes pour reproduire, attendu, obtenu, version, preuves) est dans le ticket.

| ID | Titre | Sévérité | Priorité | Cas | Statut | Échéance | Ticket |
|---|---|---|---|---|---|---|---|
| AN-001 | Annulation : le SMS n'est pas envoyé (aucune entrée dans le journal SMS) ; contournement : appel du patient par le secrétariat | majeure | haute | CT-004 | en correction | 2026-12-04 | #482 |
| AN-002 | Création : le motif long est tronqué sans infobulle dans la liste | mineure | basse | CT-003 | ouverte | 2026-12-18 | #487 |
| AN-003 | Connexion : message d'erreur différent pour un compte inexistant | bloquante | haute | CT-002 | fermée | 2026-11-25 | #479 |
