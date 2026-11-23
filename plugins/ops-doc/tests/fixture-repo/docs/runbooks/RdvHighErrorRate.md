# Alerte : RdvHighErrorRate

| | |
|---|---|
| **Sévérité** | warning (> 5 %), critical (> 20 %) |
| **Expression** | `sum(rate(http_requests_total{job="rdv-api", code=~"5.."}[5m])) / sum(rate(http_requests_total{job="rdv-api"}[5m])) > 0.05` pendant 10 min |
| **Défini dans** | `alerts/rdv.yaml` |

## Signification
Plus de 5 % des requêtes API renvoient une erreur 5xx. L'API tourne, mais une partie des requêtes échoue.

## Impact
Certaines actions échouent (réservation, annulation…). Selon la route touchée, ça va de « gênant » à « bloquant ».

## Diagnostic

1. **Quelles routes ?**
   ```promql
   topk(5, sum by (route, code) (rate(http_requests_total{job="rdv-api", code=~"5.."}[5m])))
   ```

2. **Quelles erreurs ?** Loki :
   ```logql
   {namespace="rdv-prod", app="rdv-api"} | json | level="error" | line_format "{{.route}} {{.msg}}"
   ```

3. **Corrélé à un deploy ?** `argocd app history rdv-prod | tail -3`

4. **Corrélé à la base ?** Dashboard CNPG : connexions, verrous, requêtes longues.
   ```bash
   kubectl cnpg psql rdv-pg -n rdv-prod -- -c \
     "select pid, now()-query_start as duree, state, left(query,80) from pg_stat_activity where state<>'idle' order by duree desc limit 10;"
   ```

## Remédiation
- **Deploy récent** → [rollback](../procedures/deploiement-rollback.md).
- **Requête bloquée ou verrou** : `select pg_cancel_backend(<pid>);`. Si ça ne suffit pas, `pg_terminate_backend`. Le noter dans le canal.
- **Trop de connexions** (`too many clients`) : vérifier `DB_MAX_CONNS` × nombre de replicas par rapport à `max_connections` ([dimensionnement](../dimensionnement.md)).
- **Dépendance externe** (Brevo…) : vérifier sa page de statut ; ça ne devrait pas casser l'API, ouvrir un ticket si c'est le cas.

## Vérifier que c'est résolu
Le taux d'erreur repasse sous 1 % pendant 15 min sur le dashboard.

## Historique
—

## Escalade
Si le taux reste au-dessus de 20 % après 30 min malgré un rollback : traiter comme [RdvApiDown](RdvApiDown.md) (page de maintenance, prévenir le cabinet).
