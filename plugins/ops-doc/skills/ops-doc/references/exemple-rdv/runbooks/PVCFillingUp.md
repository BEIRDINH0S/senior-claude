# Alerte : PVCFillingUp

| | |
|---|---|
| **Sévérité** | warning (plein dans 7 j), critical (> 90 %) |
| **Expression** | `predict_linear(kubelet_volume_stats_available_bytes{namespace="rdv-prod"}[3d], 7*24*3600) < 0` |
| **Défini dans** | `alerts/storage.yaml` |

## Signification
À ce rythme, un volume (le plus souvent PG données ou WAL) sera plein dans moins de 7 jours.

## Impact
Aucun pour l'instant. **Si le volume se remplit, Postgres s'arrête** : l'app est down et le redémarrage est délicat.

## Diagnostic

1. **Quel volume ?** Le label `persistentvolumeclaim` de l'alerte.
   - `rdv-pg-N-wal` → étape 2
   - `rdv-pg-N` (données) → étape 3

2. **WAL qui grossit = archivage cassé dans 90 % des cas.**
   ```bash
   kubectl cnpg status rdv-pg -n rdv-prod   # Working WAL archiving ?
   ```
   Si c'est KO → [CNPGBackupFailed](CNPGBackupFailed.md). Une fois l'archivage réparé, le WAL se vide tout seul.
   Autre cause possible : un replication slot inactif qui retient du WAL.
   ```sql
   select slot_name, active, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) from pg_replication_slots;
   ```

3. **Données qui grossissent**
   ```sql
   select relname, pg_size_pretty(pg_total_relation_size(relid)) from pg_statio_user_tables order by pg_total_relation_size(relid) desc limit 10;
   ```
   Croissance normale → agrandir (ci-dessous). Croissance anormale (table de logs, bloat) → ticket.

## Remédiation : agrandir le volume
La StorageClass doit avoir `allowVolumeExpansion: true`.
1. Dans `apps/rdv-pg/cluster.yaml`, augmenter `spec.storage.size` (ou `spec.walStorage.size`).
2. Commit, MR, sync. CNPG redimensionne les PVC.
3. Mettre à jour le [dimensionnement](../dimensionnement.md).

> [!danger] Ne jamais supprimer de fichiers WAL à la main dans `pg_wal`.

## Vérifier que c'est résolu
- `kubelet_volume_stats_available_bytes` remonte, ou la nouvelle taille du PVC apparaît dans `kubectl get pvc -n rdv-prod`.
- L'alerte repasse en `resolved`.

## Escalade
Au-dessus de 95 % sans cause identifiée : couper les écritures (page de maintenance) avant que Postgres ne s'arrête, puis agrandir le volume.

## Historique
- 2026-11-12 : WAL plein à 92 %, archivage cassé. [Post-mortem](../postmortems/2026-11-12-wal-plein.md).
