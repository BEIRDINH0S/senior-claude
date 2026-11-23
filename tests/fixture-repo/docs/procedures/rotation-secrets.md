# Procédure : rotation des secrets

> **Quand** : rotation annuelle planifiée, départ d'une personne, ou **suspicion de fuite** (secret poussé dans un commit, log…). En cas de fuite, on le fait **tout de suite**.

## Mot de passe applicatif PG (`rdv-pg-app`)
CNPG génère le secret. Pour le régénérer :
```bash
kubectl delete secret -n rdv-prod rdv-pg-app
```
CNPG le recrée avec un nouveau mot de passe et met à jour le rôle dans PG. Ensuite :
```bash
kubectl rollout restart -n rdv-prod deploy/rdv-api
```
**Impact** : quelques secondes de 5xx pendant le redémarrage des pods (les connexions ouvertes avec l'ancien mot de passe restent valides jusqu'au redémarrage).

## Secrets SOPS (`rdv-secrets`, `rdv-s3-creds`)

1. Générer la nouvelle valeur (chez le fournisseur pour S3/SMTP, `openssl rand -base64 32` pour `SESSION_SECRET`).
2. Éditer le fichier chiffré :
   ```bash
   sops apps/rdv/overlays/prod/secrets.enc.yaml
   ```
3. MR, merge, sync.
4. Redémarrer ce qui lit le secret :
   ```bash
   kubectl rollout restart -n rdv-prod deploy/rdv-api
   ```
   Pour les credentials S3, CNPG relit le secret tout seul. Vérifier :
   ```bash
   kubectl cnpg status rdv-pg -n rdv-prod   # Working WAL archiving: OK
   ```
5. **Révoquer l'ancienne valeur** chez le fournisseur. Pour S3, seulement **après** avoir vérifié que l'archivage passe avec la nouvelle.

> [!warning] Leçon du [post-mortem 2026-11-12](../postmortems/2026-11-12-wal-plein.md)
> L'ancienne clé S3 avait été révoquée avant que la nouvelle soit déployée, d'où 2 jours sans archivage. **Toujours dans cet ordre : créer, déployer, vérifier, révoquer.**

## `SESSION_SECRET`
Le changer **déconnecte tous les utilisateurs**. À faire de nuit, sauf en cas de fuite.

## Clé age SOPS
Rotation rare : nouvelle clé, `sops updatekeys` sur tous les fichiers, mise à jour du Secret `sops-age` dans `argocd` **et** de Bitwarden. À faire en procédure dédiée, pas à la volée.

## Vérification
- `kubectl get pods -n rdv-prod` : tous Ready après le redémarrage
- `kubectl cnpg status rdv-pg -n rdv-prod` : `Working WAL archiving: OK` (credentials S3)
- Connexion à l'app OK, pas de pic de 5xx sur le dashboard

## Retour arrière
Tant que l'ancienne valeur n'est pas révoquée, revenir au commit précédent du fichier SOPS et resynchroniser. **Une fois révoquée, il n'y a plus de retour arrière** : c'est pour ça qu'on révoque en dernier.
