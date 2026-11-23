---
name: grafana-dashboards-check
description: >
  Vérifie et relit des dashboards Grafana (fichiers JSON, schémas v1 et v2) : un linter repère les erreurs
  objectives (compteurs sans rate, percentiles sans le, unités et descriptions manquantes, source de
  données en dur, série par pod, camemberts, bandeau de santé caché dans un onglet, seuil rouge sans
  runbook, liens de runbooks cassés), puis une relecture juge ce qu'un script ne voit pas : le test des
  5 secondes, la hiérarchie, la cohérence avec les alertes et les runbooks, les métriques qui existent
  vraiment. Rapport priorisé avec corrections, utilisable en CI. À utiliser pour « relis mon dashboard »,
  « ce dashboard est-il bon », « vérifie nos dashboards Grafana », « ajoute un lint des dashboards en CI »,
  ou après avoir généré un dashboard.
---

# grafana-dashboards-check

Le standard de référence est `../grafana-dashboards/references/standard.md` (à partir du dossier de ce skill).

## 1. Le linter

```bash
python3 <dossier de ce skill>/../grafana-dashboards/scripts/lint_dashboard.py <fichiers ou dossiers> [--runbooks docs/runbooks] [--gauge <métrique>]
```
- `--runbooks` vérifie les liens vers les runbooks et liste ceux qu'aucun dashboard ne cite.
- `--gauge` déclare une jauge dont le nom finit par `_total` ou `_count` (exemple : `cnpg_backends_total`). Sans ça, elle déclencherait un faux `RATE-MANQUANT`.
- Les règles sont décrites dans le standard, section 11. **Vérifie chaque constat** avant de le rapporter : le linter fonctionne par heuristique.

Les dashboards n'existent que dans l'interface Grafana ? Exporte-les (`GET /api/dashboards/uid/<uid>` ou l'API `/apis/dashboard.grafana.app/…`) avec l'accord de l'utilisateur, puis signale qu'ils devraient être dans Git.

## 2. La relecture : ce que le linter ne voit pas

| À juger | Question |
|---|---|
| **Le test des 5 secondes** | En ouvrant le dashboard pendant un incident, voit-on tout de suite si ça va et quel composant souffre, sans défiler ni changer d'onglet ? |
| **La hiérarchie** | Est-ce un niveau 1 (RED, symptômes) ou un niveau 2 (détail, USE) ? Mélange-t-il les deux ? Existe-t-il des liens pour descendre d'un niveau ? |
| **Alertes ↔ panneaux** | Chaque alerte de l'app a-t-elle un panneau avec la même requête et le même seuil ? Un seuil de panneau en désaccord avec l'alerte trompe : vert sur le dashboard, rouge dans la notification |
| **Runbooks ↔ panneaux** | Les descriptions renvoient-elles au bon runbook ? Les runbooks renvoient-ils au panneau ? |
| **Les métriques existent-elles ?** | Croise chaque nom de métrique avec le code, les exporters ou Prometheus. Une faute de frappe affiche « No data » en silence |
| **Les requêtes répondent-elles à la question du titre ?** | « Taux d'erreurs » qui compte des erreurs absolues, « Disponibilité » qui ignore les 5xx, agrégation qui mélange deux apps |
| **Les seuils et couleurs** | Le rouge signifie-t-il « agir » et correspond-il au SLO ou à l'alerte ? Pas de couleurs décoratives |
| **Les doublons** | Un panneau refait-il ce qu'un dashboard communautaire fait mieux ? |
| **Le déploiement** | Le dashboard est-il dans Git, avec un UID fixe, déployé par le sidecar ? |

## 3. Le rapport

````markdown
# Revue des dashboards : <périmètre> (<date>)

**Résumé** : 3 à 5 lignes. Ces dashboards permettent-ils de diagnostiquer un incident ? Les 2 ou 3 priorités.

## Bloquant
Ce qui affiche une valeur fausse ou cache un problème : compteur sans rate, percentile sans le,
seuil en désaccord avec l'alerte, métrique inexistante, bandeau caché, lien de runbook cassé.
### <dashboard> › <panneau> : constat
**Pourquoi** : une phrase, en citant la section du standard.
**Correction** : la requête ou le fragment JSON corrigé.

## Important
Diagnostic ralenti : pas de description ni de runbook, pas d'unité, une série par pod au niveau 1, pas de lien vers les logs, source de données en dur, trop de panneaux.

## Suggestions

## Ce qui est déjà bien
````

Ne modifie pas les dashboards sans qu'on te le demande. Si l'utilisateur dit d'appliquer, corrige le JSON dans le repo, relance le linter, et rappelle que le déploiement passe par Git (sidecar).

## En CI

```yaml
dashboards-lint:
  image: python:3.12-slim
  script:
    - python3 tools/lint_dashboard.py apps/observability/dashboards --runbooks docs/runbooks
  rules:
    - changes: ["apps/observability/dashboards/**/*.json", "docs/runbooks/**/*"]
```
