# Le standard grafana-dashboards

> **Un dashboard sert à diagnostiquer, pas à surveiller.** Ce sont les alertes qui préviennent. Quand une alerte sonne, le runbook dit quoi regarder, et le dashboard doit montrer **en 5 secondes** où est le problème, puis permettre de descendre jusqu'à la cause et aux logs.

## Sommaire
1. Ce qu'un dashboard n'est pas
2. La hiérarchie : trois niveaux et des liens pour descendre
3. Le dashboard de vue d'ensemble : bandeau de santé + onglets
4. Les méthodes : RED pour les services, USE pour les ressources
5. Choisir la visualisation
6. Les requêtes
7. La boucle alerte → runbook → dashboard → logs
8. Variables, unités, couleurs, rafraîchissement
9. Les dashboards de composants : réutiliser plutôt que refaire
10. Dashboards en code (GitOps)
11. Règles vérifiées par le linter
12. Sources

---

## 1. Ce qu'un dashboard n'est pas

- **Un écran qu'on regarde en continu.** Personne ne le fait, et c'est le rôle des alertes. Une condition qui mérite qu'on agisse est une alerte (PrometheusRule), pas un panneau qu'on espère voir rougir.
- **Le catalogue de toutes les métriques disponibles.** Une métrique n'a sa place que si elle répond à une question de diagnostic. Ajouter un panneau « parce que la métrique existe » est l'erreur numéro 1 des dashboards générés automatiquement.
- **Une copie par environnement ou par app.** On utilise des variables (section 8).

## 2. La hiérarchie : trois niveaux et des liens pour descendre

C'est la pratique « maturité moyenne et haute » de la documentation Grafana : des dashboards **hiérarchiques avec drill-down**, plutôt qu'une collection plate.

| Niveau | Question | Contenu | Combien |
|---|---|---|---|
| **1. Vue d'ensemble du service** | « Les utilisateurs souffrent-ils ? Où ? » | bandeau de santé, puis RED de chaque composant dans l'ordre du flux des requêtes | **un par application** |
| **2. Composant** | « Pourquoi ce composant va mal ? » | RED détaillé (par route, par code de statut) ou USE (CPU, mémoire, disque, connexions, saturation) | un par composant, souvent un dashboard communautaire (section 9) |
| **3. Exploration** | « Que s'est-il passé exactement ? » | Explore / Logs Drilldown sur Loki, à la même période, filtré sur le composant | pas un dashboard : un lien |

Chaque niveau **pointe vers le suivant** : lien de dashboard du niveau 1 vers les niveaux 2, lien de données d'un panneau vers Explore. On ne cherche jamais un dashboard dans une liste pendant un incident.

**Une page par composant, sans niveau 1 au-dessus, est une erreur fréquente** : pour savoir si « l'app » va bien, il faut alors ouvrir cinq pages.

## 3. Le dashboard de vue d'ensemble : bandeau de santé + onglets

Grafana (12+, « dynamic dashboards ») propose des layouts **rows**, **tabs** et **auto grid**, imbricables (des onglets dans une row, par exemple). Le schéma recommandé :

