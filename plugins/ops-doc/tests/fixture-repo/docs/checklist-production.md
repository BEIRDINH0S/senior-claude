# Checklist de mise en production (Production Readiness Review)

> On la déroule avant la première mise en prod, puis avant chaque changement majeur. Elle ne sert pas à écrire la doc : elle sert à **vérifier qu'elle existe**.
> Inspirée de la checklist de Mercari (github.com/mercari/production-readiness-checklist).

Dernière revue : **2026-11-20**. Case cochée = fait, « (partiel) » = à compléter.

## Données
- [x] Archivage WAL continu + base backup quotidien vers S3 hors du cluster
- [x] **Restauration testée** (PITR, le 2026-11-18)
- [x] Alerte si le backup échoue ou date de plus de 26 h
- [ ] Backups répliqués chez un 2e fournisseur

## Observabilité
- [x] Métriques app (`/metrics`) + ServiceMonitor
- [x] Logs JSON structurés dans Loki, sans données personnelles
- [x] Dashboard Grafana de l'app + dashboard CNPG
- [x] **Chaque alerte a un `runbook_url`** qui pointe vers un runbook existant
- [x] Alertes envoyées vers un canal lu (Discord)
- [x] Watchdog / deadman switch externe (healthchecks.io)
- [x] Sonde externe hors cluster (Uptime Kuma)

## Déploiement
- [x] GitOps : rien n'est appliqué à la main en prod
- [x] Images taguées par SHA, scannées (Trivy) en CI
- [x] Procédure de rollback écrite **et testée**
- [x] Migrations idempotentes en hook PreSync
- [ ] (partiel) Staging iso-prod (staging n'a qu'une instance PG)

## Résilience
- [x] Probes readiness/liveness ; la readiness ne dépend pas de la base
- [x] Requests/limits fondées sur des mesures ([dimensionnement](dimensionnement.md))
- [x] 2 réplicas + PDB, anti-affinité
- [x] Arrêt propre (SIGTERM, `terminationGracePeriodSeconds: 30`)

## Sécurité
- [x] Aucun secret en clair dans Git (SOPS)
- [x] NetworkPolicy default deny + flux explicites
- [x] `runAsNonRoot`, `readOnlyRootFilesystem`, PSA `restricted` sur le namespace
- [x] TLS cert-manager + alerte d'expiration

## Documentation
- [x] Fiche service, architecture, inventaire de config
- [x] Plan de reprise avec RTO/RPO mesurés
- [ ] **Suppléant formé** : personne d'autre ne connaît l'app
