# LogQL : enquêter et construire des panneaux

## Le principe d'une requête

```
{sélecteur de labels}  | filtres de ligne | parseur | filtres de champs | mise en forme
```
1. **Le sélecteur** (`{namespace="rdv-prod", app="rdv-api"}`) choisit les flux grâce à l'index. Plus il est précis, moins Loki lit de données. Il est obligatoire et doit contenir au moins un matcher positif.
2. **Les filtres de ligne** (`|=`, `!=`, `|~`, `!~`) agissent sur le texte brut, **avant** le parsing. C'est la façon la moins coûteuse d'éliminer des lignes.
3. **Le parseur** (`| json`) transforme les champs JSON en labels de requête (temporaires, sans effet sur l'index).
4. **Les filtres de champs** (`| level="error"`, `| status_code >= 500`).
5. **La mise en forme** (`| line_format "{{.msg}}"`).

Règle de performance : **sélecteur précis, filtre de ligne d'abord, `| json` ensuite**.

## Enquêter (Grafana > Explore)

```logql
# Les erreurs d'une app
{namespace="rdv-prod", app="rdv-api"} | json | level="error"

# Une requête précise, de bout en bout (req_id en structured metadata ou dans le JSON)
{namespace="rdv-prod"} | req_id="8f1c2a"
{namespace="rdv-prod"} |= "8f1c2a" | json

# Un texte, puis le parsing seulement sur les lignes retenues
{app="rdv-api"} |= "timeout" | json | line_format "{{.time}} {{.msg}} {{.err_message}}"

# Les 5xx d'une route
{app="rdv-api"} | json | status_code >= 500 and route="POST /api/rdv"
```

Dans `| json`, un champ imbriqué devient `parent_enfant` : `err.message` donne `err_message`.

## Les panneaux (requêtes métriques sur logs)

```logql
# Volume de lignes par niveau (panneau « Log volume »)
sum by (level) (count_over_time({app="rdv-api"} | json [5m]))

# Taux d'erreurs par seconde
sum(rate({app="rdv-api"} | json | level="error" [5m]))

# Top 5 des messages d'erreur sur l'heure
topk(5, sum by (msg) (count_over_time({app="rdv-api"} | json | level="error" [1h])))

# Latence p95 par route depuis un champ numérique (responseTime, ajouté par pino-http)
quantile_over_time(0.95, {app="rdv-api"} | json | unwrap responseTime [5m]) by (route)
```

### Avant d'ajouter un panneau sur logs : la bonne source
| Le panneau | Source recommandée |
|---|---|
| Un taux ou une latence regardés en continu, ou qui servent à alerter | une **métrique Prometheus** exposée par l'app (`prom-client`) |
| Pas de métrique possible et le panneau est souvent rafraîchi | une **recording rule** du ruler Loki (voir `kube-logs-setup/references/alloy-loki.md`) |
| Top des messages, détail ponctuel, volume par niveau | une **requête LogQL directe** |

`quantile_over_time` avec `unwrap` relit et parse toutes les lignes de la fenêtre à chaque rafraîchissement. C'est le premier panneau à remplacer par un histogramme Prometheus.

## Pièges fréquents
- **Un sélecteur trop large** (`{namespace=~".+"}`) : Loki lit tout. Toujours cibler une app.
- **Filtrer après `| json` ce qu'un `|=` aurait éliminé avant** : on parse des lignes pour rien.
- **Un champ introuvable** : vérifiez son nom après aplatissement (`err_message`) et que la ligne est bien du JSON. Les lignes en erreur de parsing portent le label `__error__` : `| json | __error__=""` les exclut, et `| __error__!=""` les montre.
- **Des stack traces éclatées sur plusieurs entrées** : le problème est dans l'app (stack écrite en texte), pas dans la requête. Voir le standard, section 3.

## Sources
- https://grafana.com/docs/loki/latest/query/
- https://grafana.com/docs/loki/latest/query/log_queries/
- https://grafana.com/docs/loki/latest/query/metric_queries/
