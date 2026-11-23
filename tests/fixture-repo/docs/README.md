# rdv : fiche service

> **Qu'est-ce que c'est ?** Une app web de prise de rendez-vous pour un cabinet. Les clients réservent un créneau, le cabinet gère son agenda.

| | |
|---|---|
| **Responsable** | Camille R. (dev + ops) |
| **Suppléant** | — *(à définir : aujourd'hui, une seule personne connaît l'app)* |
| **Criticité** | **Moyenne** : une indisponibilité bloque les réservations mais pas le cabinet (il peut prendre les RDV par téléphone) |
| **Horaires de service** | 7h–21h, 7j/7 (peu de trafic la nuit) |
| **Astreinte** | Best effort, notifications Discord `#rdv-alertes` |
| **SLO** | 99,5 % de disponibilité mensuelle (≈ 3 h 36 d'indisponibilité tolérée par mois), p95 de latence < 500 ms |
| **RPO / RTO** | 5 min / 2 h (mesurés, voir [reprise](reprise.md)) |

## Liens

| Quoi | Où |
|---|---|
| Prod | https://rdv.example.fr |
| Staging | https://staging.rdv.example.fr |
| Code de l'app | `gitlab.com/acme/rdv-app` |
| Repo GitOps (ce repo) | `gitlab.com/acme/rdv-gitops` |
| ArgoCD | https://argocd.example.fr/applications/rdv-prod |
| Dashboard Grafana | https://grafana.example.fr/d/rdv-overview |
| Dashboard CNPG | https://grafana.example.fr/d/cloudnative-pg |
| Logs (Loki) | Grafana > Explore > `{namespace="rdv-prod"}` |
| Alertes | Alertmanager > `service=rdv` |
| Sonde externe | Uptime Kuma (VPS hors cluster) |
| Deadman switch | healthchecks.io, check `rdv-watchdog` |

## Composants

| Composant | Techno | Ressource Kube | Namespace |
|---|---|---|---|
| Front | Nginx (SPA statique) | `Deployment/rdv-front` | `rdv-prod` |
| API | Go 1.23 | `Deployment/rdv-api` | `rdv-prod` |
| Base | PostgreSQL 17 via CNPG | `Cluster/rdv-pg` (2 instances) | `rdv-prod` |
| Envoi d'e-mails | Job CronJob Go | `CronJob/rdv-rappels` | `rdv-prod` |

## Dépendances

| Dépendance | Sens | Si elle tombe |
|---|---|---|
| PostgreSQL (`rdv-pg-rw`) | API → PG | **App inutilisable** : l'API renvoie des 503 |
| SMTP Brevo | CronJob → Brevo | Les rappels ne partent plus, le reste fonctionne |
| S3 (Scaleway, `rdv-backups`) | CNPG → S3 | Plus de backups ni d'archivage WAL ; le RPO se dégrade, l'app tourne |
| cert-manager + Let's Encrypt | — | Le certificat expire au bout de 90 jours si le renouvellement échoue |

## Accès
- **Cluster** : kubeconfig dans le gestionnaire de mots de passe (Bitwarden, entrée `k3s-prod`).
- **Base en lecture** : `kubectl cnpg psql rdv-pg -n rdv-prod`. Ne jamais écrire en prod à la main sans l'avoir noté dans le canal.
- **Clé SOPS (age)** : Bitwarden, entrée `sops-age-rdv`. **Sans elle, impossible de reconstruire le cluster.**

## Commandes utiles
```bash
kubectl get pods -n rdv-prod
kubectl cnpg status rdv-pg -n rdv-prod
kubectl logs -n rdv-prod deploy/rdv-api --since=15m
argocd app get rdv-prod
```

Connexion de secours : `postgres://app:S3cr3tP4ssw0rd@rdv-pg-rw:5432/app`
Voir aussi [le vieux wiki](wiki/ancien.md) et [[architecture]].
