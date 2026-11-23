---
name: ops-doc-init
description: >
  Crée de zéro la documentation d'exploitation d'une application Kubernetes dans docs/, en lisant le repo :
  manifests, Kustomize/Helm, cluster CloudNativePG, PrometheusRule, Application ArgoCD, NetworkPolicy, CI
  GitLab/GitHub, Dockerfile. Produit la fiche service, l'architecture avec des schémas Mermaid, l'inventaire
  de config, le dimensionnement, le plan de reprise, un runbook par alerte, la checklist de mise en prod,
  avec les vrais noms de ressources, et marque TODO ce qui ne se devine pas. À utiliser quand une app n'a pas
  de doc ops et qu'on demande de « documenter l'app pour l'exploitation », « faire les runbooks », « préparer
  l'astreinte », « écrire le dossier d'exploitation », « initialiser la doc ops », même sans dire ops-doc.
---

# ops-doc-init : générer la doc ops depuis le repo

Le but : un `docs/` conforme au standard, **rempli avec ce que le repo dit vraiment**, et une liste de questions précises pour tout ce que le repo ne peut pas dire.

Avant de commencer, lis `../ops-doc/references/standard.md` (à partir du dossier de ce skill). Pour le niveau de détail attendu, parcours `../ops-doc/references/exemple-rdv/` : au moins `README.md` et un runbook.

## 1. Situer le travail

- **Où vit la doc ?** Par défaut, `docs/` à la racine du repo qui décrit le déploiement : le repo GitOps s'il est séparé du code de l'app. Si les manifests et le code sont dans deux repos différents et que tu n'as accès qu'à un des deux, dis-le et demande le chemin de l'autre.
- **Un `docs/` existe déjà ?** S'il contient de la doc ops non standard, c'est le travail d'**ops-doc-import**. S'il contient autre chose (doc de dev, ADR existants), ne l'écrase pas : ajoute les fichiers du standard à côté et signale les recoupements.

## 2. Inventorier le repo

Lis le repo plutôt que de le deviner. Les informations à collecter, et où les trouver :

| Info | Où chercher |
|---|---|
| Composants (workloads) | `kind: Deployment|StatefulSet|CronJob|Job|DaemonSet` : nom, image, réplicas, probes, ressources, labels `app.kubernetes.io/*` |
| Environnements | overlays Kustomize, `values-*.yaml` Helm, Applications ArgoCD |
| URLs | `kind: Ingress|IngressRoute|HTTPRoute` : hosts, chemins, TLS (cert-manager `Certificate`, annotations `cert-manager.io/*`) |
| Base de données | `kind: Cluster` (`postgresql.cnpg.io`) : instances, version d'image, `storage`, `walStorage`, `postgresql.parameters`, sauvegardes (`plugins` barman-cloud + `ObjectStore`, ou l'ancien `backup.barmanObjectStore`), `ScheduledBackup` (planning, rétention), `Pooler` |
| Alertes | `kind: PrometheusRule` : nom, expression, `for`, sévérité, `runbook_url` |
| Observabilité | `ServiceMonitor`, `PodMonitor`, dashboards (ConfigMaps Grafana), Loki |
| Réseau | `NetworkPolicy` (default deny ? flux autorisés), `Service` |
| Résilience | `PodDisruptionBudget`, `HorizontalPodAutoscaler`, anti-affinité, `terminationGracePeriodSeconds` |
| Sécurité | `securityContext`, labels Pod Security sur le Namespace |
| Config et secrets | `env`, `envFrom`, `ConfigMap`, références à des Secrets ; outil de gestion des secrets (fichiers `*.enc.yaml` / `.sops.yaml` → SOPS, `SealedSecret`, `ExternalSecret`) |
| GitOps | `kind: Application|ApplicationSet` : repo source, chemin, `syncPolicy` (auto, prune, selfHeal), hooks (`argocd.argoproj.io/hook`), sync waves |
| CI | `.gitlab-ci.yml` / `.github/workflows/` : étapes, build d'image, stratégie de tags, scan |
| Langage de l'app | `Dockerfile`, fichiers de dépendances |

Si `kubectl` est configuré, tu peux compléter **en lecture seule** (`get`, `describe`) : vraies tailles de PVC, état du cluster CNPG avec `kubectl cnpg status`, alertes chargées. Demande avant, puisque le contexte courant peut être la prod, et ne lis jamais le contenu d'un Secret.

## 3. Générer les fichiers

Copie `../ops-doc/assets/templates/` dans `docs/`, puis remplis chaque fichier :

