# senior-claude

Des plugins [Claude Code](https://claude.com/claude-code) pour que Claude travaille comme un ingénieur senior. Ils sont **tirés de ma pratique** du développement et de l'exploitation : une application en production sur Kubernetes, avec GitOps (GitLab + ArgoCD), PostgreSQL via CloudNativePG, et Prometheus, Loki et Grafana pour l'observabilité.

Chaque plugin traite **un problème précis**, contient quelque chose qui s'exécute (skills, scripts, hooks), et s'installe seul.

> *English: Claude Code plugins that make Claude work like a senior engineer, drawn from my own development and operations practice (Kubernetes, GitOps, CloudNativePG, Prometheus/Loki/Grafana). Written in French; translations welcome.*

## Plugins

| Plugin | Problème traité | Contenu |
|---|---|---|
| [**ops-doc**](plugins/ops-doc/README.md) | Une doc d'exploitation qui existe, est utilisable à 3 h du matin et reste alignée sur ce qui tourne | 5 skills (init, import, check, review), un script de vérification sans dépendance, un hook qui demande aux agents de vérifier et relire la doc avant commit et push |
| [**kube-logs**](plugins/kube-logs/README.md) | Des logs exploitables sans rien gérer côté app : une ligne JSON sur stdout, et Alloy, Loki et Grafana font le reste | 5 skills (audit, setup, validate, query), un audit statique (code Node, Dockerfile, manifests, Alloy, Loki), un validateur des logs réels (stdin, kubectl, API Loki) utilisable en CI, une config pino éprouvée en prod |

## Installation

```
/plugin marketplace add BEIRDINH0S/senior-claude
/plugin install ops-doc@senior-claude
/plugin install kube-logs@senior-claude
```

On installe seulement les plugins qui nous intéressent. Chaque README de plugin décrit aussi une installation manuelle, sans le système de plugins.

## Organisation

```
.claude-plugin/marketplace.json   le catalogue
plugins/<nom>/                    un plugin autonome : manifeste, skills, hooks, tests, README
```

Les plugins ne dépendent pas les uns des autres.

## Contribuer

Les retours d'usage, corrections et nouvelles règles sont bienvenus : voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

[MIT](LICENSE)
