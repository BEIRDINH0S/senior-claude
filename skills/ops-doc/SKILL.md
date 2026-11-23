---
name: ops-doc
description: >
  Point d'entrée de la documentation d'exploitation (doc ops) d'une application, surtout sur Kubernetes :
  fiche service, architecture, inventaire de config et secrets, dimensionnement, plan de reprise (RPO/RTO),
  runbooks liés aux alertes, procédures, ADR, post-mortems, checklist de mise en prod, DAT/DEX.
  Contient le standard, les modèles, un exemple complet et le script de vérification utilisés par
  ops-doc-init, ops-doc-import, ops-doc-check et ops-doc-review. À utiliser dès qu'on parle de documenter
  une app pour l'exploitation ou l'astreinte, d'écrire ou de mettre à jour un runbook, un post-mortem, un
  ADR ou une procédure, de préparer un DEX ou un dossier d'exploitation, ou quand on demande « où en est la
  doc ops », même sans prononcer « ops-doc ».
---

# ops-doc

Une doc d'exploitation sert à une chose : qu'une personne compétente qui **ne connaît pas l'app** puisse la faire tourner, diagnostiquer une panne et la réparer **sans appeler l'auteur**. Tout le reste en découle.

Ce skill porte le **standard commun** et oriente vers le skill adapté à l'état de la doc.

## Ressources partagées (dans le dossier de ce skill)

| Chemin | Quand le lire |
|---|---|
| `references/standard.md` | **Toujours avant de produire ou juger de la doc.** Arborescence, sections obligatoires par fichier, conventions, règles du script |
| `references/exemple-rdv/` | Un exemple complet et conforme (app fictive « rdv » : API Go, CNPG, ArgoCD). Pour voir le niveau de détail attendu. **Ne pas recopier ses valeurs** : elles sont inventées |
| `assets/templates/` | Les modèles à copier dans `docs/`, avec les marqueurs `TODO(ops-doc)` |
| `scripts/check_docs.py` | Vérification mécanique. `python3 <ce dossier>/scripts/check_docs.py <repo> [--docs DIR] [--manifests DIR]`. Bibliothèque standard uniquement |

Les autres skills `ops-doc-*` utilisent ces chemins sous la forme `../ops-doc/...` à partir de leur propre dossier : ils sont installés côte à côte.

## Choisir le bon skill selon l'état de la doc

Regarde d'abord ce qui existe (`ls docs/`, recherche de README, wiki ou fichiers .docx d'exploitation), puis :

| Situation | Skill |
|---|---|
| Aucune doc ops, ou seulement un README de dev | **ops-doc-init** : génère `docs/` à partir du repo |
| De la doc existe mais pas au standard : un gros README fourre-tout, un export de wiki, un Word, des notes | **ops-doc-import** : repère les infos, les classe, crée les fichiers |
| `docs/` suit le standard, on veut savoir s'il est conforme et à jour | **ops-doc-check** |
| La doc est conforme, on veut savoir si elle est bonne (utilisable en astreinte) | **ops-doc-review** |

L'enchaînement naturel est init ou import → check → review, puis check à chaque MR qui touche l'exploitation.

Si l'utilisateur ne précise pas, dis-lui en une phrase ce que tu as trouvé et quel skill tu enchaînes, puis enchaîne.

## Petites tâches de maintenance (à faire directement ici)

Elles ne justifient pas un autre skill :
- **Nouvelle alerte** → copier `assets/templates/runbooks/_template.md` vers `docs/runbooks/<NomExactDeLAlerte>.md`, le remplir avec les vrais noms (namespace, workload), et ajouter `runbook_url` à l'alerte dans la PrometheusRule.
- **Incident** → `docs/postmortems/AAAA-MM-JJ-titre.md` depuis le modèle. Sans blâme, avec un tableau d'actions qui a des responsables et des échéances. Mettre à jour la section Historique des runbooks concernés.
- **Décision d'architecture** → `docs/adr/NNNN-titre.md`, numéro suivant. Un ADR accepté ne se modifie pas : on le remplace par un nouveau.
- **Opération planifiée récurrente** → `docs/procedures/verbe-objet.md` depuis le modèle.
- **Nouvelle variable ou nouveau secret** → une ligne dans `docs/config.md`, sans la valeur.

Après chaque modification, relance le script de vérification.

## Si un hook a bloqué ton commit ou ton push

Le hook `ops-doc` bloque les `git commit` et `git push` qui touchent l'exploitation tant que la doc n'a pas été vérifiée pour cet état exact. Son message dit quoi faire : **ops-doc-check** limité au diff pour un commit, **ops-doc-review** sur les fichiers concernés pour un push. Fais le travail pour de vrai, mets la doc à jour, puis enregistre ton rapport avec la commande indiquée. L'enregistrement n'est là que pour éviter de refaire le travail quand rien n'a changé. Enregistrer sans avoir relu viderait le contrôle de son sens. Si tu penses que le blocage est un faux positif, dis-le à l'utilisateur plutôt que de le contourner.

## Règles qui valent pour tous les skills ops-doc

- **Ne rien inventer.** Un chiffre (RTO, SLO, taille observée), un nom de responsable ou une justification de décision qu'on ne trouve ni dans le repo ni chez l'utilisateur devient un `TODO(ops-doc): <question précise>`. Une doc fausse est pire qu'une doc trouée, parce qu'on lui fait confiance pendant un incident.
- **Ne jamais écrire une valeur de secret**, même si elle traîne dans la source. Si tu en trouves une dans le repo ou la doc d'origine, signale-la à l'utilisateur : elle est probablement à faire tourner.
- **Lecture seule sur le cluster.** Si `kubectl` est disponible, tu peux faire des `get` et des `describe` pour compléter. Jamais d'action qui modifie quoi que ce soit, jamais de lecture du contenu d'un Secret.
- **Les vrais noms partout** : les commandes des runbooks doivent pouvoir se copier-coller telles quelles.
- **Liens Markdown relatifs**, pas de `[[wikilink]]`.
- **La langue de l'équipe** : celle de la doc existante, sinon celle de l'utilisateur.
