---
name: grafana-dashboards-design
description: >
  Conçoit les dashboards Grafana d'une application sur Kubernetes à partir de ce qui compte pour le
  diagnostic : son architecture, ses alertes, ses runbooks et ses métriques réelles. Produit la hiérarchie
  (vue d'ensemble, composants, lien vers les logs), le JSON au schéma v2 avec bandeau de santé et onglets,
  des descriptions de panneaux qui renvoient aux runbooks, des liens de données vers Loki, les fichiers
  GitOps du sidecar, et relie en retour alertes et runbooks aux panneaux. À utiliser pour « fais-moi un
  dashboard pour mon app », « refais nos dashboards Grafana », « il nous faut une vue d'ensemble », « ajoute
  un panneau pour cette alerte », « organise nos dashboards ».
---

# grafana-dashboards-design

Lis d'abord `../grafana-dashboards/references/standard.md` (à partir du dossier de ce skill), puis ouvre `../grafana-dashboards/assets/exemple-rdv-overview.json` pour voir le résultat attendu.

## 1. Inventorier ce qui compte (pas toutes les métriques)

| Source | Ce qu'on en tire |
|---|---|
| `docs/README.md` et `docs/architecture.md` (ops-doc) | les composants et l'**ordre du flux** des requêtes, donc l'ordre des onglets et des lignes RED |
| `docs/runbooks/*.md` et les `PrometheusRule` | **un panneau par alerte**, avec la même requête et le même seuil, et le lien vers le runbook |
| SLO de la fiche service | les seuils du bandeau de santé |
| le code de l'app (`prom-client`, middleware HTTP) | les métriques applicatives réelles : noms, labels (`route`, `status_code`) |
| exporters en place (CNPG, kube-state-metrics, kubelet, ingress) | les métriques des composants |
| Prometheus, si accessible (`/api/v1/label/__name__/values`, `/api/v1/series`) | **la confirmation** que chaque métrique existe avec ces labels |
| dashboards existants | ce qui sert déjà, ce qui fait doublon, ce qui est à remplacer |

Il n'y a pas de métrique HTTP applicative (pas d'histogramme de durée, pas de compteur par statut) ? Dis-le en premier : le niveau 1 en dépend, et la bonne correction est d'**instrumenter l'app** (`prom-client` en Node), pas de calculer ces valeurs à partir des logs.

## 2. Proposer le plan avant le JSON

Montre à l'utilisateur, en quelques lignes :
- l'arbre des dashboards : le niveau 1 (le sien) et les niveaux 2, avec les dashboards communautaires à réutiliser (CNPG, kubernetes-mixin…) ;
- le **bandeau de santé** : 4 à 8 indicateurs, un par composant ou par SLO, avec le seuil et le runbook de chacun ;
- les **onglets** et leur contenu (RED par composant, dans l'ordre du flux) ;
- les **trous** : runbooks sans métrique pour les montrer, métriques manquantes, alertes à créer.

Attends son accord : ce plan, c'est le choix de ce qui compte, et c'est le sien.

## 3. Écrire le JSON

En partant de l'exemple :
- **ressource Kubernetes au schéma v2**, avec l'`apiVersion` vérifiée sur l'instance ou dans un export ; `metadata.name` = UID fixe et lisible (`<app>-overview`) ;
- variables `datasource` (Prometheus), `loki`, `namespace` ; toutes les requêtes en `${datasource}` et `namespace="$namespace"` ;
- layout : une row « Santé » (auto grid, panneaux stat), puis une row « Détail » qui contient les onglets ;
- requêtes : `rate(…[$__rate_interval])` sur les compteurs, `histogram_quantile(q, sum by (le) (…))` pour les percentiles, agrégation sans `pod` au niveau 1 ;
- chaque panneau a une **unité**, une **description** au format « **Montre** / **Normal** / **Si anormal** → [runbook](…) », et si c'est un panneau d'erreurs, un **lien de données** vers Explore Loki avec `${__from}` et `${__to}` ;
- dashboard : liens vers les dashboards de niveau 2 (avec `var-namespace=${namespace}&${__url_time_range}`) et vers le dossier des runbooks ;
- rafraîchissement automatique à 1 min.

Pour ajouter un panneau à un dashboard existant, respecte son schéma (v1 ou v2) : ne convertis pas sans le dire.

## 4. Fermer la boucle avec les runbooks et les alertes

Le travail n'est pas fini tant que la boucle n'est pas fermée (standard, section 7) :
- **runbooks** : dans la section Diagnostic de chaque runbook concerné, un lien vers le panneau (`/d/<uid>?viewPanel=<id>`, ou `viewPanel=panel-<id>` selon la version : vérifie le format dans l'URL que produit Grafana) ;
- **alertes** : une annotation qui pointe vers le panneau (`__dashboardUid__` / `__panelId__` pour les alertes gérées par Grafana, une annotation `dashboard_url` pour les PrometheusRule) ;
- **fiche service** (`docs/README.md`) : le lien du dashboard dans la section Liens.

## 5. Livrer en GitOps

Suis `../grafana-dashboards/references/gitops-sidecar.md` : fichier `.json` dans le repo, entrée `configMapGenerator` avec le label du sidecar et l'annotation de dossier, `ServerSideApply=true` sur l'Application ArgoCD. Versionne aussi les dashboards communautaires retenus.

## 6. Vérifier

```bash
python3 <dossier de ce skill>/../grafana-dashboards/scripts/lint_dashboard.py <dossier des dashboards> --runbooks docs/runbooks
```
- Aucune erreur, et chaque avertissement corrigé ou justifié.
- `RUNBOOK-NON-REFERENCE` : un runbook dont le symptôme n'a aucun panneau. Ajoute le panneau, ou explique pourquoi c'est impossible.
- Si une instance Grafana est accessible, importe le dashboard pour vérifier qu'il s'affiche et qu'aucun panneau n'est vide : `POST /apis/dashboard.grafana.app/<version>/namespaces/default/dashboards`. Ne l'importe jamais en prod sans accord : en prod, le déploiement passe par Git.

## Rendre la main

Résume : l'arbre des dashboards, ce que montre le bandeau de santé, les liens ajoutés dans les runbooks et les alertes, les fichiers créés, le résultat du linter, et les trous restants (métriques à instrumenter, alertes à créer).
