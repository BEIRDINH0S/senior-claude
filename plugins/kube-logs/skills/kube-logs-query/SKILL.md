---
name: kube-logs-query
description: >
  Écrit des requêtes LogQL pour Grafana Loki à partir de logs JSON : enquêter sur un incident (erreurs
  d'une app, suivi d'une requête par req_id ou trace_id, recherche d'un message), et construire des
  panneaux de dashboard (volume par niveau, taux d'erreurs, top des messages), en signalant quand un
  panneau devrait plutôt être une métrique Prometheus ou une recording rule Loki. Optimise les requêtes
  lentes : sélecteur précis, filtres de ligne avant le parsing. À utiliser pour « écris une requête Loki »,
  « comment je retrouve cette erreur dans Grafana », « fais-moi un panneau des erreurs », « ma requête Loki
  est lente », « suis cette requête dans les logs », même sans dire LogQL.
---

# kube-logs-query

La référence LogQL est dans `references/logql.md` (dossier de ce skill). Le standard est dans `../kube-logs/references/standard.md` : la section 6 explique pourquoi certains champs ne sont pas des labels, et la section 8 traite de « logs ou métriques ».

## Démarche

1. **Connaître les labels réels.** Une requête LogQL repose sur des labels indexés, et une erreur de nom de label renvoie un résultat vide sans aucun message. Si tu as accès à Grafana ou à `logcli`, liste les labels (`logcli labels`, `logcli labels app`). Sinon, déduis-les de la config Alloy du repo, et à défaut, demande-les. Ne suppose pas qu'un champ du JSON est un label.
2. **Construire du plus sélectif au plus coûteux** :
   - sélecteur sur les labels, le plus précis possible (namespace **et** app) ;
   - filtres de ligne (`|=`, `|~`) pour éliminer tôt ;
   - `| json`, puis les filtres sur les champs ;
   - mise en forme.
3. **Pour une enquête**, donne une suite de requêtes qui vont du large au précis : les erreurs, puis une requête particulière (`req_id`), puis le contexte autour (même pod, même minute). Explique ce que chacune doit montrer.
4. **Pour un panneau**, applique la règle du standard avant d'écrire la requête :
   - taux, latence ou comptage regardés en continu, ou utilisés pour alerter → **propose une métrique** (`prom-client` en Node, plus un ServiceMonitor) ;
   - si c'est impossible et que le panneau se rafraîchit souvent → **recording rule** Loki (exemple dans `../kube-logs-setup/references/alloy-loki.md`) ;
   - sinon (top des messages, volume par niveau, détail d'enquête) → requête LogQL directe.
   Écris quand même la requête LogQL demandée, et ajoute la recommandation en une phrase. La décision revient à l'utilisateur.
5. **Vérifier la syntaxe** : un sélecteur avec au moins un matcher positif, des noms de champs aplatis après `| json` (`err.message` devient `err_message`), `unwrap` uniquement sur un champ numérique. Quand c'est possible, teste la requête (Grafana Explore ou `logcli query`) plutôt que de l'affirmer juste.

## Si la requête ne renvoie rien ou renvoie du bruit

- **Rien** : le nom ou la valeur du label est-il exact ? La plage de temps et la rétention couvrent-elles la période ? Les lignes sont-elles du JSON (`| __error__!=""` montre les échecs de parsing) ?
- **Des stack traces éclatées sur plusieurs lignes** : c'est un problème de l'app, pas de la requête. Oriente vers **kube-logs-audit** ou **kube-logs-setup**.
- **Une requête lente** : sélecteur trop large, ou `| json` placé avant un filtre de ligne qui aurait suffi.
