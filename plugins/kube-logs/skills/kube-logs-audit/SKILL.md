---
name: kube-logs-audit
description: >
  Audite le logging d'une application déployée sur Kubernetes : écrit-elle bien du JSON sur stdout, sans
  fichiers de logs ni PVC dédié, avec des niveaux en texte, le masquage des secrets, des stack traces sur
  une seule ligne, un Dockerfile qui lance Node directement ? Côté plateforme : labels Loki à forte
  cardinalité dans Alloy, rétention Loki désactivée, dashboards qui recalculent des métriques depuis les
  logs. Lance un script, vérifie ses constats, puis rend un rapport priorisé avec les corrections. À
  utiliser pour « audite mes logs », « mes logs sont illisibles dans Grafana », « on stocke les logs dans un
  volume, c'est bien ? », « review du logging », ou avant de migrer une app vers la stack Loki.
---

# kube-logs-audit

Le standard de référence est `../kube-logs/references/standard.md` (à partir du dossier de ce skill). Lis-le avant de juger.

## 1. La passe automatique

```bash
python3 <dossier de ce skill>/../kube-logs/scripts/audit_logs.py <repo>
```
Les codes et leur signification sont dans le standard, section 9. Le script fonctionne par heuristique : **vérifie chaque constat** en lisant le code concerné avant de le rapporter. Par exemple, un `LOG-SECRET` peut mentionner `token` sans en loguer la valeur, et un `console.log` peut se trouver dans un outil CLI légitime.

## 2. La passe dynamique : les logs réels

Le code ne dit pas tout : une lib qui écrit sur stdout, le runtime qui imprime une exception, `npm` qui ajoute ses lignes. Si l'app tourne quelque part (local, staging, prod) ou si Loki est accessible, valide un échantillon réel avec le skill **kube-logs-validate** et intègre ses résultats au rapport. Sinon, dis que l'audit est seulement statique.

## 3. La passe de lecture : ce que les scripts ne voient pas

| À vérifier | Comment |
|---|---|
| **Le logger est-il utilisé partout ?** | cherche les endroits où l'app logue autrement : une seconde lib, `process.stdout.write`, des logs de frameworks non branchés sur le logger (ORM, client HTTP) |
| **Les messages sont-ils stables ?** | `logger.info("commande " + id)` ou un gabarit avec variables dans `msg` : le contexte doit aller dans des champs |
| **Les niveaux sont-ils justes ?** | les 4xx attendus loguées en `error` ? des `info` qui inondent (une ligne par élément d'une boucle) ? |
| **Les erreurs non rattrapées** | `uncaughtException` / `unhandledRejection` passent-elles par le logger ? |
| **La corrélation** | y a-t-il un `req_id` (ou `trace_id`) sur les logs d'une requête ? Est-il propagé aux appels sortants ? |
| **Le masquage couvre-t-il le domaine ?** | la liste `redact` contient-elle les champs sensibles propres à l'app (téléphone, adresse…) ? |
| **Les sondes et `/metrics`** sont-elles exclues des logs d'accès ? | sinon, des milliers de lignes inutiles |
| **Les dashboards Grafana** (s'ils sont dans le repo, en JSON ou en ConfigMap) | des `quantile_over_time ... unwrap` ou des `rate(...)` sur logs regardés en continu → proposer une métrique `prom-client` ou une recording rule Loki |
| **Les labels Alloy** | au-delà des noms suspects que le script détecte : combien de labels au total (5 à 10 recommandés) ? Des valeurs dynamiques ? |
| **La rétention Loki** | réglée ? cohérente avec une éventuelle règle de cycle de vie S3 (cette règle doit être plus longue que la rétention) ? |

Si la config de la plateforme (Alloy, Loki) n'est pas dans le repo, dis-le, et liste les questions à poser à qui la gère : labels, rétention, structured metadata. Ne présume pas qu'elle est correcte.

## 4. Le rapport

````markdown
# Audit kube-logs : <repo> (<date>)

**Résumé** : 3 à 5 lignes. L'app suit-elle le principe « JSON sur stdout, la plateforme fait le reste » ? Les 2 ou 3 priorités.

## Bloquant
Problèmes qui font perdre des logs, en exposent de sensibles, ou mettent la plateforme en danger :
fichiers ou PVC de logs, secrets logués, labels à forte cardinalité, rétention absente.
### fichier:ligne : constat
**Pourquoi c'est un problème** : une phrase, en citant la section du standard.
**Correction** :
```diff
- ...
+ ...
```

## Important
Logs illisibles ou peu exploitables : stack traces multi-lignes, niveau numérique, console.*, pas de req_id, npm start.

## Suggestions
Métriques à la place de panneaux sur logs, structured metadata, niveaux à ajuster.

## Ce qui est déjà bien
````

Classe chaque constat selon son **effet réel**, pas selon le niveau donné par le script.

Ne modifie rien sans qu'on te le demande. Si l'utilisateur dit d'appliquer, passe par **kube-logs-setup** pour les corrections, puis relance le script.

## Migration depuis des fichiers de logs (le cas fréquent)

Quand l'app écrit dans des fichiers, souvent sur un PVC, le rapport propose la migration dans cet ordre, sans perte de logs :
1. Faire écrire l'app sur stdout en JSON (kube-logs-setup).
2. Vérifier dans Grafana que les logs arrivent dans Loki avec les bons labels.
3. Retirer le transport fichier, le sidecar éventuel, le `volumeMount`, puis le PVC. Avant de supprimer le PVC, demander à l'utilisateur s'il faut archiver les anciens fichiers.
4. Si le PVC empêchait d'avoir plusieurs réplicas (`ReadWriteOnce`), le signaler : on peut maintenant en ajouter.
