# Inventaire de configuration

> Les **noms** et l'**emplacement** de chaque variable et de chaque secret. **Jamais les valeurs.**

## Variables d'environnement : `rdv-api`

| Variable | Exemple | Obligatoire | Défini dans |
|---|---|---|---|
| `DATABASE_URL` | — | oui | Secret `rdv-pg-app` (généré par CNPG, clé `uri`) |
| `HTTP_PORT` | `8080` | non | `apps/rdv/base/deployment.yaml` |
| `LOG_LEVEL` | `info` | non | ConfigMap `rdv-config` |
| `LOG_FORMAT` | `json` | non | ConfigMap `rdv-config` |
| `PUBLIC_URL` | `https://rdv.example.fr` | oui | Overlay `apps/rdv/overlays/prod` |
| `SESSION_SECRET` | — | oui | Secret `rdv-secrets` (SOPS) |
| `DB_MAX_CONNS` | `10` | non | ConfigMap `rdv-config` |

## Secrets

| Secret | Contient | Géré par | Rotation |
|---|---|---|---|
| `rdv-pg-app` | user/mdp/URI de l'app PG | **CNPG** (généré automatiquement) | Voir [rotation-secrets](procedures/rotation-secrets.md) |
| `rdv-pg-superuser` | superuser PG | CNPG (`enableSuperuserAccess: false` en temps normal) | — |
| `rdv-secrets` | `SESSION_SECRET`, `SMTP_PASSWORD` | **SOPS** (age), `apps/rdv/overlays/prod/secrets.enc.yaml` | 1 fois/an ou si fuite |
| `rdv-s3-creds` | `ACCESS_KEY_ID`, `ACCESS_SECRET_KEY` | SOPS | 1 fois/an |
| `rdv-tls` | certificat TLS | **cert-manager** | Automatique (90 jours) |

> [!warning] La clé age qui déchiffre SOPS
> Elle se trouve dans Bitwarden (`sops-age-rdv`) et dans le Secret `sops-age` du namespace `argocd`. **Si on perd les deux, tous les secrets sont perdus.**

## Où se trouve quoi dans le repo GitOps
```
rdv-gitops/
├── apps/rdv/
│   ├── base/                 Deployment, Service, Ingress, NetworkPolicy, PDB
│   └── overlays/
│       ├── staging/
│       └── prod/             tags d'image, replicas, secrets.enc.yaml
├── apps/rdv-pg/              Cluster CNPG, ObjectStore, ScheduledBackup, PodMonitor
├── platform/                 cert-manager, monitoring, cnpg-operator, argocd
├── alerts/                   PrometheusRule (chaque alerte a un runbook_url)
└── docs/                     ← ce dossier
```
