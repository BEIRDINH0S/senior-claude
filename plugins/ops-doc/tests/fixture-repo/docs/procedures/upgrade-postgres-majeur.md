# Procédure : montée de version majeure de PostgreSQL

> Exemple : 17 → 18. Les versions **mineures** (17.4 → 17.5) se font en changeant juste `imageName` : CNPG redémarre les instances en commençant par les répliques.

## Prérequis
- [ ] Version de l'opérateur CNPG compatible (voir les release notes)
- [ ] L'app testée contre la nouvelle version **en staging**
- [ ] Backup récent réussi
- [ ] Créneau annoncé au cabinet (une coupure courte est possible)

## Méthode retenue : import dans un nouveau cluster
CNPG peut créer un nouveau cluster en important les données d'un cluster existant (`bootstrap.initdb.import`). L'ancien reste intact : **le retour arrière consiste simplement à repointer l'app vers lui.**

1. Créer `rdv-pg-18` avec :
   ```yaml
   spec:
     imageName: ghcr.io/cloudnative-pg/postgresql:18
     bootstrap:
       initdb:
         import:
           type: microservice
           databases: [app]
           source:
             externalCluster: rdv-pg
     externalClusters:
       - name: rdv-pg
         connectionParameters:
           host: rdv-pg-rw
           user: postgres
           dbname: postgres
         password:
           name: rdv-pg-superuser
           key: password
   ```
   (activer temporairement `enableSuperuserAccess: true` sur `rdv-pg`)
2. Vérifier les données (comptages par table).
3. **Couper les écritures** (page de maintenance), puis refaire l'import pour récupérer le delta, ou accepter une coupure le temps d'un import complet (≈ 5 min pour 1,2 Gi).
4. Pointer l'app vers `rdv-pg-18-rw`, sync, vérifier.
5. Configurer les backups sur `rdv-pg-18`, lancer un backup.
6. Garder `rdv-pg` 7 jours, puis le supprimer.

> CNPG propose aussi les upgrades majeurs en place (`pg_upgrade`) dans ses versions récentes : plus rapide, mais sans retour arrière simple. Pour une petite base, l'import est plus sûr.

## Vérification
- `kubectl cnpg status rdv-pg-18 -n rdv-prod` : instances saines, version 18
- Comptages par table identiques entre `rdv-pg` et `rdv-pg-18`
- App fonctionnelle, premier backup de `rdv-pg-18` réussi

## Retour arrière
Repointer l'app vers `rdv-pg-rw` (tant qu'il existe encore).
