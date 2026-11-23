---
name: kube-logs-setup
description: >
  Met en place ou corrige le logging d'une application Kubernetes selon le principe « une ligne JSON par
  événement sur stdout, la plateforme fait le reste » : configuration du logger (Node.js/TypeScript avec
  pino et pino-http en priorité), niveaux en texte, masquage des secrets, req_id, erreurs sur une seule
  ligne, gestion des exceptions non rattrapées, Dockerfile qui lance Node directement ; et côté plateforme,
  pipeline Grafana Alloy (parsing JSON, labels sobres, structured metadata), rétention Loki et recording
  rules. À utiliser pour « configure les logs de mon app », « passe mes logs en JSON », « arrête d'écrire les
  logs dans un fichier », « configure Alloy pour Loki », « active la rétention Loki », ou pour appliquer les
  corrections d'un audit kube-logs.
---

# kube-logs-setup

Lis d'abord `../kube-logs/references/standard.md` (à partir du dossier de ce skill). Ensuite, selon la partie à configurer :

| Partie | Référence |
|---|---|
| App Node.js / TypeScript | `references/node-pino.md` : la configuration éprouvée en production par l'auteur du plugin |
| Alloy, Loki (rétention, recording rules) | `references/alloy-loki.md` |
| Autre langage | Pas de référence éprouvée dans ce plugin. Applique le standard (section 3) avec le logger JSON idiomatique du langage, en le disant à l'utilisateur, et vérifie la doc officielle du logger. Par exemple : Go `log/slog` avec `slog.NewJSONHandler(os.Stdout, …)`, Python `structlog` ou `python-json-logger`, Java Logback avec un encodeur JSON |

## Démarche

1. **Constater l'existant.** Lance `python3 <dossier de ce skill>/../kube-logs/scripts/audit_logs.py <repo>` et lis le code qui logue : logger utilisé, framework (Express, Fastify, NestJS…), transports, Dockerfile, manifests.
2. **S'adapter au framework.** Fastify embarque pino : on configure ses options, on n'ajoute pas un second logger. NestJS : `nestjs-pino`. Express : `pino` + `pino-http`. Ne change pas de bibliothèque de log si celle en place peut produire le format du standard (winston sait faire du JSON sur stdout avec `format.json()` et `transports.Console`). Une migration de bibliothèque a un coût, et c'est à l'utilisateur de décider.
3. **Appliquer le standard**, en adaptant la référence au code existant :
   - un module logger unique, importé partout ;
   - JSON sur stdout, niveau en texte, horodatage ISO, `service` ;
   - `redact` avec les chemins sensibles **du domaine de l'app**, pas seulement ceux de l'exemple ;
   - logs d'accès HTTP avec `req_id` ; sondes et `/metrics` exclues ;
   - erreurs logguées sous la forme `{ err }` ; gestionnaires `uncaughtException` / `unhandledRejection` ;
   - remplacement des `console.*` du code applicatif, et règle ESLint `no-console` ;
   - `pino-pretty` en devDependency, activé seulement dans un terminal ;
   - Dockerfile : `CMD ["node", "<point d'entrée compilé>"]`.
4. **Retirer l'ancien** : transports fichier, sidecar `tail`, `volumeMount` et PVC de logs. Demande avant de supprimer un PVC : il peut contenir un historique à archiver.
5. **Côté plateforme**, seulement si la config est dans le repo, ou si l'utilisateur le demande :
   - Alloy : parsing JSON, labels limités (`namespace`, `app`, `container`, éventuellement `level`), `pod`, `req_id` et `trace_id` en structured metadata ;
   - Loki : rétention activée dans le bloc `compactor`, règle de cycle de vie S3 plus longue que la rétention ;
   - pour un panneau sur logs regardé en continu : une métrique `prom-client`, ou à défaut une recording rule.
6. **Vérifier** :
   - relance le script d'audit ;
   - lance l'app en local en redirigeant sa sortie (sans TTY, donc en JSON), provoque une requête et une erreur volontaire, puis valide la sortie avec l'outil (voir **kube-logs-validate**) :
     ```bash
     node dist/main.js 2>&1 | python3 <dossier de ce skill>/../kube-logs/scripts/validate_logs.py
     ```
   - si l'app est déployée, valide aussi ce qui arrive dans Loki (`validate_logs.py --loki … --query '{app="<app>"}'`) ;
   - propose d'ajouter le test de contrat des logs en CI (voir kube-logs-validate).

## Rendre la main

Récapitule les fichiers modifiés et, pour chaque changement, la règle du standard qui le justifie. Liste ce qui reste à faire hors du repo : config Alloy ou Loki gérée ailleurs, suppression du PVC, ajout de réplicas devenu possible. Si tu as ajouté `prom-client`, rappelle qu'il faut un `ServiceMonitor` pour que Prometheus récupère les métriques.
