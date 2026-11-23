---
name: kube-logs-validate
description: >
  Vérifie que les logs réellement produits par une application respectent le format attendu : une ligne =
  un objet JSON, champs time/level/msg présents, niveau en texte, date ISO, erreurs sérialisées, aucun
  secret ni e-mail en clair, messages stables. Valide un fichier, la sortie d'une commande, les fichiers
  bruts de /var/log/pods, `kubectl logs`, ou directement ce qui est arrivé dans Loki via son API. Donne un
  taux de conformité, des exemples par règle, et un code de sortie pour la CI. À utiliser pour « vérifie
  que mes logs sont au bon format », « est-ce que tous mes logs sont en JSON en prod », « contrôle les logs
  dans Loki », « ajoute un test de format des logs en CI », ou pour prouver qu'une correction de logging
  marche vraiment.
---

# kube-logs-validate

`kube-logs-audit` lit le **code**. Ici, on lit les **logs réellement produits** : c'est la preuve que le format est respecté, y compris pour ce que le code ne montre pas (une lib qui écrit sur stdout, le runtime Node qui imprime une exception, `npm` qui ajoute ses lignes).

L'outil : `../kube-logs/scripts/validate_logs.py` (à partir du dossier de ce skill). Bibliothèque standard uniquement, **lecture seule**.

## Choisir la source

| Situation | Commande |
|---|---|
| L'app tourne dans le cluster | `validate_logs.py --kubectl "-n <ns> -l app.kubernetes.io/name=<app> --since=1h --tail=-1"` |
| Vérifier ce qui est **arrivé dans Loki** (après Alloy) | `validate_logs.py --loki <url> --query '{namespace="<ns>", app="<app>"}' --since 6h` (+ `--header 'X-Scope-OrgID: …'` si Loki est multi-tenant) |
| Un fichier de logs, ou des fichiers bruts de `/var/log/pods` | `validate_logs.py fichier.log` (le préfixe CRI est retiré, et les lignes partielles recollées) |
| L'app en local ou en CI | `node dist/main.js \| validate_logs.py` ou `npm test 2>&1 \| validate_logs.py`, selon ce qui produit des logs applicatifs |

Pour Loki dans le cluster sans exposition : `kubectl port-forward -n <monitoring> svc/<loki-gateway> 3100:80`, puis `--loki http://localhost:3100`. Demande avant de lancer des commandes `kubectl` : le contexte courant peut être la prod. Toutes les commandes sont en lecture seule.

## Lire le résultat

- **`PAS-JSON` et `STACK-ECLATEE`** : des lignes écrites hors du logger. Les exemples montrent d'où elles viennent (`> app@1.0.0 start` désigne npm, `    at …` une stack écrite en texte, un message de lib tierce une lib à brancher sur le logger).
- **`SECRET-CLE`, `SECRET-VALEUR`** : **à traiter en premier**. Une valeur sensible est déjà dans Loki : il faut corriger le `redact`, puis faire tourner le secret exposé. Ce n'est pas qu'un problème de format.
- **`MSG-VARIABLE`** : le gabarit affiché (`commande <n> créée`) montre la partie stable ; les valeurs vont dans des champs.
- **0 ligne lue** : sélecteur, période ou labels faux. Ce n'est pas une conformité.

Les règles sont décrites dans `../kube-logs/references/standard.md`, section 9.

## Adapter les règles au projet

Un fichier `.kube-logs.json` à la racine (ou `--config`) remplace les valeurs par défaut :
```json
{
  "required": ["time", "level", "msg", "service"],
  "levels": ["debug", "info", "warn", "error", "fatal"],
  "sensitive_keys": ["password", "token", "authorization", "cookie", "iban", "phone"],
  "max_line_bytes": 16384
}
```
Ajoute les champs sensibles propres au domaine de l'app.

## En CI : un test de contrat sur les logs

Le but : faire échouer la CI si une MR introduit un log hors format. Il faut faire tourner l'app (ou ses tests d'intégration) et valider ce qu'elle écrit :
```yaml
logs-format:
  image: node:22
  script:
    - npm ci && npm run build
    - node dist/main.js > app.log 2>&1 & APP_PID=$!
    - sleep 3 && npx wait-on http://localhost:8080/healthz
    - npm run test:e2e        # génère du trafic, donc des logs, y compris des erreurs
    - kill $APP_PID || true
    - python3 tools/validate_logs.py app.log
```
`2>&1` est voulu : une stack imprimée sur stderr par le runtime doit faire échouer le test. Au début, `--tolerance 0.01` peut laisser le temps de corriger l'existant, mais l'objectif reste 0.

## Rendre la main

Donne le taux de conformité, les règles touchées par ordre de gravité avec un exemple chacune, et pour chacune la correction (renvoie vers **kube-logs-setup** pour l'appliquer). S'il y a un secret exposé, dis-le en premier et explicitement.
