---
name: recette-run
description: >
  Exécute une campagne de recette : joue les cas de test du cahier sur l'environnement de recette
  (navigateur via agent-browser, API, base, journaux), observe chaque résultat attendu, capture une
  preuve par cas (capture annotée, log, réponse), note OK / KO / bloqué, ouvre et qualifie les anomalies
  (bloquante, majeure, mineure), re-teste les corrections, sans jamais marquer OK un résultat non observé.
  À utiliser pour « lance la recette », « exécute les cas de test », « rejoue la campagne sur la rc3 »,
  « re-teste l'anomalie AN-001 ».
---

# recette-run

Lis `../recette/references/standard.md`, sections 7 et 8, à partir du dossier de ce skill.

## 0. Avant de commencer

- **Les critères d'entrée** de `recette/strategie.md` sont-ils remplis : version déployée, données en place ? S'ils ne le sont pas, dis-le et n'exécute pas. Une campagne sur une mauvaise version ne vaut rien.
- **La version réellement déployée** : vérifie-la (page « à propos », `/version`, en-tête HTTP, tag d'image) plutôt que de la supposer.
- **L'environnement** : jamais la prod. Si l'URL fournie ressemble à la prod, arrête-toi et demande.
- **Crée la campagne** `recette/campagnes/AAAA-MM-JJ-vX.Y.Z/` depuis le modèle, avec la version et l'environnement constatés.
- **agent-browser**, pour les cas dans le navigateur : `command -v agent-browser`. S'il est absent, propose de l'installer (`brew install agent-browser` ou `npm install -g agent-browser`, puis `agent-browser install`) et attends l'accord de l'utilisateur. Si l'utilisateur refuse, les cas web sont exécutés par lui, et toi tu tiens la campagne.

## 1. Jouer un cas

Pour chaque cas, de priorité haute d'abord :
1. **Mets en place les préconditions et les données** exactement comme le cas le dit.
2. **Pour chaque étape** : fais l'action, puis **observe le résultat** et compare-le **mot pour mot** au résultat attendu.
   - Dans le navigateur : `agent-browser --session recette ...` (`open`, `fill`, `click`, puis `snapshot -i`, `get text <sel>` ou `wait --text "…"` pour observer).
   - Une API : la requête et la réponse complète (code et corps).
   - En base ou dans un journal : la requête de lecture et son résultat. **Lecture seule** : on ne modifie pas les données pour faire passer un cas.
3. **Statut** :
   - `OK` : **tous** les résultats attendus ont été observés ;
   - `KO` : au moins un résultat diffère. Note **le résultat obtenu**, puis ouvre ou référence une anomalie ;
   - `bloqué` : impossible à exécuter (une autre anomalie, l'environnement, des données absentes). Note la raison ;
   - `non exécuté` : pas joué dans cette campagne. Note pourquoi.
4. **La preuve** dans `preuves/` : elle montre le **résultat obtenu**. Une capture annotée qui montre le message ou l'état attendu ; si le plugin **doc-screenshots** est installé, sa recette de capture permet le cadrage, le numéro et le floutage. Sinon : `agent-browser screenshot preuves/CT-NNN.png`, un fichier `.txt` avec la requête et la réponse, ou un extrait de log.
5. **La ligne d'exécution** dans `campagne.md` : cas, statut, testeur, date, anomalie, lien vers la preuve.

Si le cas lui-même est faux (attendu impossible, étape ambiguë), **ne l'adapte pas en silence**. Note-le, signale-le à l'utilisateur, corrige le cas avec son accord, puis rejoue-le.

## 2. Ouvrir une anomalie (`recette/anomalies.md`)

- Un titre qui dit **ce qui ne va pas**, pas ce qu'on a fait : « Annulation : le SMS n'est pas envoyé ».
- **La sévérité selon l'impact métier** (standard, section 8). Elle n'a rien à voir avec la difficulté de correction. En cas de doute entre deux niveaux, propose et laisse le métier trancher.
- Le contournement, s'il en existe un : c'est ce qui sépare une majeure d'une bloquante.
- Le cas concerné, le statut `ouverte`, une échéance si elle est connue, le ticket s'il existe. Pour créer le ticket, utilise le skill de l'outil de tickets, s'il y en a un, avec l'accord de l'utilisateur.
- Dans la description du ticket : les étapes pour reproduire, l'attendu, l'obtenu, la version, la preuve.

## 3. Re-tester une correction

Quand une anomalie passe en `corrigée` : vérifie la nouvelle version déployée, **rejoue le cas en entier** (pas seulement l'étape fautive), avec une nouvelle preuve. Ensuite :
- c'est bon : l'anomalie passe en `fermée`, et la ligne de campagne est mise à jour (version et date dans les notes) ;
- c'est toujours KO : l'anomalie reste ouverte, avec un commentaire.

Rejoue aussi les cas de priorité haute touchés par la correction : la non-régression.

## 4. Vérifier et rendre la main

```bash
python3 <dossier de ce skill>/../recette/scripts/check_recette.py recette/ --campagne <nom>
```
Corrige les erreurs de forme : preuve manquante, KO sans anomalie. Puis résume :
- les OK, KO, bloqués et non exécutés ;
- les anomalies ouvertes par sévérité ;
- la décision que **proposent** les critères.

Propose **recette-pv** pour le bilan.
