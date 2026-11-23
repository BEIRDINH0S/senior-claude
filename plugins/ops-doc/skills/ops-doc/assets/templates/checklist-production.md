# Checklist de mise en production

> À dérouler avant la première mise en prod, puis avant chaque changement majeur. Elle ne sert pas à écrire la doc : elle sert à vérifier qu'elle existe.

Dernière revue : AAAA-MM-JJ.

## Données
- [ ] Sauvegardes automatiques vers un stockage hors du cluster
- [ ] Restauration testée (date : )
- [ ] Alerte si la sauvegarde échoue ou est trop ancienne

## Observabilité
- [ ] Métriques applicatives exposées et scrapées
- [ ] Logs structurés, sans données personnelles ni secrets
- [ ] Dashboard de l'app
- [ ] Chaque alerte a un `runbook_url` vers un runbook existant
- [ ] Alertes envoyées vers un canal réellement lu
- [ ] Watchdog / deadman switch externe
- [ ] Sonde externe hors du cluster

## Déploiement
- [ ] GitOps : rien n'est appliqué à la main en prod
- [ ] Images taguées immuablement (SHA / semver) et scannées
- [ ] Procédure de rollback écrite et testée
- [ ] Migrations de schéma rétrocompatibles, lancées hors du démarrage de l'app

## Résilience
- [ ] Probes readiness/liveness (la readiness ne dépend pas de la base)
- [ ] Requests/limits fondées sur des mesures
- [ ] Au moins 2 réplicas + PodDisruptionBudget pour les composants sans état
- [ ] Arrêt propre sur SIGTERM

## Sécurité
- [ ] Aucun secret en clair dans Git
- [ ] NetworkPolicy default deny + flux explicites
- [ ] `runAsNonRoot`, `readOnlyRootFilesystem`, Pod Security `restricted`
- [ ] TLS + alerte d'expiration du certificat

## Documentation
- [ ] Fiche service, architecture, inventaire de config
- [ ] Plan de reprise avec RTO/RPO mesurés
- [ ] Au moins deux personnes savent intervenir
