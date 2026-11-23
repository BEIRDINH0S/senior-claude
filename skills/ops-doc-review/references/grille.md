# Grille de review

Des questions à se poser, par type de document. Elles ne sont pas toutes pertinentes partout : c'est un aide-mémoire, pas un formulaire à remplir.

## Runbook

**Signification et impact**
- Comprend-on ce qui est mesuré **sans connaître la PromQL** ?
- L'impact est-il dit du point de vue de l'utilisateur (« les clients ne peuvent plus réserver »), pas du système (« le pod est down ») ?
- Sait-on si c'est urgent : que se passe-t-il si on attend 1 h ? jusqu'au matin ?

**Diagnostic**
- Le diagnostic est-il ordonné du plus probable au moins probable, ou du plus rapide à vérifier au plus long ?
- Chaque commande : vrais noms, bon namespace, copiable telle quelle, syntaxe juste ?
- Chaque étape dit-elle **quoi regarder dans le résultat** et **où aller selon ce qu'on voit** ?
- Y a-t-il un réflexe « déploiement récent ? » quand c'est pertinent ?
- Les requêtes LogQL et PromQL sont-elles fournies, pas seulement « aller voir dans Grafana » ?

**Remédiation**
- Chaque cause du diagnostic a-t-elle sa remédiation ?
- Les actions destructrices (`delete`, `pg_terminate_backend`, drain, suppression de PVC, `--force`) sont-elles signalées, avec leur conséquence et une alternative plus douce essayée avant ?
- Une remédiation n'est-elle qu'un « redémarrer » ? Si oui, la doc dit-elle quoi capturer **avant** (logs, état), pour que la cause puisse être trouvée ensuite ?
- Renvoie-t-elle vers une procédure existante plutôt que de la recopier ?

**Fin**
- « Vérifier que c'est résolu » est-il observable (métrique, commande, test utilisateur) ?
- Escalade : qui, comment le joindre, à partir de quel délai ? Et s'il n'y a personne : quelle mesure de protection (page de maintenance, prévenir les utilisateurs) ?
- L'historique pointe-t-il vers les post-mortems ?

## Procédure
- Le « quand » est-il clair ? Une procédure qu'on ne sait pas quand utiliser ne sert pas.
- Les prérequis sont-ils vérifiables (des cases à cocher), y compris les accès ?
- L'impact est-il annoncé (coupure, déconnexion des utilisateurs) et faut-il prévenir quelqu'un ?
- Les étapes sont-elles numérotées et atomiques, avec la sortie attendue pour chaque commande importante ?
- Le point de non-retour est-il signalé **avant** qu'on l'atteigne ?
- Le retour arrière est-il possible depuis chaque étape ?
- La vérification finale est-elle explicite ?
- A-t-elle déjà été exécutée ? Une durée mesurée est un bon indice.

## Plan de reprise
- Les RPO/RTO sont-ils mesurés, avec une date, ou juste espérés ?
- **Paradoxe du bootstrap** : tout ce dont on a besoin pour reconstruire est-il disponible si le cluster a disparu ? En particulier :
  - la clé de déchiffrement des secrets (SOPS age/PGP, clé du contrôleur Sealed Secrets) ;
  - le kubeconfig ou l'accès à l'hébergeur ;
  - les credentials du stockage de sauvegardes ;
  - l'accès au repo Git et au registry.
- Les CRD et opérateurs installés à la main sont-ils dans Git ?
- Le DNS (TTL, qui peut le modifier) est-il couvert ?
- La restauration de la base écrit-elle dans une **autre** archive que l'originale (`serverName` différent avec CNPG) ?
- Les scénarios couvrent-ils la suppression accidentelle (PITR), pas seulement la panne matérielle ?

## Fiche service (README)
- Le test des 30 secondes : quoi, gravité, qui appeler, où regarder ?
- Les dépendances disent-elles ce qui se passe quand elles tombent ?
- Y a-t-il un suppléant ? Sinon, est-ce écrit comme un risque ?
- Les liens fonctionnent-ils et pointent-ils vers la prod ?

## Architecture, config, dimensionnement
- Les schémas montrent-ils les composants réels ?
- Les risques listés sont-ils réels et accompagnés d'une mitigation, même « acceptée » ?
- config.md : sait-on **où changer** chaque valeur, et ce qui doit redémarrer après ?
- dimensionnement.md : les valeurs sont-elles justifiées par une mesure ? Distingue-t-on « observé » et « configuré » ?

## ADR
- Le contexte explique-t-il pourquoi il fallait décider ?
- Y a-t-il de **vraies** options écartées, avec la raison ?
- Les conséquences incluent-elles les coûts acceptés, pas seulement les gains ?
- Le statut est-il à jour (un ADR remplacé doit le dire) ?

## Post-mortem
- Est-il sans blâme (pas de « X a oublié de », mais « rien n'empêchait de ») ?
- La chronologie contient-elle la détection, et le délai entre le début et la détection ?
- La cause racine va-t-elle au-delà du déclencheur ?
- Les actions ont-elles un type (prévenir / détecter / atténuer), un responsable, une échéance, un statut ?
- Les runbooks et alertes concernés ont-ils été mis à jour en conséquence ?

## Transversal
- Une seule personne détient-elle le savoir nécessaire (accès, contexte) ?
- Les alertes attendues pour l'archi existent-elles ? Pour une app sur CNPG, on attend au minimum :
  - app indisponible et taux de 5xx ;
  - sauvegarde en échec ou trop ancienne ;
  - archivage WAL en échec ;
  - volume qui se remplit ;
  - réplication en retard ou instance manquante ;
  - certificat qui expire ;
  - Watchdog avec un deadman switch externe.
- La terminologie est-elle constante (le même composant porte le même nom partout) ?
- Les dates de revue sont-elles récentes ?
