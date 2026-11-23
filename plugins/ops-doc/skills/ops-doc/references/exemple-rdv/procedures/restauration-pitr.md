# Procédure : restauration de la base (PITR)

> **Quand** : données corrompues, `DELETE` accidentel, migration destructrice, ou reconstruction complète du cluster.
> **Durée mesurée** : 35 min pour 1,2 Gi (test du 2026-11-18).

## Principe
CNPG ne restaure **jamais en place**. On crée un **nouveau** `Cluster` qui démarre depuis le dernier base backup, puis rejoue le WAL jusqu'à l'instant choisi. Une fois vérifié, on bascule l'app dessus.

> [!danger] Ne pas écraser l'archive d'origine
> Le nouveau cluster doit archiver sous un **autre `serverName`** que l'ancien. Sinon il écrit par-dessus le WAL dont on pourrait encore avoir besoin.

## Étapes

### 1. Choisir l'instant cible
Juste **avant** l'incident, en UTC. Exemple : le `DELETE` a eu lieu à 14:03 heure de Paris → cible `2026-11-20 13:02:00+00`.

### 2. Vérifier qu'un backup antérieur existe
```bash
kubectl get backups -n rdv-prod --sort-by=.metadata.creationTimestamp
```

### 3. Créer le cluster de restauration
`apps/rdv-pg/restore/cluster-restore.yaml` :
```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: rdv-pg-restore
  namespace: rdv-prod
spec:
  instances: 1                   # 1 suffit pour vérifier ; on monte à 2 après bascule
  storage: { size: 10Gi }
  walStorage: { size: 5Gi }
  bootstrap:
    recovery:
      source: origin
      recoveryTarget:
        targetTime: "2026-11-20 13:02:00+00"
  externalClusters:
    - name: origin
      plugin:
        name: barman-cloud.cloudnative-pg.io
        parameters:
          barmanObjectName: rdv-pg-store
          serverName: rdv-pg            # l'archive qu'on LIT
  plugins:
    - name: barman-cloud.cloudnative-pg.io
      isWALArchiver: true
      parameters:
        barmanObjectName: rdv-pg-store
        serverName: rdv-pg-restore      # l'archive où on ÉCRIT (différente)
```
Commit, MR, sync.

### 4. Suivre la restauration
```bash
kubectl get cluster -n rdv-prod rdv-pg-restore -w
kubectl logs -n rdv-prod -l cnpg.io/cluster=rdv-pg-restore -f
```

### 5. Vérifier les données
```bash
kubectl cnpg psql rdv-pg-restore -n rdv-prod -- -d app -c "select count(*), max(created_at) from rendez_vous;"
```
Le `max(created_at)` doit être juste avant l'instant cible, et les données supprimées doivent être revenues.

### 6. Basculer
Deux options :
- **Restauration partielle** (quelques lignes) : `pg_dump` des tables concernées depuis `rdv-pg-restore`, puis réinjection dans `rdv-pg`. **L'app ne s'arrête pas.**
- **Restauration complète** : pointer l'app vers `rdv-pg-restore-rw` (Secret `rdv-pg-restore-app`), commit, sync. Les écritures faites après l'instant cible sont perdues : **prévenir le cabinet**.

### 7. Nettoyer
- Restauration partielle : supprimer `rdv-pg-restore`.
- Restauration complète : renommer dans Git, passer à `instances: 2`, recréer la `ScheduledBackup`, **lancer un backup tout de suite**, mettre à jour la doc ([config](../config.md), [README](../README.md)).

## Retour arrière
La restauration ne touche pas au cluster d'origine `rdv-pg`. Tant que l'app n'a pas basculé (étape 6), il suffit de supprimer `rdv-pg-restore`. Après une bascule complète, revenir sur `rdv-pg` fait perdre les écritures faites depuis sur le cluster restauré.

## Vérification finale
- [ ] App fonctionnelle sur les données restaurées
- [ ] Backup réussi sur le nouveau cluster
- [ ] `Working WAL archiving: OK`
- [ ] Post-mortem ouvert
