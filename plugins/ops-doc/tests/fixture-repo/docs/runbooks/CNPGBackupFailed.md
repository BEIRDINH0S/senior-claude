# Alerte : CNPGBackupFailed

| | |
|---|---|
| **Sévérité** | warning |
| **Expression** | dernier backup réussi > 26 h, **ou** dernier échec plus récent que le dernier succès |
| **Défini dans** | `alerts/cnpg.yaml` |

> [!note] Nom des métriques
> Avec le **plugin Barman Cloud**, les métriques de backup sont exposées par le plugin, pas par le collecteur CNPG historique (`cnpg_collector_last_*_backup_timestamp`). Vérifier le nom exact dans Prometheus avant d'écrire la règle.

## Signification
Le backup planifié (`ScheduledBackup/rdv-pg-daily`, 3h) a échoué, ou n'a pas tourné.

## Impact
**Aucun impact utilisateur.** En cas de restauration, on repartirait d'un base backup plus ancien et on rejouerait plus de WAL : la restauration est plus longue, mais **pas de perte de données tant que l'archivage WAL fonctionne**. Vérifier ce point en priorité (étape 2).

## Diagnostic

1. **État des backups**
   ```bash
   kubectl get backups -n rdv-prod --sort-by=.metadata.creationTimestamp | tail -5
   kubectl describe backup -n rdv-prod <dernier-backup-en-échec>
   ```

2. **L'archivage WAL fonctionne-t-il ?** C'est le plus important.
   ```bash
   kubectl cnpg status rdv-pg -n rdv-prod
   ```
   Section *Continuous Backup status* : `Working WAL archiving: OK` et un `Last Archived WAL` récent.
   Si l'archivage est KO aussi, **le WAL s'accumule sur le disque** → surveiller [PVCFillingUp](PVCFillingUp.md).

3. **Logs**
   ```logql
   {namespace="rdv-prod", pod=~"rdv-pg-.*"} |~ "barman|backup|archive" |= "error"
   ```

4. **Causes fréquentes**
   | Symptôme dans les logs | Cause |
   |---|---|
   | `AccessDenied`, `InvalidAccessKeyId` | credentials S3 expirés ou changés |
   | `NoSuchBucket` | bucket supprimé ou renommé |
   | `QuotaExceeded` | quota du fournisseur atteint |
   | timeout | réseau, NetworkPolicy qui bloque la sortie 443 |

## Remédiation
- **Credentials** : voir [rotation-secrets](../procedures/rotation-secrets.md), section S3.
- **NetworkPolicy** : vérifier la règle d'egress de `rdv-pg` vers le 443.
- Après correction, **relancer un backup à la main** :
  ```bash
  kubectl cnpg backup rdv-pg -n rdv-prod --method plugin --plugin-name barman-cloud.cloudnative-pg.io
  ```

## Vérifier que c'est résolu
- Le nouveau backup est `completed`.
- `Working WAL archiving: OK`.

## Escalade
Si ce n'est pas résolu en 48 h : risque réel. Faire un `pg_dump` manuel vers un autre stockage en attendant.

## Historique
- 2026-11-12 : archivage KO après rotation de clé S3, voir le [post-mortem](../postmortems/2026-11-12-wal-plein.md).
