---
name: kube-logs
description: >
  Bonnes pratiques des logs d'une application sur Kubernetes avec la stack Prometheus / Loki / Grafana :
  l'app écrit une ligne JSON par événement sur stdout et la plateforme (runtime de conteneurs, Alloy,
  Loki, Grafana) collecte, stocke, fait tourner les fichiers et affiche. Contient le standard (format,
  niveaux, masquage, labels Loki et cardinalité, structured metadata, rétention, logs ou métriques) et
  le script d'audit utilisés par kube-logs-audit, kube-logs-setup et kube-logs-query. À utiliser dès qu'on
  parle de logs dans une app conteneurisée : logger, format JSON, stdout, fichiers de logs, PVC de logs,
  Loki, Alloy, Promtail, Fluent Bit, labels, LogQL, « mes logs sont illisibles », « où mettre mes logs »,
  « Loki est lent », même sans dire kube-logs.
---

# kube-logs

**Le principe** : l'app écrit **une ligne JSON par événement sur stdout**, et c'est tout. Les fichiers, la rotation, le transport, le stockage, la rétention et l'affichage sont le travail de la plateforme : runtime de conteneurs, kubelet, Alloy, Loki et Grafana. Une app qui gère elle-même ses fichiers de logs refait mal ce que la plateforme fait déjà, et se prive de tout ce qu'elle offre.

## Ressources (dans le dossier de ce skill)

| Chemin | Quand le lire |
|---|---|
| `references/standard.md` | **Avant de produire ou de juger quoi que ce soit.** La chaîne des logs, pourquoi pas de fichiers ni de PVC, le format d'une ligne, les niveaux, le masquage, les labels Loki, la rétention, logs ou métriques, avec les sources officielles |
| `scripts/audit_logs.py` | Audit **statique** : code (JS/TS), `package.json`, Dockerfile, manifests, config Alloy et Loki. `python3 <ce dossier>/scripts/audit_logs.py <repo> [--json]` |
| `scripts/validate_logs.py` | Validation **des logs réellement produits** (fichier, stdin, `kubectl logs`, API Loki) : chaque ligne doit respecter le format. `python3 <ce dossier>/scripts/validate_logs.py --help`. Lecture seule |

Les deux scripts n'utilisent que la bibliothèque standard Python.

Les autres skills `kube-logs-*` accèdent à ces fichiers via `../kube-logs/...`.

## Choisir le bon skill

| Demande | Skill |
|---|---|
| « Est-ce que mon logging est bon ? », relecture d'un repo, migration depuis des fichiers de logs | **kube-logs-audit** |
| Mettre en place ou corriger le logger d'une app, configurer Alloy ou la rétention Loki | **kube-logs-setup** |
| Prouver que les logs produits (en local, en CI, dans le cluster ou dans Loki) sont au bon format | **kube-logs-validate** |
| Écrire une requête LogQL, enquêter sur un incident, construire un panneau Grafana sur logs | **kube-logs-query** |

Pour une question de principe (« pourquoi pas de fichiers ? », « faut-il mettre user_id en label ? »), réponds directement à partir du standard, en citant la section concernée.

## Règles qui valent pour tous les skills kube-logs

- **Expliquer le pourquoi** à partir du standard, surtout quand on corrige une habitude (fichiers sur un PVC, `console.log`, labels nombreux). C'est le pourquoi qui empêche la régression.
- **Ne jamais mettre en label un champ à valeurs non bornées** (identifiants, URL, IP, e-mail, pod). Ils vont dans le JSON ou en structured metadata.
- **Ne jamais proposer de loguer un secret ni une donnée personnelle**, même « temporairement pour déboguer ».
- **Vérifier les noms d'options** d'Alloy, de Loki et de pino dans la documentation de la version utilisée quand un doute existe : ces outils évoluent vite. Les exemples des références sont des points de départ, pas des vérités figées.
- **Ce qui se compte ou se mesure en continu est une métrique Prometheus**, pas une requête sur les logs. Signale-le quand tu le vois.
