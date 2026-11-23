# Le standard ops-doc

La référence commune aux skills `ops-doc-*`. Elle dit **ce que doit contenir** la doc d'exploitation d'une app, **où**, et **pourquoi**. Le script `scripts/check_docs.py` vérifie la partie mécanique de ce standard ; la section « Règles vérifiées par le script » liste exactement quoi.

## Sommaire
1. Principes
2. Arborescence
3. Contenu attendu, fichier par fichier
4. Runbook ou procédure ?
5. Conventions transverses
6. Règles vérifiées par le script
7. Correspondance avec les livrables DAT / DEX

---

## 1. Principes

1. **La doc vit dans le repo**, dans `docs/`, versionnée et relue en MR comme le code. Une doc dans un wiki à part finit par décrire un système qui n'existe plus.
2. **Une alerte = un runbook.** L'alerte porte une annotation `runbook_url` qui pointe vers son runbook. À 3 h du matin, l'astreinte doit passer de la notification à la procédure en un clic.
3. **Rien d'inventé.** Un RTO, un SLO, une taille mesurée ou un responsable viennent d'une mesure ou d'une décision humaine. Quand l'info manque, on écrit un marqueur `TODO(ops-doc): <question précise>`. Une doc fausse est pire qu'une doc incomplète, parce qu'on lui fait confiance.
4. **Jamais de valeur de secret.** On documente le nom d'un secret, ce qu'il contient, qui le gère et comment le faire tourner. Jamais sa valeur.
5. **Des dates.** Le dimensionnement, la checklist et le plan de reprise portent une date de dernière revue ou de dernier test. Sans date, impossible de savoir si on peut encore s'y fier.
6. **Écrite pour quelqu'un qui ne connaît pas l'app.** Le critère de qualité : un ingénieur compétent qui découvre l'app peut diagnostiquer et réparer sans appeler l'auteur.

## 2. Arborescence

```
docs/
├── README.md                 fiche service (point d'entrée, GitLab/GitHub l'affichent par défaut)
├── architecture.md           contexte, conteneurs, flux, données, déploiement, risques
├── config.md                 inventaire des variables et des secrets
├── dimensionnement.md        ressources et stockage, avec la méthode et la date
├── reprise.md                plan de reprise : RPO/RTO, scénarios, reconstruction complète
├── checklist-production.md   revue avant mise en prod (Production Readiness Review)
├── runbooks/                 un fichier par alerte : <NomExactDeLAlerte>.md
├── procedures/               opérations planifiées : <verbe-objet>.md
├── adr/                      décisions : NNNN-titre-court.md
└── postmortems/              incidents : AAAA-MM-JJ-titre-court.md
```

Chaque dossier contient un `_template.md`, copié depuis `assets/templates/`. Le script ignore les fichiers qui commencent par `_`.

Une petite app peut ne pas encore avoir de post-mortem ou d'ADR : le dossier existe quand même, avec son modèle, pour que la place soit prête.

## 3. Contenu attendu, fichier par fichier

Les **sections obligatoires** sont des titres Markdown (`##` ou `###`) dont le texte **contient** le mot-clé, sans tenir compte de la casse ni des accents. « Dépendances externes » satisfait « Dépendances ».

### README.md : la fiche service
Le premier fichier qu'on ouvre. Il répond à « qu'est-ce que c'est, est-ce grave si ça tombe, qui appeler, où regarder ».
- En tête : une phrase qui dit ce que fait l'app, puis un tableau avec **Responsable**, **Criticité**, horaires de service, astreinte, SLO, **RPO / RTO** (avec un renvoi vers `reprise.md`).
- Sections obligatoires : `Liens` (prod, staging, repos, ArgoCD, dashboards, logs, alertes), `Composants` (une ligne par workload, avec sa techno et sa ressource Kube), `Dépendances` (pour chacune, **ce qui se passe si elle tombe**), `Accès` (où sont les accès, sans les valeurs).
- Recommandé : `Sommaire de la doc` (liens vers les autres fichiers), `Commandes utiles`.

### architecture.md
Pour comprendre le système avant de le toucher. C'est un arc42 allégé.
- Sections obligatoires : `Contexte`, `Données`, `Déploiement`, `Risques`.
- Recommandé : objectif et contraintes, schéma de conteneurs, flux réseau (le tableau doit correspondre aux NetworkPolicies), décisions (liens vers `adr/`).
- Les schémas sont en **Mermaid** dans des blocs de code : GitLab, GitHub et Obsidian les affichent, et ils se relisent en diff.

