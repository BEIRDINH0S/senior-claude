---
name: grafana-dashboards
description: >
  Bonnes pratiques des dashboards Grafana pour une application sur Kubernetes (Prometheus, Loki) : un
  dashboard sert à diagnostiquer, pas à surveiller. Hiérarchie à trois niveaux avec drill-down, bandeau de
  santé toujours visible et détail en onglets (dynamic dashboards, schéma v2), RED pour les services et USE
  pour les ressources, choix des visualisations, requêtes PromQL correctes (rate, percentiles), boucle
  alerte → runbook → dashboard → logs, dashboards en GitOps avec le sidecar Grafana. Contient le standard,
  un exemple de référence et un linter de JSON utilisés par grafana-dashboards-design et
  grafana-dashboards-check. À utiliser dès qu'on crée, modifie, relit ou organise un dashboard Grafana,
  un panneau, une requête de panneau, ou qu'on se demande comment déployer des dashboards, même sans dire
  grafana-dashboards.
---

# grafana-dashboards

**Un dashboard sert à diagnostiquer, pas à surveiller.** Ce sont les alertes qui préviennent. Quand une alerte sonne, le runbook dit quoi regarder, et le dashboard doit montrer **en 5 secondes** où est le problème, puis permettre de descendre jusqu'à la cause et aux logs.

Laissé à lui-même, un modèle de langage produit le dashboard type « toutes les métriques disponibles » : pas de hiérarchie, pas d'unités, des compteurs sans `rate()`, des moyennes de latence, une série par pod, des camemberts, une source de données en dur, aucune description. Ce skill existe pour éviter ça.

## Ressources (dans le dossier de ce skill)

| Chemin | Quand le lire |
|---|---|
| `references/standard.md` | **Avant de produire ou de juger un dashboard.** Hiérarchie, bandeau et onglets, RED/USE, visualisations, requêtes, boucle avec les runbooks, variables, GitOps, règles du linter, sources |
| `references/gitops-sidecar.md` | Pour déployer : sidecar du chart Grafana, Kustomize `configMapGenerator`, ArgoCD `ServerSideApply`, provisioning du schéma v2 |
| `assets/exemple-rdv-overview.json` | Un dashboard de niveau 1 de référence au **schéma v2** (Grafana 13) : bandeau de santé, onglets API / Base / Logs, descriptions et liens vers les runbooks, lien de données vers Loki. Point de départ à adapter, sans en recopier les métriques à l'aveugle |
| `assets/screenshots/` | Captures de trois dashboards : celui généré par une IA, celui dont le bandeau est caché dans un onglet, et l'exemple de référence |
| `scripts/lint_dashboard.py` | Linter du JSON (schémas v1 et v2) : `python3 <ce dossier>/scripts/lint_dashboard.py <fichiers ou dossiers> [--runbooks docs/runbooks]`. Bibliothèque standard uniquement, code de sortie 1 en cas d'erreur |

Les autres skills `grafana-dashboards-*` y accèdent via `../grafana-dashboards/...`.

## Choisir le bon skill

| Demande | Skill |
|---|---|
| Créer un dashboard, ou refondre une collection de dashboards | **grafana-dashboards-design** |
| Vérifier ou relire des dashboards existants, ou les passer en CI | **grafana-dashboards-check** |

Pour une question de principe (« faut-il des onglets ? », « un dashboard par composant ? »), réponds à partir du standard en citant la section concernée.

## Règles qui valent pour tous les skills grafana-dashboards

- **Partir des runbooks et des alertes**, pas de la liste des métriques. Si le repo suit ops-doc (`docs/runbooks/`), chaque runbook doit avoir un panneau qui montre son symptôme, et chaque panneau qui peut virer au rouge doit renvoyer à son runbook.
- **Ne jamais inventer un nom de métrique.** Vérifie qu'elle existe dans le code de l'app (`prom-client`…), les PrometheusRule ou les exporters en place, et si possible dans Prometheus (`/api/v1/label/__name__/values`). Un panneau sur une métrique imaginaire affiche « No data » le jour de l'incident.
- **Le JSON passe par le linter** avant d'être proposé ou commité.
- **Schéma v2 sur un Grafana récent** (onglets, layouts dynamiques), en ressource Kubernetes. **L'`apiVersion` se vérifie sur l'instance** (`GET /apis/dashboard.grafana.app/`) ou dans un export, jamais de mémoire. L'exemple utilise `v2beta1`, accepté par Grafana 13.3.
- **Dashboards en code dans Git**, déployés par le sidecar. Jamais d'instruction du type « crée-le dans l'interface » comme résultat final.