```
┌─────────────────────────────────────────────────────────────┐
│ $datasource  $namespace                         [liens ▾]   │
├─────────────────────────────────────────────────────────────┤
│ ROW « Santé » (toujours visible, jamais dans un onglet)     │
│ [Disponibilité] [Taux 5xx] [Latence p95] [Base] [Backups]   │  ← stats + seuils
├─────────────────────────────────────────────────────────────┤
│ ROW « Détail »                                              │
│  ┌ Onglet API ┬ Onglet Base ┬ Onglet Ingress ┬ Onglet Logs ┐│
│  │ RED de l'API : débit | erreurs | latence p50/p95/p99    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

- **Le bandeau de santé est hors des onglets.** Un onglet fermé cache ce qu'il contient : si l'indicateur de la base passe au rouge pendant qu'on regarde l'onglet API, on ne le voit pas. Le bandeau résume l'état de **chaque** composant, par une valeur et une couleur.
- **Le bandeau tient sur une ligne, sans défiler** : 4 à 8 panneaux « stat ». Si on dépasse, c'est que le bandeau contient du détail.
- **Les onglets regroupent le détail par composant**, dans l'ordre du flux des requêtes.
- **Faire défiler dans un onglet de détail est acceptable** : on y vient pour creuser. La règle « pas de défilement » vaut pour la réponse à « est-ce que ça va ? ».
- Les règles d'affichage conditionnel (afficher ou masquer une row selon une variable) existent, mais elles demandent un layout auto grid. À n'utiliser que si on en a besoin.

## 4. Les méthodes : RED pour les services, USE pour les ressources

| Méthode | Pour | Signaux |
|---|---|---|
| **RED** | un service qui reçoit des requêtes (API, ingress) | **R**ate (requêtes/s), **E**rrors (taux d'erreurs), **D**uration (latence, en percentiles) |
| **USE** | une ressource (CPU, mémoire, disque, pool de connexions, file) | **U**tilisation, **S**aturation (file d'attente, throttling), **E**rreurs |
| **4 signaux d'or** (SRE Google) | synthèse | latence, trafic, erreurs, saturation |

La documentation Grafana recommande d'**alerter sur les symptômes** (RED, ce que subit l'utilisateur) plutôt que sur les causes (USE). Le niveau 1 est donc du RED, et l'USE vit au niveau 2, pour expliquer.

Mise en page RED d'un composant : **débit et erreurs à gauche, latence à droite**, une ligne par composant dans l'ordre du flux.

## 5. Choisir la visualisation

| Question | Visualisation | À éviter |
|---|---|---|
| État actuel (« ça va ? ») | **Stat** avec seuils de couleur, éventuellement avec sparkline | jauge décorative |
| Évolution d'un débit ou d'un taux | **Time series** | barres empilées pour des taux |
| Latence | **Time series de percentiles** (p50, p95, p99), ou **heatmap** de l'histogramme | une **moyenne** : elle cache la queue de distribution |
| Classement (top routes, top erreurs) | **Table** ou **bar gauge** triée | camembert |
| Événements (déploiements, incidents) | **Annotations** sur les time series | un panneau à part |
| Logs | **Logs** limité à l'app, ou mieux, un lien vers Explore | un panneau logs non filtré au niveau 1 |
| Proportions | **Bar gauge** | **camembert** : l'œil compare mal les angles, et il devient illisible au-delà de 3 ou 4 parts |

## 6. Les requêtes

- **Un compteur (`*_total`, `*_count`, `*_sum`, `*_bucket`) s'utilise toujours avec `rate()` ou `increase()`.** Sa valeur brute monte à l'infini et repart à zéro à chaque redémarrage : la tracer telle quelle n'a pas de sens.
- **`rate(x[$__rate_interval])`** plutôt qu'une fenêtre fixe : Grafana ajuste la fenêtre à l'intervalle de scraping et au zoom, et on évite les trous ou le lissage excessif.
- **Percentiles** : `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[$__rate_interval])))`. Sans le **`le`** dans le `by`, le résultat est faux.
- **Une moyenne de latence** (`_sum / _count`) peut compléter les percentiles, **jamais les remplacer**.
- **L'agrégation au bon niveau** : au niveau 1, `sum by (route)` ou `sum` tout court. Une série par pod (`by (pod)`, `{{pod}}` en légende) change à chaque déploiement et rend le panneau illisible. Elle a sa place au niveau 2.
- **Pas de namespace ni d'app en dur** dans les requêtes : `namespace="$namespace"`.
- Une requête lourde, utilisée par plusieurs panneaux ou plusieurs dashboards, devient une **recording rule** Prometheus.

## 7. La boucle alerte → runbook → dashboard → logs

Les dashboards et les runbooks se construisent ensemble. Le runbook dit **quoi regarder**, le dashboard **le montre**.

```
Alerte ──runbook_url──────────▶ Runbook (docs/runbooks/<Alerte>.md)
  │ __dashboardUid__ / __panelId__     │ Diagnostic : « panneau X du dashboard Y » (lien)
  ▼                                    ▼
Panneau ◀──────────────────────────────┘
  │ description : quoi, normal, si anormal → lien runbook
  │ lien de données ──▶ Explore Loki {namespace, app}, même période
  ▼
