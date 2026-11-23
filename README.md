# kube-ops-plugins

Des plugins [Claude Code](https://claude.com/claude-code) **tirés de ma pratique** : j'exploite une application en production sur Kubernetes, avec GitOps (GitLab + ArgoCD), PostgreSQL via CloudNativePG, et Prometheus, Loki et Grafana pour l'observabilité.

Chaque plugin traite **un problème précis**, contient quelque chose qui s'exécute (skills, scripts, hooks), et s'installe seul.

> *English: Claude Code plugins drawn from running a Kubernetes app in production (GitOps, CloudNativePG, Prometheus/Loki/Grafana). Written in French; translations welcome.*

## Plugins

| Plugin | Problème traité | Contenu |
|---|---|---|
| [**ops-doc**](plugins/ops-doc/README.md) | Une doc d'exploitation qui existe, est utilisable à 3 h du matin et reste alignée sur ce qui tourne | 5 skills (init, import, check, review), un script de vérification sans dépendance, un hook qui demande aux agents de vérifier et relire la doc avant commit et push |

## Installation

```
/plugin marketplace add BEIRDINH0S/kube-ops-plugins
/plugin install ops-doc@kube-ops-plugins
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
