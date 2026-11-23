# PV de recette : rdv v1.4.0

> Généré par `check_recette.py` le 2026-11-26. La décision ci-dessous est une **proposition** calculée à partir des critères de la stratégie : elle est relue, complétée et **signée par des humains**.

| | |
|---|---|
| **Application** | rdv |
| **Version recettée** | 1.4.0 |
| **Environnement** | recette — https://recette.rdv.example.fr (build 1.4.0-rc2, puis rc3 le 25/11 pour AN-003) |
| **Période** | 2026-11-24 → 2026-11-25 |
| **Campagne** | `2026-11-24-v1.4.0` |

## Bilan

| Cas prévus | OK | KO | Bloqués | Non exécutés | Taux de réussite | Exigences couvertes |
|---|---|---|---|---|---|---|
| 6 | 4 | 1 | 0 | 1 | 80.0 % | 4 / 5 |

## Critères de sortie

| Critère | Seuil | Constaté | Respecté |
|---|---|---|---|
| Anomalies bloquantes ouvertes | ≤ 0 | 0 | oui |
| Anomalies majeures ouvertes | ≤ 1 | 1 | oui |
| Taux de réussite des cas exécutés | ≥ 80 % | 80.0 % | oui |
| Cas de priorité haute exécutés | ≥ 100 % | 100 % (4/4) | oui |

## Anomalies ouvertes

| ID | Titre | Sévérité | Statut | Échéance | Ticket |
|---|---|---|---|---|---|
| AN-001 | Annulation : le SMS n'est pas envoyé (aucune entrée dans le journal SMS) ; contournement : appel du patient par le secrétariat | majeure | en correction | 2026-12-04 | #482 |
| AN-002 | Création : le motif long est tronqué sans infobulle dans la liste | mineure | ouverte | 2026-12-18 | #487 |

## Réserves

En cas d'acceptation, les anomalies suivantes sont levées comme **réserves**, à corriger avant leur échéance :

- **AN-001** (majeure) : Annulation : le SMS n'est pas envoyé (aucune entrée dans le journal SMS) ; contournement : appel du patient par le secrétariat. Échéance : 2026-12-04.
- **AN-002** (mineure) : Création : le motif long est tronqué sans infobulle dans la liste. Échéance : 2026-12-18.

## Décision

**Décision proposée par les critères : GO AVEC RÉSERVES**

Décision prise :

- [ ] GO sans réserve
- [ ] GO avec réserves (liste ci-dessus)
- [ ] NO-GO

Justification (obligatoire si la décision prise diffère de la proposition) :

> 

## Prérequis de mise en production

- [ ] Procédure de rollback écrite et testée
- [ ] Sauvegarde des données prévue juste avant la MEP
- [ ] Checklist de mise en production revue
- [ ] Utilisateurs et support informés (date, impacts, contact)

## Signatures

| Rôle | Nom | Fonction | Date | Signature |
|---|---|---|---|---|
| Métier (MOA) | | | | |
| Équipe projet (MOE) | | | | |
