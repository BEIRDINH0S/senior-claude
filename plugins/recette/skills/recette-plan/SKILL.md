---
name: recette-plan
description: >
  Prépare une recette avant mise en production : stratégie (périmètre, hors périmètre, environnement,
  données de test, rôles, critères d'entrée et de sortie go / no-go), liste des exigences à partir des
  specs, tickets, user stories ou du code, et cas de test précis et exécutables par un autre (données,
  étapes, résultat attendu observable, cas négatifs), avec la traçabilité exigences ↔ cas. Produit un
  cahier de recette Markdown dans recette/, vérifié par script. À utiliser pour « écris le cahier de
  recette », « prépare la recette de la v1.4 », « quels tests métier avant la MEP », « fais les cas de test
  de cette user story ».
---

# recette-plan

Lis d'abord `../recette/references/standard.md` (à partir du dossier de ce skill), puis parcours `../recette/assets/exemple-rdv/` : au moins `strategie.md` et deux cas.

## 1. Rassembler les sources du besoin

- **Les specs, user stories, tickets et notes de version** de la version à recetter : c'est le besoin.
- **Le code** (routes, formulaires, règles de validation, messages d'erreur, tâches planifiées) : il donne les libellés exacts, les valeurs limites et les cas d'erreur à tester. **Le code n'est pas le besoin** : une exigence se formule à partir des specs. Un écart entre les specs et le code est une question pour l'utilisateur, et peut-être déjà une anomalie.
- **`recette/a-tester.md`** : les changements notés pendant le développement. **Chaque entrée sans cas devient un cas**, ou est marquée « hors recette : raison » avec l'accord de l'utilisateur. Remplis la colonne Cas.
- **La version précédente** (`recette/` s'il existe) : les cas de priorité haute deviennent la non-régression. Les cas à rejouer se choisissent par analyse d'impact des changements.

## 2. La stratégie (`recette/strategie.md`)

Depuis `../recette/assets/templates/strategie.md`. Remplis ce que les sources disent. Le reste (qui signe, seuils de go / no-go, date de MEP) relève de **décisions du métier** : laisse-les en `TODO(recette): question`, et pose ces questions à l'utilisateur. En particulier, **les critères de sortie se fixent maintenant, avant l'exécution.** Propose les valeurs par défaut du standard, et fais-les valider.

Écris un **Hors périmètre** explicite. Ce qui n'y figure pas est réputé testé.

Deux sections conditionnent tout le reste :
- **Types de recette** : l'UAT, **mais aussi l'exploitation** (restauration de sauvegarde, retour arrière, supervision), le contractuel ou réglementaire (RGPD, accessibilité), et le non fonctionnel concerné (performance, sécurité, utilisabilité). On oublie souvent l'exploitation, alors que c'est elle qui permet de revenir en arrière si la MEP échoue.
- **Risques produit** : liste ce qui peut mal tourner pour l'utilisateur, avec la probabilité et l'impact. C'est ce qui fixe la priorité des cas et la profondeur des tests. Les entrées de risque « haut » d'`a-tester.md` y figurent.

## 3. Les exigences (`recette/exigences.md`)

- Une ligne par besoin vérifiable, formulée du point de vue de l'utilisateur, avec sa source (ticket, story, paragraphe de spec).
- **Ses critères d'acceptation** : précis, mesurables, vrais ou faux ; sans détail de solution ; non fonctionnels compris. Si les specs ne permettent pas de les écrire, c'est une ambiguïté à lever avec le métier **avant** d'écrire les cas.
- Priorité : **haute** si une panne bloque le métier, **moyenne**, **basse**.
- Découpe les besoins composés : « créer et annuler un rendez-vous » donne deux exigences.

## 4. Les cas de test (`recette/cas/CT-NNN-titre.md`)

Depuis `../recette/assets/templates/cas/_template.md`. Pour chaque exigence :
- **au moins un cas nominal** (le chemin normal) ;
- **les cas négatifs qui comptent** : saisie invalide, champ obligatoire vide, droits insuffisants, valeur limite, action en double, et, si l'exigence le dit, ce qui ne doit pas se passer ;
- pour la sécurité : pas d'information divulguée dans les messages d'erreur, accès refusé sans droits.

**Dérive les cas des critères d'acceptation** avec les techniques du standard (section 7) :
- **partitions d'équivalence** et **valeurs limites** pour les champs et les règles numériques ;
- **tables de décision** pour les combinaisons de règles ;
- **transitions d'états** pour les cycles de vie ;
- **processus métier** pour les parcours.

Pour les zones à risque haut ou mal spécifiées, ajoute une **session exploratoire** (modèle `_template-exploratoire.md` : charte avec but, cible, profil, pistes, durée). Elle complète les cas scriptés, elle ne les remplace pas.

Chaque cas doit pouvoir être exécuté **par quelqu'un qui n'a jamais vu l'application** :
- les **préconditions** : l'état de départ, avec quel compte ;
- les **données** : le compte (sans mot de passe), les valeurs exactes à saisir ;
- les **étapes** : une action par ligne, et **un résultat attendu observable** par étape (libellé exact, valeur, état, message, entrée de journal). Reprends les libellés exacts du code ou des maquettes ;
- un cas = **un objectif** ;
- la priorité du cas suit le niveau de risque et la priorité de l'exigence. Le type est l'un de ceux du standard (fonctionnel, exploitation, securite, performance, exploratoire…).

Ce qu'un résultat attendu n'est **jamais** : « ça fonctionne », « OK », « l'écran s'affiche correctement », « pas d'erreur ». Le script les signale (`CAS-ATTENDU-VAGUE`).

## 5. Vérifier

```bash
python3 <dossier de ce skill>/../recette/scripts/check_recette.py recette/
```
Zéro erreur. En particulier :
- aucun `EXIGENCE-NON-COUVERTE` : chaque exigence a son cas, ou elle passe dans le hors périmètre avec l'accord de l'utilisateur ;
- aucun `CAS-ATTENDU-VAGUE`.

## 6. Rendre la main

Résume en quelques lignes :
- le nombre d'exigences et de cas, par priorité ;
- la matrice de couverture en une ligne par exigence ;
- **les questions ouvertes** : critères de go / no-go, signataire, données de test à créer, écarts entre les specs et le code.

Propose ensuite **recette-run** une fois la version livrée en recette.
