# Plan de reprise (PRA)

| | Cible | Mesuré | Dernier test |
|---|---|---|---|
| **RPO** (données perdues au maximum) | 15 min | ≈ 5 min (`archive_timeout` par défaut) | 2026-11-18 |
| **RTO** (temps pour revenir en service) | 4 h | **1 h 52** | 2026-11-18 (game day) |

## Scénarios

| Scénario | Ce qui se passe | Quoi faire |
|---|---|---|
| Un pod API meurt | Kube le redémarre, l'autre replica sert | Rien |
| Le primaire PG meurt | CNPG promeut la réplique (≈ 30 s) | Vérifier `kubectl cnpg status`, voir [RdvApiDown](runbooks/RdvApiDown.md) |
| Un nœud meurt | Pods replanifiés ; l'instance PG du nœud est reconstruite depuis le primaire | Vérifier que CNPG retrouve 2 instances |
| Données corrompues / `DELETE` accidentel | — | [restauration-pitr](procedures/restauration-pitr.md) |
| **Cluster entièrement perdu** | — | **Reconstruction complète ci-dessous** |

## Reconstruction complète

### Prérequis (hors du cluster)
- [ ] Accès Bitwarden : kubeconfig, **clé age SOPS**, credentials S3, token GitLab
- [ ] Repo `rdv-gitops` accessible
- [ ] Bucket `rdv-backups` intact

### Étapes (durées mesurées au game day du 2026-11-18)

| # | Étape | Durée |
|---|---|---|
| 1 | Nouveau cluster k3s (3 nœuds) | 20 min |
| 2 | Installer ArgoCD : `kubectl apply -k platform/argocd/bootstrap` | 5 min |
| 3 | Injecter la clé age : `kubectl -n argocd create secret generic sops-age --from-file=keys.txt` | 2 min |
| 4 | Appliquer l'app-of-apps : `kubectl apply -f platform/root-app.yaml` | 2 min |
| 5 | Attendre platform (cert-manager, opérateur CNPG, monitoring) | 15 min |
| 6 | **Restaurer PG** : passer `apps/rdv-pg` en mode recovery (voir [restauration-pitr](procedures/restauration-pitr.md)), commit, sync | 35 min |
| 7 | Vérifier que l'app est saine (pods Ready, login, création d'un RDV de test) | 10 min |
| 8 | Basculer le DNS vers la nouvelle IP | 5 min + propagation |
| 9 | Remettre `apps/rdv-pg` en mode normal (nouveau `serverName` d'archivage) | 10 min |

### Problèmes rencontrés au game day (et corrigés depuis)
- La clé age n'était que dans le cluster → copiée dans Bitwarden.
- Le CRD `ObjectStore` du plugin Barman Cloud avait été installé à la main → ajouté à `platform/`.
- Le DNS avait un TTL de 24 h → réduit à 300 s.

## Prochain game day
**2027-05** (tous les 6 mois), ou après un changement d'infra majeur.
