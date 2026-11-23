# Node.js / TypeScript avec pino

C'est la configuration éprouvée en production par l'auteur du plugin. Pino écrit du JSON sur stdout par défaut et c'est rapide ; Fastify l'utilise nativement.

## Installation

```bash
npm install pino pino-http
npm install --save-dev pino-pretty     # dev uniquement : jamais en dépendance de prod
```

## Le logger : `src/logger.ts`

```ts
import pino from "pino";

const isTTY = process.stdout.isTTY;   // vrai dans un terminal, faux dans un conteneur

export const logger = pino({
  level: process.env.LOG_LEVEL ?? "info",
  base: { service: process.env.SERVICE_NAME ?? "api" },   // pas de pid/hostname : Kube les fournit
  timestamp: pino.stdTimeFunctions.isoTime,                 // "time":"2026-11-23T14:02:11.482Z"
  messageKey: "msg",
  formatters: {
    level: (label) => ({ level: label }),                   // "level":"info" plutôt que 30
  },
  redact: {
    paths: [
      "req.headers.authorization",
      "req.headers.cookie",
      'res.headers["set-cookie"]',
      "*.password",
      "*.token",
      "*.secret",
    ],
    censor: "[masqué]",
  },
  // En local seulement : affichage lisible. En conteneur (pas de TTY) : JSON brut.
  transport: isTTY ? { target: "pino-pretty" } : undefined,
});
```

Pourquoi chaque option :
- **`level` depuis `LOG_LEVEL`** : passer en `debug` sur un pod en changeant une variable, sans toucher au code.
- **`base`** : par défaut, pino ajoute `pid` et `hostname`. Dans Kubernetes, le hostname est le nom du pod, déjà fourni par Alloy ; `service` est plus utile.
- **`formatters.level`** : le niveau en texte, lisible et filtrable dans Grafana (`| json | level="error"`). Limite : pino refuse ce formateur quand on utilise plusieurs cibles de transport (`transport.targets`). On n'en a pas besoin ici, puisque stdout suffit.
- **`redact`** : le masquage est garanti par la configuration, pas par la vigilance. Ajoutez les chemins propres à votre domaine.
- **`transport` conditionnel** : `pino-pretty` reste une dépendance de dev. Dans le conteneur, `isTTY` est faux, donc JSON. Si `NODE_ENV=production` est la convention de l'équipe, on peut tester ça plutôt.

## Les requêtes HTTP : `pino-http`

```ts
import { randomUUID } from "node:crypto";
import pinoHttp from "pino-http";
import { logger } from "./logger";

export const httpLogger = pinoHttp({
  logger,
  genReqId: (req, res) => {
    const id = (req.headers["x-request-id"] as string) ?? randomUUID();
    res.setHeader("x-request-id", id);
    return id;
  },
  customAttributeKeys: { reqId: "req_id" },
  customLogLevel: (_req, res, err) =>
    err || res.statusCode >= 500 ? "error" : res.statusCode >= 400 ? "warn" : "info",
  autoLogging: { ignore: (req) => req.url === "/healthz" || req.url === "/metrics" },
});
```
- **`req_id`** : repris de l'en-tête s'il existe (un ingress ou un service amont peut en fournir un), et renvoyé au client pour qu'un utilisateur puisse le citer dans un ticket.
- **Niveau selon le statut** : un 404 n'est pas une erreur.
- **On ignore les sondes et `/metrics`** : sinon, des milliers de lignes inutiles par heure.
- Dans le code d'une route, `req.log.info(...)` hérite du `req_id`.

Express : `app.use(httpLogger)`. Fastify : passer `logger` dans les options de Fastify, qui utilise pino nativement. NestJS : `nestjs-pino`.

## Les erreurs

```ts
try {
  await createRdv(input);
} catch (err) {
  req.log.error({ err, rdv_slot: input.slot }, "échec de création du rendez-vous");
  throw err;
}
```
- **Toujours `{ err }`** : pino sérialise l'erreur en `{type, message, stack}` dans un champ JSON, donc sur une ligne.
- **Jamais `logger.error(err.stack)`** ni `console.error(err)` : la stack part en texte multi-lignes, et chaque ligne devient une entrée séparée dans Loki. C'est la cause classique des « logs illisibles ».

## Les erreurs non rattrapées

Sans gestionnaire, Node imprime la stack sur stderr en plusieurs lignes, hors du logger.
```ts
process.on("uncaughtException", (err) => {
  logger.fatal({ err }, "uncaughtException");
  process.exit(1);
});
process.on("unhandledRejection", (reason) => {
  logger.fatal({ err: reason }, "unhandledRejection");
  process.exit(1);
});
```
Avec la destination par défaut de pino (stdout synchrone), la ligne est écrite avant `exit`. Si vous avez configuré une destination asynchrone, videz-la avant de sortir (voir « Exit logging » dans la doc pino).

## Le Dockerfile

```dockerfile
CMD ["node", "dist/main.js"]
```
- **Pas de `npm start`** : npm s'intercale comme processus parent, ajoute ses propres lignes (`> app@1.0.0 start`) dans les logs, et ne transmet pas toujours SIGTERM à Node. Kubernetes finit alors par tuer le pod de force après `terminationGracePeriodSeconds`.
- **Forme exec (avec crochets)**, pas `CMD node dist/main.js` : la forme shell fait de `/bin/sh` le PID 1, et il ne transmet pas les signaux.
- Si l'app lance des sous-processus, ajoutez un init minimal : `ENTRYPOINT ["/sbin/tini", "--"]`, ou `--init` / `shareProcessNamespace` selon le contexte.

## Bannir `console.*` du code applicatif

ESLint :
```json
{ "rules": { "no-console": "error" } }
```
avec une exception pour les scripts CLI et les tests. `console.log(obj)` affiche les gros objets sur plusieurs lignes (`util.inspect`), sans niveau ni contexte.

## Les métriques à côté : `prom-client`

Pour ce qui se compte ou se mesure en continu (requêtes, erreurs, latence), exposez une métrique plutôt que de la recalculer depuis les logs :
```ts
import client from "prom-client";
client.collectDefaultMetrics();
export const httpDuration = new client.Histogram({
  name: "http_request_duration_seconds",
  help: "Durée des requêtes HTTP",
  labelNames: ["method", "route", "status_code"],
});
```
Exposez `/metrics`, puis déclarez un `ServiceMonitor` pour que Prometheus le récupère. Côté métriques aussi, `route` doit être le **modèle** de route (`/api/rdv/:id`), pas l'URL réelle, sinon la cardinalité explose.
