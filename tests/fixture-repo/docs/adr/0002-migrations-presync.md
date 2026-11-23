# 0002 - Migrations de schéma en hook ArgoCD PreSync

- **Statut** : accepté
- **Date** : 2026-10-02
- **Décideurs** : Camille R.

## Contexte
L'API lançait ses migrations au démarrage. Avec 2 replicas, les deux pods tentaient de migrer en même temps, et une migration ratée faisait crasher tous les pods en boucle.

## Options envisagées
1. Migrations au démarrage de l'app, avec un verrou (advisory lock)
2. Init container
3. **Job Kubernetes en hook ArgoCD `PreSync`**

## Décision
**Hook PreSync.** Le Job tourne **une seule fois**, **avant** le déploiement de la nouvelle version. S'il échoue, ArgoCD arrête le sync et l'ancienne version continue de tourner.

```yaml
metadata:
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
```

## Conséquences
- **Gain** : Une migration ratée ne casse plus la prod : elle bloque juste le déploiement
- **Coût** : Pendant le déploiement, l'**ancienne** version de l'app tourne sur le **nouveau** schéma. Les migrations doivent donc être **rétrocompatibles** (méthode expand/contract) :
  - ajouter une colonne nullable → déployer le code qui l'utilise → rendre la colonne obligatoire plus tard
  - ne jamais renommer ou supprimer une colonne dans la même release que le code qui arrête de l'utiliser
- **Gain** : Conséquence directe : on ne fait jamais de rollback du schéma (voir [deploiement-rollback](../procedures/deploiement-rollback.md))
