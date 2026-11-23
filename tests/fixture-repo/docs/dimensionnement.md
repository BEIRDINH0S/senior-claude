# Dimensionnement

> **On a mesuré, on n'a pas deviné.** Chaque valeur indique d'où elle vient et quand elle a été revue.
> Revue : **tous les 3 mois**, ou quand une alerte de capacité se déclenche.

Dernière revue : **2025-01-10**. Période observée : 2026-11-06 → 2026-11-20 (14 jours de prod).

## Méthode

1. Observer au moins 7 à 14 jours de prod dans Prometheus.
2. **CPU** : `request` = p95 observé (arrondi au-dessus). **Pas de limit CPU**, pour éviter le throttling.
3. **Mémoire** : `request` = `limit` = max observé + 25 %. Au-delà de la limite, le pod est OOMKilled, donc on garde de la marge.
4. Comparer avec [KRR](https://github.com/robusta-dev/krr) : `krr simple -n rdv-prod`.

```promql
# CPU p95 sur 14 jours, par conteneur
quantile_over_time(0.95,
  sum by (pod, container) (rate(container_cpu_usage_seconds_total{namespace="rdv-prod", container!=""}[5m]))[14d:5m])

# Mémoire max sur 14 jours
max_over_time(
  sum by (pod, container) (container_memory_working_set_bytes{namespace="rdv-prod", container!=""})[14d:5m])
```

## Résultat : compute

| Conteneur | CPU p95 observé | Mémoire max observée | **requests** | **limits** |
|---|---|---|---|---|
| `rdv-api` | 35m | 48 Mi | cpu 50m, mem 64Mi | mem 64Mi |
| `rdv-front` | 5m | 12 Mi | cpu 10m, mem 32Mi | mem 32Mi |
| `rdv-pg` (postgres) | 80m | 410 Mi | cpu 100m, mem 1Gi | mem 1Gi |
| `rdv-rappels` | 20m (pic) | 30 Mi | cpu 20m, mem 64Mi | mem 64Mi |

## Postgres

| Paramètre | Valeur | Pourquoi |
|---|---|---|
| `shared_buffers` | `256MB` | ≈ 25 % de la mémoire du pod (1 Gi) |
| `effective_cache_size` | `768MB` | ≈ 75 % : c'est une indication pour le planificateur, pas une allocation |
| `max_connections` | `50` | 2 pods API × `DB_MAX_CONNS=10` + cron + marge ; pas besoin de PgBouncer |
| `work_mem` | `8MB` | Requêtes simples |

## Stockage

| Volume | Taille | Utilisé (2026-11-20) | Croissance | Plein dans |
|---|---|---|---|---|
| Données PG (par instance) | 10 Gi | 1,2 Gi | ≈ 60 Mi/mois | > 10 ans |
| WAL PG (par instance) | 5 Gi | 0,4 Gi | stable si l'archivage fonctionne | — |
| S3 `rdv-backups` | — | 9 Go | 30 base backups + WAL | stable (rétention 30 j) |
| Loki (S3) | — | 3 Go | rétention 30 j | stable |

```promql
# Taille de la base
cnpg_pg_database_size_bytes{namespace="rdv-prod", datname="app"}

# Alerte "plein dans 7 jours" (voir runbook PVCFillingUp)
predict_linear(kubelet_volume_stats_available_bytes{namespace="rdv-prod"}[3d], 7*24*3600) < 0
```

> [!note] Pourquoi un volume séparé pour le WAL ?
> Si l'archivage vers S3 casse, le WAL s'accumule localement. Sur un volume séparé, ça remplit le volume WAL sans toucher aux données. Voir le post-mortem [2026-11-12](postmortems/2026-11-12-wal-plein.md).

## Réplicas

| Composant | Réplicas | Pourquoi |
|---|---|---|
| `rdv-api` | 2 + PDB `minAvailable: 1` | Pas pour la charge : pour drainer un nœud sans coupure |
| `rdv-front` | 2 + PDB | Idem |
| `rdv-pg` | 2 instances (anti-affinité nœud) | Failover automatique en environ 30 s |
| HPA | **non** | Le trafic ne le justifie pas (pic à 20 req/s, 1 pod tient 200 req/s au test de charge) |
