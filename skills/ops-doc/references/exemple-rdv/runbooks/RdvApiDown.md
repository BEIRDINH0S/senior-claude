# Alerte : RdvApiDown

| | |
|---|---|
| **Sévérité** | critical |
| **Expression** | `sum(up{job="rdv-api", namespace="rdv-prod"}) == 0` pendant 2 min, **ou** sonde Uptime Kuma KO |
| **Défini dans** | `alerts/rdv.yaml` |

## Signification
Aucun pod `rdv-api` ne répond au scraping Prometheus. L'API est probablement inaccessible.

## Impact
**Les clients ne peuvent plus réserver.** Le front s'affiche mais toutes les actions échouent.

## Diagnostic

1. **Les pods tournent-ils ?**
   ```bash
   kubectl get pods -n rdv-prod -l app.kubernetes.io/name=rdv-api
   ```
   - `CrashLoopBackOff` → étape 2
   - `Pending` → étape 4
   - `Running` mais pas `Ready` → étape 3

2. **Pourquoi ça crashe ?**
   ```bash
   kubectl logs -n rdv-prod deploy/rdv-api --previous --tail=50
   kubectl describe pod -n rdv-prod -l app.kubernetes.io/name=rdv-api | grep -A5 "Last State"
   ```
   - `OOMKilled` → cause B
   - `connection refused ... 5432` → cause C
   - Erreur de config ou de variable manquante → cause A

3. **Pourquoi pas Ready ?** La readiness tape sur `/healthz`.
   ```bash
   kubectl exec -n rdv-prod deploy/rdv-api -- wget -qO- localhost:8080/healthz
   ```

4. **Pourquoi Pending ?**
   ```bash
   kubectl describe pod -n rdv-prod <pod> | tail -20   # Events : Insufficient memory ? node not ready ?
   kubectl get nodes
   ```

5. **Un déploiement récent ?**
   ```bash
   argocd app history rdv-prod | tail -3
   ```
   Si un sync a eu lieu dans les 30 dernières minutes, c'est le suspect n°1 → cause A.

## Remédiation

### A. Mauvais déploiement
**Rollback d'abord, analyse ensuite.** Voir [deploiement-rollback](../procedures/deploiement-rollback.md).

### B. OOMKilled
Augmenter temporairement la limite mémoire dans `apps/rdv/overlays/prod`, commit, sync. Ouvrir un ticket pour comprendre la cause (fuite ? requête qui charge trop ?) et mettre à jour le [dimensionnement](../dimensionnement.md).

### C. Base inaccessible
```bash
kubectl cnpg status rdv-pg -n rdv-prod
```
- Failover en cours : attendre 1 min, l'API se reconnecte toute seule.
- Aucun primaire : voir le dashboard CNPG et les logs `{namespace="rdv-prod", pod=~"rdv-pg-.*"}`. Escalader si ce n'est pas résolu en 15 min.

### D. Nœud(s) down
`kubectl get nodes`. Si un nœud est `NotReady`, les pods doivent se replanifier. Sinon, `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`.

## Vérifier que c'est résolu
- `kubectl get pods`: 2/2 Ready
- https://rdv.example.fr : créer puis annuler un RDV de test
- Alerte `resolved` dans Discord

## Escalade
Pas d'escalade aujourd'hui (une seule personne). **Si ce n'est pas résolu en 1 h** : afficher le message de maintenance (`kubectl apply -f apps/rdv/maintenance.yaml`) et prévenir le cabinet par SMS.

## Historique
- 2026-11-08 : mauvaise variable d'env après un deploy, rollback en 4 min.