Logs
```

- **Chaque alerte a un panneau qui montre sa condition.** C'est la même requête, avec le seuil de l'alerte tracé (seuils en mode ligne, ou couleur du stat). Quand l'alerte sonne, on voit immédiatement depuis quand et à quel point.
- **Les alertes pointent vers ce panneau** : annotations `__dashboardUid__` et `__panelId__` pour les alertes gérées par Grafana, ou un lien construit dans une annotation `dashboard_url` pour les PrometheusRule. Le lien arrive alors dans la notification.
- **Chaque panneau qui peut virer au rouge** (seuils) renvoie vers le runbook correspondant, dans sa description ou dans un lien de panneau.
- **Les runbooks pointent vers les panneaux** dans leur section Diagnostic (lien avec `viewPanel`).
- **Les panneaux d'erreurs ont un lien de données vers Loki**, avec les mêmes labels et la même période (`${__from}`, `${__to}`) : un clic sur le pic mène aux logs du pic.
- **Description d'un panneau**, toujours sur le même modèle :
  > **Montre** : le taux de réponses 5xx de l'API. **Normal** : < 0,5 %. **Si anormal** : [runbook RdvHighErrorRate](…), puis logs d'erreur via le lien du panneau.

Un dashboard sans runbook, c'est un dashboard dont personne ne sait quoi faire quand il rougit. Un runbook sans dashboard, c'est un diagnostic à l'aveugle.

## 8. Variables, unités, couleurs, rafraîchissement

- **Variables** : au minimum `datasource` (type datasource) et `namespace`, avec éventuellement `app`. La source de données se référence par **`${datasource}`**, pas par un UID en dur : l'UID change d'une instance Grafana à l'autre, et le dashboard casse en staging ou après une réinstallation.
- **UID de dashboard fixe et lisible** (`rdv-overview`) : les liens des runbooks et des alertes en dépendent. Sans UID fixe, chaque réimport en génère un nouveau.
- **Unités toujours renseignées** : `reqps`, `percentunit`, `s`/`ms`, `bytes`, `short`. Un « 0,02 » sans unité ne dit pas s'il s'agit de 2 % ou de 20 ms.
- **Couleurs** : le rouge veut dire « il faut agir », et seulement ça. Les seuils correspondent aux seuils des alertes ou des SLO, pas à des valeurs au hasard. Pas d'arc-en-ciel décoratif.
- **Rafraîchissement** : 30 s à 1 min suffisent. 5 à 10 s chargent Prometheus et Loki pour rien.
- **Titres de panneaux** : la question à laquelle le panneau répond, ou la grandeur avec son unité (« Taux de 5xx », « Latence p95 »), sans jargon de requête.

## 9. Les dashboards de composants : réutiliser plutôt que refaire

Les composants standards ont des dashboards maintenus par leur communauté, meilleurs que ce qu'on referait :

| Composant | Dashboard |
|---|---|
| Cluster, nœuds, pods (USE) | dashboards du **kubernetes-mixin**, fournis par kube-prometheus-stack |
| PostgreSQL / CloudNativePG | dashboard officiel CloudNativePG (repo `cloudnative-pg/grafana-dashboards`) |
| Loki, Alloy | dashboards des mixins Loki et Alloy |
| Ingress NGINX, Traefik, cert-manager | dashboards officiels des projets |

On les **versionne dans le repo GitOps** (fichier JSON à une version donnée) plutôt que de les importer à la main : ils survivent ainsi à une réinstallation. Le dashboard de niveau 1, lui, est le seul que personne ne peut faire à votre place : c'est le sien qui compte.

## 10. Dashboards en code (GitOps)

Un dashboard modifié à la main dans l'interface dérive : personne ne sait qui a changé quoi, et une réinstallation l'efface. Les dashboards vivent dans Git et sont déployés comme le reste. Méthode retenue, la plus simple : le **sidecar du chart Grafana** (voir `gitops-sidecar.md`).

- Un fichier `.json` par dashboard dans le repo, une ConfigMap par dashboard générée par Kustomize, avec le label que le sidecar surveille.
- **ArgoCD en `ServerSideApply=true`** : sinon, un gros dashboard dépasse la limite de 256 Ko de l'annotation `last-applied-configuration`. C'est la « limite des ConfigMaps » qu'on rencontre en pratique ; la vraie limite d'une ConfigMap est 1 Mio.
- `allowUiUpdates: false` : une modification se fait dans Git. Pour prototyper, on modifie dans l'interface, on exporte le JSON et on le commite.
- **Schéma v2** (onglets, layouts dynamiques) : un dashboard v2 provisionné par fichier doit être au format ressource Kubernetes (`apiVersion: dashboard.grafana.app/v2…`, `kind: Dashboard`, `metadata`, `spec`). La doc Grafana le marque encore comme preview selon les versions. **Vérifiez l'`apiVersion` exacte en exportant un dashboard depuis votre Grafana** plutôt que de l'écrire de mémoire.

## 11. Règles vérifiées par le linter

`scripts/lint_dashboard.py` : schéma v1 (`panels[]`) et schéma v2 (`elements` + `layout`, brut ou en ressource Kubernetes). Bibliothèque standard uniquement.

| Code | Niveau | Règle |
|---|---|---|
| `TITRE-MANQUANT` | erreur | panneau sans titre |
| `RATE-MANQUANT` | erreur | un compteur (`_total`, `_count`, `_sum`, `_bucket`) sans `rate`/`irate`/`increase` |
| `QUANTILE-SANS-LE` | erreur | `histogram_quantile` sans `le` dans l'agrégation |
| `RUNBOOK-INTROUVABLE` | erreur | lien vers `runbooks/X.md` alors que le fichier n'existe pas (avec `--runbooks`) |
| `DS-EN-DUR` | avertissement | source de données référencée par UID en dur au lieu de `${datasource}` |
| `UID-MANQUANT` | avertissement | dashboard sans UID fixe |
| `UNITE-MANQUANTE` | avertissement | time series, stat, gauge ou bar gauge sans unité |
| `DESCRIPTION-MANQUANTE` | avertissement | panneau sans description |
| `LATENCE-MOYENNE` | avertissement | latence calculée en `_sum / _count` sans aucun percentile dans le dashboard |
| `CAMEMBERT` | avertissement | panneau piechart |
| `SERIE-PAR-POD` | avertissement | légende ou agrégation par `pod`/`instance`/`container` (lisible au niveau 2 seulement) |
| `NAMESPACE-EN-DUR` | avertissement | `namespace="…"` littéral dans une requête |
| `SEUIL-SANS-RUNBOOK` | avertissement | panneau avec un seuil rouge mais sans lien ni mention de runbook |
| `BANDEAU-CACHE` | avertissement | layout v2 dont le premier niveau est en onglets : le bandeau de santé n'est jamais visible en entier |
| `TROP-DE-PANNEAUX` | avertissement | plus de `--max-panels` (12 par défaut) panneaux visibles sans repli |
| `REFRESH-COURT` | avertissement | rafraîchissement automatique inférieur à 30 s |
| `RATE-INTERVAL` | info | `rate()` avec une fenêtre fixe plutôt que `$__rate_interval` |
| `PAS-DE-VARIABLE` | info | aucune variable de dashboard |
| `PAS-DE-LIEN-LOGS` | info | aucun lien vers Loki/Explore dans le dashboard |
| `RUNBOOK-NON-REFERENCE` | info | un runbook de `--runbooks` qu'aucun dashboard ne mentionne |

## 12. Sources

- Grafana, *Dashboard best practices* (méthodes, maturité, hiérarchie) : https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/
- Grafana, *The RED Method* : https://grafana.com/blog/the-red-method-how-to-instrument-your-services/
- Grafana, *Dynamic dashboards* (rows, tabs, auto grid) : https://grafana.com/blog/dynamic-dashboards-grafana-12/ et https://grafana.com/whats-new/2026-04-08-dynamic-dashboards-is-now-generally-available/
- Grafana, *Schema v2 : layout* : https://grafana.com/docs/grafana/latest/observability-as-code/schema-v2/
- Grafana, *Provisioning* : https://grafana.com/docs/grafana/latest/administration/provisioning/
- Grafana, *Alert rules* (runbook, lien dashboard/panneau) : https://grafana.com/docs/grafana/latest/alerting/alerting-rules/create-grafana-managed-rule/
- Grafana, *Observability as code* : https://grafana.com/docs/grafana/latest/observability-as-code/get-started/
- Google SRE book, *Monitoring Distributed Systems* (4 signaux d'or) : https://sre.google/sre-book/monitoring-distributed-systems/
- Brendan Gregg, *The USE Method* : https://www.brendangregg.com/usemethod.html
