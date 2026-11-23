# NOM-APP : fiche service

> **Qu'est-ce que c'est ?** TODO(ops-doc): une phrase, ce que fait l'app et pour qui.

| | |
|---|---|
| **Responsable** | TODO(ops-doc): nom ou équipe |
| **Suppléant** | TODO(ops-doc): qui d'autre sait intervenir ? |
| **Criticité** | TODO(ops-doc): haute / moyenne / basse, et ce que ça bloque si l'app tombe |
| **Horaires de service** | TODO(ops-doc) |
| **Astreinte** | TODO(ops-doc): qui est prévenu, par quel canal |
| **SLO** | TODO(ops-doc): disponibilité, latence |
| **RPO / RTO** | TODO(ops-doc) (voir [reprise](reprise.md)) |

## Sommaire de la doc
- [Architecture](architecture.md)
- [Configuration et secrets](config.md)
- [Dimensionnement](dimensionnement.md)
- [Plan de reprise](reprise.md)
- [Checklist de mise en production](checklist-production.md)
- Runbooks : `runbooks/`, procédures : `procedures/`, décisions : `adr/`, incidents : `postmortems/`

## Liens

| Quoi | Où |
|---|---|
| Prod | |
| Staging | |
| Code de l'app | |
| Repo GitOps | |
| ArgoCD | |
| Dashboard | |
| Logs | |
| Alertes | |

## Composants

| Composant | Techno | Ressource Kube | Namespace |
|---|---|---|---|
| | | | |

## Dépendances

| Dépendance | Sens | Si elle tombe |
|---|---|---|
| | | |

## Accès
- **Cluster** : TODO(ops-doc): où se trouve le kubeconfig (sans la valeur)
- **Base** : 
- **Clé de déchiffrement des secrets** : TODO(ops-doc): où, en dehors du cluster ?

## Commandes utiles
```bash
kubectl get pods -n NAMESPACE
```