### config.md
- Sections obligatoires : `Variables` (tableau : nom, exemple non sensible, obligatoire ou non, **où c'est défini**), `Secrets` (tableau : nom, contenu, **géré par**, rotation).
- Toute variable d'environnement et tout Secret référencés dans les manifests doivent y figurer.
- Recommandé : où se trouve quoi dans le repo, et où vit la clé qui déchiffre les secrets (SOPS, Sealed Secrets).

### dimensionnement.md
- Une ligne `Dernière revue : AAAA-MM-JJ`.
- Sections obligatoires : `Méthode` (comment on choisit les valeurs, avec les requêtes PromQL), `Stockage` (taille, usage, croissance).
- Recommandé : un tableau compute (observé, requests, limits), les paramètres Postgres, les réplicas et leur justification.
- Les valeurs « observées » viennent de Prometheus. Si on n'a pas encore mesuré, on l'écrit (`TODO(ops-doc)`) plutôt que de reporter les requests comme si c'était une mesure.

### reprise.md
- Sections obligatoires : `RPO`, `RTO` (dans un titre ou un tableau en tête), `Scénarios` (panne de pod, de primaire, de nœud, corruption de données, perte totale), `Reconstruction` (étapes ordonnées depuis un cluster vide).
- Une date de dernier test (game day).
- Recommandé : prérequis hors cluster (où sont la clé de déchiffrement, le kubeconfig, les credentials S3), problèmes rencontrés au dernier test, date du prochain.

### checklist-production.md
- Une ligne `Dernière revue : AAAA-MM-JJ`.
- Des cases à cocher `- [ ]` / `- [x]`, regroupées par thème : Données, Observabilité, Déploiement, Résilience, Sécurité, Documentation.
- Une case cochée doit être vraie dans le repo. `ops-doc-check` le vérifie quand c'est possible.

### runbooks/<Alerte>.md
- Le nom du fichier est **exactement** le nom de l'alerte (`alert:` dans la PrometheusRule).
- En tête : un tableau avec la sévérité, l'**expression** PromQL et le fichier qui définit l'alerte.
- Sections obligatoires : `Signification`, `Impact`, `Diagnostic`, `Remédiation`, `Vérifier` (que c'est résolu), `Escalade`.
- Recommandé : `Historique` (chaque déclenchement, avec le lien vers le post-mortem).
- Le diagnostic va du plus probable au moins probable, avec des commandes **copiables telles quelles** et les vrais noms (namespace, deployment, cluster CNPG).

### procedures/<verbe-objet>.md
- En tête : **quand** on l'utilise, et sa durée si elle est connue.
- Sections obligatoires : `Étapes` (ou des sections numérotées équivalentes), `Vérification`.
- Une mention de `retour arrière` ou de `rollback` : comment annuler si ça se passe mal. Si l'opération est irréversible, le dire explicitement.
- Recommandé : `Prérequis`.

### adr/NNNN-titre.md
- Champs : **Statut** (proposé, accepté, remplacé par NNNN), **Date**.
- Sections obligatoires : `Contexte`, `Décision`, `Conséquences`. Recommandé : `Options envisagées`.
- On ne modifie pas un ADR accepté : quand la décision change, on écrit un nouvel ADR qui le remplace.

### postmortems/AAAA-MM-JJ-titre.md
- Sans blâme : on cherche ce qui, dans le système, a permis l'erreur.
- Sections obligatoires : `Résumé`, `Chronologie`, `Cause` (racine), `Actions` (tableau avec responsable, échéance, type prévenir/détecter/atténuer, fait ou non).
- Recommandé : impact, ce qui a bien marché, ce qui a mal marché, où on a eu de la chance.

## 4. Runbook ou procédure ?

| | Runbook | Procédure |
|---|---|---|
| Déclenché par | une **alerte** (subi) | une **décision** (planifié) |
| Question | « que se passe-t-il, que faire ? » | « comment faire X proprement ? » |
| Structure | signification, impact, diagnostic, remédiation, vérifier, escalade | quand, prérequis, étapes, vérification, retour arrière |
| Nom | `NomDeLAlerte.md` | `verbe-objet.md` |

Une remédiation de runbook renvoie souvent vers une procédure (« → voir `procedures/deploiement-rollback.md` ») plutôt que de la recopier.

## 5. Conventions transverses

- **Liens en Markdown standard et relatifs** : `[rollback](../procedures/deploiement-rollback.md)`. Pas de `[[wikilink]]`, que GitLab et GitHub n'affichent pas.
- **Les marqueurs `TODO(ops-doc): <question>`** sont les seuls « trous » autorisés. Ils se comptent et se cherchent (`grep -rn "TODO(ops-doc)" docs/`).
- **Les dates** au format ISO `AAAA-MM-JJ`.
- **Les commandes** dans des blocs de code avec leur langage (`bash`, `promql`, `logql`, `sql`, `yaml`).
- **Traçabilité de l'import** : un commentaire HTML `<!-- source: chemin:ligne -->` indique d'où vient une info importée. Il est invisible au rendu et ça permet de remonter à l'original.
- **Langue** : celle de l'équipe, la même partout. Les noms techniques (alertes, ressources) restent tels quels.
- **Labels Kubernetes recommandés** sur les ressources : `app.kubernetes.io/name`, `instance`, `version`, `component`, `part-of`, `managed-by`. La doc et les commandes s'appuient dessus (`-l app.kubernetes.io/name=...`).
- **Annotations de liens** (convention `a8r.io`, pas officielle) : `a8r.io/owner`, `a8r.io/runbook`, `a8r.io/documentation` sur les Deployments.

## 6. Règles vérifiées par le script

`scripts/check_docs.py` ne lit que des fichiers, sans dépendance Python externe. Niveaux : **ERREUR** (non conforme), **AVERTISSEMENT** (à corriger), **INFO**.

| Code | Niveau | Règle |
|---|---|---|
| `STRUCT-FICHIER` | erreur | un fichier racine obligatoire manque |
| `STRUCT-DOSSIER` | erreur | un dossier obligatoire manque |
| `STRUCT-MODELE` | avertissement | un dossier n'a pas son `_template.md` |
| `SECTION` | erreur | une section obligatoire manque |
| `CHAMP` | erreur | un champ obligatoire manque (Responsable, Criticité, Statut…) |
| `NOM-FICHIER` | avertissement | ADR ou post-mortem mal nommé |
| `LIEN-CASSE` | erreur | un lien relatif pointe vers un fichier qui n'existe pas |
| `WIKILINK` | avertissement | `[[...]]` utilisé |
| `SECRET` | erreur | quelque chose qui ressemble à une valeur de secret |
| `ALERTE-SANS-URL` | erreur | une alerte du repo n'a pas de `runbook_url` |
| `ALERTE-SANS-RUNBOOK` | erreur | une alerte n'a pas de `docs/runbooks/<Alerte>.md` (sauf si son `runbook_url` pointe vers une doc externe) |
| `RUNBOOK-URL` | avertissement | le `runbook_url` ne pointe pas vers le runbook de l'alerte |
| `RUNBOOK-ORPHELIN` | avertissement | un runbook ne correspond à aucune alerte du repo |
| `CONFIG-VAR` | avertissement | une variable d'env des manifests est absente de `config.md` |
| `CONFIG-SECRET` | avertissement | un Secret référencé dans les manifests est absent de `config.md` |
| `DATE-MANQUANTE` | avertissement | pas de `Dernière revue` ou de date de test |
| `DATE-PERIMEE` | avertissement | dernière revue plus vieille que `--max-age-days` (180 par défaut) |
| `CHECKLIST-VIDE` | avertissement | la checklist n'a pas de cases à cocher |
| `TODO` | info | les marqueurs `TODO(ops-doc)` restants |
| `MERMAID` | info | `architecture.md` n'a pas de schéma |

L'extraction des alertes, des variables et des secrets depuis les manifests se fait par expressions régulières, donc par heuristique. Elle marche sur du YAML Kubernetes classique, Kustomize ou des templates Helm simples. Un faux positif se corrige à la main ; il ne doit pas pousser à déformer la doc.

## 7. Correspondance avec les livrables DAT / DEX

En ESN, chez des clients grands comptes ou dans le public, on demande souvent un **DAT** (Dossier d'Architecture Technique) et un **DEX** (Dossier d'Exploitation), en Word sur le modèle du client. Le contenu est le même :

| Livrable | Fichiers |
|---|---|
| DAT | `architecture.md` + `adr/` + `dimensionnement.md` |
| DEX | `README.md` + `config.md` + `procedures/` + `runbooks/` + `reprise.md` |

```bash
pandoc docs/README.md docs/architecture.md docs/config.md docs/procedures/*.md docs/runbooks/*.md docs/reprise.md \
  -o DEX.docx --reference-doc=modele-client.docx --toc
```
