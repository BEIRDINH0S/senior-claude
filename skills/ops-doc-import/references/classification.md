# Grille de classement des informations

Pour chaque information extraite d'une source, la question à se poser est : **qui va la chercher, et à quel moment ?**

| Si l'information est… | Indices dans le texte | Elle va dans |
|---|---|---|
| Ce que fait l'app, pour qui | « l'application permet », « utilisée par » | `README.md`, en tête |
| Qui contacter, qui est responsable | noms, équipes, « en cas de problème appeler » | `README.md` : Responsable, Suppléant, Astreinte |
| Une URL, un dashboard, un lien | http…, « le Grafana est ici » | `README.md` > Liens |
| Un composant, une techno | « l'API en Go », « un Redis pour les sessions » | `README.md` > Composants + `architecture.md` |
| Ce dont l'app dépend | « appelle l'API X », « envoie des mails via » | `README.md` > Dépendances (**avec** ce qui se passe si ça tombe) |
| Comment accéder au cluster, à la base | « le kubeconfig est », « pour se connecter » | `README.md` > Accès (**jamais** les valeurs) |
| Des flux, des ports, du réseau | « le port 5432 », « seul X parle à Y » | `architecture.md` > Flux réseau |
| Où sont les données, les sauvegardes, leur rétention | « backup tous les soirs », « on garde 30 jours » | `architecture.md` > Données |
| Le pipeline, les environnements | « on merge sur main puis », « staging » | `architecture.md` > Déploiement + `procedures/deploiement-rollback.md` |
| Une limite connue, un « attention » | « attention, si… », « ne pas… », « connu pour » | `architecture.md` > Risques, ou l'endroit où le risque se manifeste |
| Une variable, un paramètre | `FOO=`, « la variable X » | `config.md` > Variables |
| Un secret, une clé, un mot de passe | « le token », « la clé API » | `config.md` > Secrets (nom + gestion uniquement) ; **valeur en clair → rapport** |
| Une taille, une ressource, un nombre de réplicas | « 2 Go de RAM », « 3 pods » | `dimensionnement.md` (indique la date de la source) |
| Que faire si tout est perdu, RPO/RTO | « en cas de sinistre », « PRA » | `reprise.md` |
| Que faire quand une **alerte** ou un **symptôme** apparaît | « si l'alerte X », « quand les utilisateurs voient une 502 », « si ça rame » | `runbooks/<Alerte>.md` ; si aucune alerte ne correspond → rapport : alerte à créer |
| Comment faire une opération **choisie** | « pour déployer », « pour restaurer », « une fois par an, renouveler » | `procedures/<verbe-objet>.md` |
| **Pourquoi** on a choisi quelque chose | « on a choisi X parce que », « on a abandonné Y » | `adr/NNNN-…md` (statut : accepté ; date : celle de la source, sinon `TODO`) |
| Le récit d'un incident passé | une date + « panne », « incident », « on a perdu » | `postmortems/AAAA-MM-JJ-…md` + Historique du runbook concerné |
| Une case de vérification avant prod | « avant de passer en prod, vérifier » | `checklist-production.md` |

## Cas ambigus

- **Une commande de diagnostic sans contexte** (« `kubectl logs -l app=api` ») → dans le runbook dont le symptôme l'utilise le plus probablement, avec une confiance moyenne. Si aucun runbook ne s'impose, mets-la dans `README.md` > Commandes utiles.
- **« Redémarrer X si ça plante »** → c'est une remédiation (donc un runbook), pas une procédure. Si c'est le seul remède connu, signale-le dans le rapport : redémarrer soigne le symptôme, la cause reste à trouver.
- **Une décision et sa procédure mélangées** (« on utilise Velero, voici comment restaurer ») → coupe en deux : le pourquoi dans un ADR, le comment dans une procédure.
- **Une info datée** (« actuellement 3 Go ») → reporte-la avec sa date d'origine, ou vérifie-la dans le repo.
- **Une opinion ou un historique sans valeur pour l'exploitation** (« c'était mieux avant ») → n'importe pas, et ne la cite pas dans le rapport non plus.
