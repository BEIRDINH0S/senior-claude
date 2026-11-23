---
name: ops-doc-import
description: >
  Transforme une documentation d'exploitation existante mais désorganisée en doc ops structurée dans
  docs/ : gros README fourre-tout, export de wiki ou de Confluence, notes, page Notion, fichier Word
  (DEX, manuel d'exploitation), fil de discussion d'incident. Repère chaque information utile, la classe
  (fiche service, config, runbook, procédure, ADR, post-mortem…), la confronte à l'état réel du repo pour
  repérer ce qui est obsolète ou contradictoire, puis crée les fichiers en gardant la trace de la source.
  À utiliser quand on demande de « remettre au propre la doc », « migrer le wiki dans le repo »,
  « restructurer la doc d'exploitation », « récupérer les infos de ce document pour faire les runbooks »,
  ou dès qu'une doc ops existe mais ne suit pas le standard ops-doc.
---

# ops-doc-import : de la doc en vrac vers le standard

Le but : **rien d'utile ne se perd, rien de faux n'est recopié**. Une vieille doc mélange le vrai, l'obsolète et le jamais-vrai ; recopier le tout tel quel donnerait une doc propre en apparence, mais fausse.

Avant de commencer, lis `../ops-doc/references/standard.md` (à partir du dossier de ce skill), en particulier « Contenu attendu » et « Runbook ou procédure ? ».

## 1. Rassembler les sources

- Liste les sources avec l'utilisateur : fichiers du repo, export de wiki, page Notion ou Confluence (par l'outil connecté s'il existe), fichiers Word ou PDF.
- **Word** : `pandoc fichier.docx -t gfm -o /tmp/<nom>.md` si pandoc est installé, sinon le skill docx s'il existe, sinon demande un export en Markdown ou en texte.
- **Ne modifie jamais les sources.** On les supprime seulement à la fin, sur demande explicite.
- Note pour chaque source sa date de dernière modification (git log, métadonnées) : c'est un premier indice d'obsolescence.

## 2. Extraire et classer

Lis tout, puis découpe en **informations atomiques** : une info = un fait, une commande, une consigne ou une décision. Classe chacune avec la grille de `references/classification.md` (dans le dossier de ce skill).

Construis la table de correspondance :

| # | Information (résumé) | Source (fichier:ligne) | Cible (fichier > section) | Confiance |
|---|---|---|---|---|
| 1 | Redémarrer l'API si les connexions PG saturent | wiki/ops.md:42 | runbooks/RdvHighErrorRate.md > Remédiation | moyenne : aucune alerte nommée dans la source |

Confiance **haute** = sans ambiguïté, **moyenne** = classement interprété, **basse** = info douteuse ou peut-être obsolète.

## 3. Confronter au repo

Si les manifests sont accessibles, vérifie chaque fait vérifiable : noms de ressources, réplicas, versions, variables, secrets, alertes, URLs, commandes. Ensuite :

- **Contradiction** (la doc dit 3 réplicas, le manifest en a 2) → c'est le repo qui décrit ce qui tourne **maintenant**. Mets la valeur du repo dans la doc, et note la contradiction dans le rapport : parfois c'est le repo qui a tort, et seul l'humain peut le dire.
- **Obsolète** (le composant cité n'existe plus) → ne pas importer, mais lister dans le rapport.
- **Commande** : adapte les noms de ressources à l'état actuel, et signale chaque adaptation.
- **Secret en clair dans la source** → ne pas le recopier. Le signaler **en premier** dans le rapport : il est à faire tourner, et la source est à nettoyer.

Repère aussi les **doublons** (la même procédure à deux endroits, avec des variantes) : garde la version la plus récente ou la plus complète, et signale les écarts.

## 4. Faire valider le plan

Avant d'écrire, montre à l'utilisateur :
- la table de correspondance (ou un résumé par fichier cible si elle dépasse une cinquantaine de lignes) ;
- les contradictions et les infos obsolètes ;
- ce qui n'a pas trouvé de place ;
- les fichiers du standard pour lesquels la source ne dit rien.

Attends son feu vert : le classement comporte des choix d'interprétation, et une contradiction ne se tranche qu'avec lui. Si l'utilisateur a dit de tout faire sans s'arrêter, va jusqu'au bout et mets ces points dans le rapport final.

## 5. Écrire

- Pars des modèles `../ops-doc/assets/templates/`. Réécris les infos dans la structure : on reformule pour la clarté, mais on n'ajoute rien qui ne soit ni dans la source ni dans le repo.
- **Traçabilité** : après chaque bloc importé, un commentaire `<!-- source: wiki/ops.md:42-58 -->`. Il est invisible au rendu et permet de remonter à l'original pendant la relecture. L'utilisateur pourra les retirer plus tard.
- Les trous restent en `TODO(ops-doc): <question>`.
- Une alerte connue mais absente des manifests (citée dans la vieille doc) → pas de runbook créé. Signale-la : soit l'alerte a disparu, soit elle vit ailleurs.
- Écris le rapport d'import dans `docs/_import-rapport.md`. Le `_` le fait ignorer par le script ; il est à supprimer une fois traité. Il contient : sources, table de correspondance, contradictions, obsolète, non classé, secrets trouvés, trous.

## 6. Vérifier et rendre la main

```bash
python3 <dossier de ce skill>/../ops-doc/scripts/check_docs.py <repo>
```
Corrige les erreurs qui viennent de l'import. Puis résume en quelques lignes : combien d'infos importées, combien écartées et pourquoi, les contradictions à trancher, les secrets à faire tourner, les questions ouvertes. Propose ensuite **ops-doc-review**.
