# Dimensionnement

Dernière revue : AAAA-MM-JJ. Période observée : TODO(ops-doc).

## Méthode

1. Observer au moins 7 à 14 jours de prod dans Prometheus.
2. CPU : `request` = p95 observé ; pas de limit CPU, pour éviter le throttling.
3. Mémoire : `request` = `limit` = max observé + 25 %.
4. Comparer avec [KRR](https://github.com/robusta-dev/krr) ou le VPA en mode recommandation.

```promql
quantile_over_time(0.95,
  sum by (pod, container) (rate(container_cpu_usage_seconds_total{namespace="NAMESPACE", container!=""}[5m]))[14d:5m])

max_over_time(
  sum by (pod, container) (container_memory_working_set_bytes{namespace="NAMESPACE", container!=""})[14d:5m])
```

## Compute

| Conteneur | CPU p95 observé | Mémoire max observée | requests | limits |
|---|---|---|---|---|
| | TODO(ops-doc) | TODO(ops-doc) | | |

## Stockage

| Volume | Taille | Utilisé | Croissance | Plein dans |
|---|---|---|---|---|
| | | | | |

```promql
predict_linear(kubelet_volume_stats_available_bytes{namespace="NAMESPACE"}[3d], 7*24*3600) < 0
```

## Réplicas

| Composant | Réplicas | Pourquoi |
|---|---|---|
| | | |
