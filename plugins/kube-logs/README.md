# kube-logs

> **Le principe** : l'app écrit **une ligne JSON par événement sur stdout**, et c'est tout. Le runtime de conteneurs, Grafana Alloy, Loki et Grafana collectent, stockent, font tourner les fichiers, appliquent la rétention et affichent.

## D'où ça vient

Avant, j'écrivais les logs de mon app dans des fichiers, sur un PVC. Il fallait faire un `exec` dans le pod pour les lire, la rotation était à ma charge, et le volume attachait le pod à un nœud. Découvrir la stack d'observabilité de Kubernetes (Prometheus, Grafana, Loki) a tout changé : je n'ai plus qu'à formater mes logs en JSON et à les écrire sur stdout, et les outils s'occupent du reste.

Ce plugin encode cette pratique, **recoupée avec la documentation officielle** de Kubernetes, Grafana Loki et Alloy, OpenTelemetry et pino (sources en fin de [`standard.md`](skills/kube-logs/references/standard.md)). La configuration Node.js/pino est celle que j'utilise en production. Pour les autres langages, le standard s'applique, mais je n'ai pas de configuration éprouvée à proposer.

## Les skills

| Skill | Pour |
|---|---|
| **kube-logs** | Le standard (chaîne des logs, format, niveaux, masquage, labels Loki, rétention, logs ou métriques) et les deux scripts. Oriente vers le bon skill |
| **kube-logs-audit** | « Mon logging est-il bon ? » : script, puis lecture, puis rapport priorisé. Plan de migration depuis des fichiers de logs ou un PVC |
| **kube-logs-setup** | Mettre en place ou corriger : pino et pino-http, `redact`, `req_id`, erreurs sur une ligne, Dockerfile, pipeline Alloy, rétention Loki, recording rules |
| **kube-logs-validate** | **Prouver** que les logs réellement produits sont au bon format : en local, en CI, via `kubectl logs` ou directement dans Loki |
| **kube-logs-query** | LogQL pour enquêter et pour les dashboards, en signalant quand un panneau devrait être une métrique Prometheus |

## Ce que l'audit détecte

| Côté app | Côté plateforme |
|---|---|
| logs écrits dans des fichiers (pino, winston, log4js, streams) | labels Loki à forte cardinalité dans Alloy (`user_id`, `trace_id`, `pod`…) |
| volume monté pour les logs, sidecar `tail -f` | `loki.process` sans parsing JSON |
| `console.*` dans le code applicatif | **rétention Loki absente** (désactivée par défaut, donc logs conservés pour toujours) |
| niveau pino numérique, pas de `redact`, `pino-pretty` en prod | |
| secrets mentionnés dans des appels de log, `err.stack` loguée en texte | |
| `CMD npm start` ou forme shell (SIGTERM mal transmis) | |

```bash
python3 plugins/kube-logs/skills/kube-logs/scripts/audit_logs.py /chemin/du/repo          # rapport lisible
python3 plugins/kube-logs/skills/kube-logs/scripts/audit_logs.py /chemin/du/repo --json   # pour la CI (code 1 si erreur)
```

## Valider les logs réels : `validate_logs.py`

L'audit lit le code ; cet outil lit **ce que l'app écrit vraiment**, ligne par ligne. Il vérifie :
- que chaque ligne est un objet JSON (pas de lignes de `npm`, pas de stack éclatée) ;
- les champs obligatoires, le niveau en texte, une date ISO ;
- que les erreurs sont sérialisées ;
- l'absence de secret ou d'e-mail en clair, même imbriqué ;
- que les messages sont stables.

```bash
node dist/main.js 2>&1 | python3 validate_logs.py                                    # en local ou en CI
python3 validate_logs.py --kubectl "-n prod -l app.kubernetes.io/name=api --since=1h" # dans le cluster
python3 validate_logs.py --loki http://localhost:3100 --query '{app="api"}' --since 6h # ce qui est arrivé dans Loki
python3 validate_logs.py /var/log/pods/prod_api-*/api/0.log                          # fichiers bruts du nœud (format CRI)
```
Le code de sortie vaut 1 si des lignes sont hors format, ce qui permet d'en faire un **test de contrat en CI** : lancer l'app, générer du trafic, valider sa sortie. Les règles se règlent par projet dans `.kube-logs.json`.

## Installation

```
/plugin marketplace add BEIRDINH0S/senior-claude
/plugin install kube-logs@senior-claude
```
Ou à la main : un lien symbolique de chaque dossier `skills/*` vers `~/.claude/skills/`. Les skills doivent rester côte à côte.

## Licence

[MIT](../../LICENSE)
