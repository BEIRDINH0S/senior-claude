---
version: 1.4.0
environnement: recette — https://recette.rdv.example.fr (build 1.4.0-rc2, puis rc3 le 25/11 pour AN-003)
debut: 2026-11-24
fin: 2026-11-25
---
# Campagne de recette v1.4.0

## Exécution
| Cas | Statut | Testeur | Date | Anomalie | Preuve |
|---|---|---|---|---|---|
| CT-001 | OK | Camille R. | 2026-11-24 | | [capture](preuves/CT-001-connexion.png) |
| CT-002 | OK | Camille R. | 2026-11-25 | AN-003 (corrigée en rc3, re-testée) | [réponses](preuves/CT-002-messages.txt) |
| CT-003 | OK | Camille R. | 2026-11-24 | AN-002 | [capture](preuves/CT-003-creation.png) |
| CT-004 | KO | Camille R. | 2026-11-24 | AN-001 | [capture](preuves/CT-004-annulation.png) · [journal SMS](preuves/CT-004-sms-log.txt) |
| CT-005 | OK | Camille R. | 2026-11-24 | | [journal SMS](preuves/CT-005-rappels.txt) |
| CT-006 | non exécuté | | | | |
| CT-007 | OK | Camille R. + secrétariat | 2026-11-25 | AN-002 | [notes de session](preuves/CT-007-session.txt) |
| CT-008 | OK | Camille R. | 2026-11-25 | | [journal de restauration](preuves/CT-008-restauration.txt) |

## Notes
- CT-006 (priorité basse) reporté : environnement indisponible pour le téléchargement le 25/11 ; à exécuter dans la campagne 1.4.1.
- AN-003 détectée le 24/11 (rc2), corrigée en rc3 le 25/11, CT-002 rejoué et OK.
