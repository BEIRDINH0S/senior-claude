# Procédure : déploiement et rollback

## Déploiement normal

1. Merge sur `main` de `rdv-app` → la CI build l'image `registry.gitlab.com/acme/rdv-app:<sha>` et ouvre une MR sur `rdv-gitops` qui met à jour le tag dans `overlays/staging`.
2. Merge de cette MR → ArgoCD synchronise staging.
3. **Vérifier staging** : pods Ready, créer un RDV de test, pas d'erreur dans les logs.
4. Promotion en prod : MR qui copie le tag dans `overlays/prod`, puis merge.
5. Tag Git `prod-AAAAMMJJ-N` sur le commit → ArgoCD synchronise la prod.
6. **Surveiller 15 min** : dashboard `rdv-overview` (taux de 5xx, latence), canal d'alertes.

> Pas de déploiement le vendredi après 16h ni la veille d'un jour où personne n'est disponible.

## Rollback

> **Rollback d'abord, analyse ensuite.** On répare l'incident en restaurant la version précédente ; on cherche la cause une fois le service rétabli.

### Option 1 : revert Git (recommandé, reste GitOps)
```bash
cd rdv-gitops
git revert <commit-du-bump-prod> --no-edit
git push
git tag prod-$(date +%Y%m%d)-rollback && git push --tags
```
ArgoCD resynchronise sur l'ancien tag d'image. **Durée : ~3 min.**

### Option 2 : rollback ArgoCD (en urgence, si GitLab est indisponible)
```bash
argocd app history rdv-prod
argocd app rollback rdv-prod <ID>
```
> [!warning] L'auto-sync doit être désactivé pour que le rollback tienne, sinon Argo réapplique `main`. **Faire le revert Git juste après** pour que Git redevienne la source de vérité, puis réactiver l'auto-sync.

### Et la base ?
Les migrations doivent être **rétrocompatibles** (expand/contract, voir [ADR 0002](../adr/0002-migrations-presync.md)). L'ancienne version de l'app tourne donc sur le nouveau schéma, et **on ne fait pas de rollback du schéma**.
Si une migration a cassé des données → [restauration-pitr](restauration-pitr.md).

## Vérification
- `argocd app get rdv-prod` : `Synced` et `Healthy`
- Le tag d'image en cours est bien l'ancien : `kubectl get deploy -n rdv-prod rdv-api -o jsonpath='{.spec.template.spec.containers[0].image}'`
- Taux de 5xx revenu à la normale