- **README.md** : composants, liens, dépendances et accès à partir de l'inventaire. Responsable, criticité, SLO, astreinte et RPO/RTO restent en `TODO(ops-doc)` sauf si l'utilisateur les a donnés : ce sont des décisions, pas des faits du repo.
- **architecture.md** : les schémas Mermaid dessinent les **vrais** composants et flux. Le tableau des flux réseau reflète les NetworkPolicies. S'il n'y en a pas, écris-le, c'est un risque à mettre dans la section Risques. La section Risques liste ce que l'inventaire révèle : une seule instance de base, pas de PDB, un secret en clair, pas de sauvegarde, etc.
- **config.md** : **toutes** les variables d'env et **tous** les Secrets référencés, avec l'endroit où chacun est défini. Ne lis et n'écris aucune valeur de secret.
- **dimensionnement.md** : reporte les requests/limits **actuelles** dans les colonnes requests et limits, et laisse les colonnes « observé » en `TODO(ops-doc)` avec les requêtes PromQL adaptées au namespace. Une request n'est pas une mesure. Laisse aussi la date de revue en `AAAA-MM-JJ` : aucune revue n'a encore eu lieu.
- **reprise.md** : les scénarios découlent de l'archi (failover CNPG si au moins 2 instances, sinon perte de service). La reconstruction suit l'ordre réel du bootstrap GitOps tel qu'on le lit dans le repo. Les durées et le RTO mesuré restent en `TODO(ops-doc)`, avec un renvoi : « à mesurer lors d'un game day ».
- **runbooks/** : **un runbook par alerte définie dans le repo**, nommé exactement comme l'alerte. L'en-tête reprend l'expression et le fichier. Le diagnostic utilise les vrais noms (namespace, labels, cluster CNPG). Pour la remédiation, propose les causes classiques de ce type d'alerte, et marque `TODO(ops-doc)` ce qui dépend du métier.
  - S'il n'y a **aucune alerte**, ne crée pas de runbooks fantômes. Propose dans le rapport final un jeu minimal d'alertes : app down, taux de 5xx, sauvegarde en échec ou trop ancienne, archivage WAL en échec, volume qui se remplit (`predict_linear`), certificat qui expire, Watchdog. Propose de les écrire avec leur runbook si l'utilisateur le souhaite.
  - Si des alertes n'ont pas de `runbook_url`, propose le patch des PrometheusRule (URL vers `docs/runbooks/<Alerte>.md` sur la branche principale).
- **procedures/** : au minimum `deploiement-rollback.md` (déduit de la CI et d'ArgoCD) et, s'il y a une base CNPG, `restauration-pitr.md` (cluster de restauration avec `bootstrap.recovery` et un **`serverName` d'archivage différent**). Chaque procédure a ses sections Vérification et Retour arrière.
- **checklist-production.md** : coche uniquement ce que tu as **constaté** dans le repo, et ajoute la source entre parenthèses si ce n'est pas évident. Laisse la date de revue en `AAAA-MM-JJ` : c'est l'utilisateur qui fera la revue.
- **adr/**, **postmortems/** : seulement les modèles. N'écris pas d'ADR dont tu ne connais pas les raisons : liste dans le rapport les décisions qui mériteraient un ADR (« pourquoi CNPG », « pourquoi SOPS »…), pour que l'utilisateur en donne le pourquoi.

## 4. Vérifier

```bash
python3 <dossier de ce skill>/../ops-doc/scripts/check_docs.py <repo>
```
Corrige toutes les **erreurs** sauf celles qui viennent du repo lui-même : une alerte sans `runbook_url` se corrige dans la PrometheusRule, pas dans la doc. Les `TODO` sont attendus à ce stade.

## 5. Rendre la main

Termine par un compte rendu court :
1. Les fichiers créés, en une ligne chacun.
2. **Les questions** : tous les `TODO(ops-doc)` regroupés par thème et formulés comme des questions auxquelles l'utilisateur peut répondre d'un mot. Exemple : « Criticité : haute, moyenne ou basse ? Que se passe-t-il pour les utilisateurs si l'app tombe 1 h ? »
3. **Ce que l'inventaire a révélé** : les risques trouvés (pas de sauvegarde, une seule instance, pas de NetworkPolicy, secret en clair…). Ça vaut souvent plus que la doc elle-même.
4. La suite : répondre aux questions pour que tu remplisses les `TODO`, puis **ops-doc-review**.

Quand l'utilisateur répond, remplace les `TODO` correspondants et relance le script.
