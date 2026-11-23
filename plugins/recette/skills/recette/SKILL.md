---
name: recette
description: >
  Bonnes pratiques de la recette avant une mise en production (MEP) : stratégie, exigences et traçabilité,
  cas de test exécutables par un autre, campagne avec preuves, anomalies qualifiées (bloquante, majeure,
  mineure), go / no-go calculé sur des critères fixés à l'avance, PV de recette avec réserves et
  signatures (vocabulaire MOA / MOE, VABF / VSR). Cahier de recette en Markdown dans le repo, vérifié par
  un script qui propose la décision et génère le PV. Contient le standard, les modèles et un exemple
  utilisés par recette-plan, recette-run et recette-pv. À utiliser dès qu'on parle de recette, de cahier
  de recette, de cas de test métier, de tests d'acceptation (UAT), de PV, de go / no-go, de « valider
  avant la MEP », ou quand un hook demande de compléter recette/a-tester.md, même sans dire recette.
---

# recette

**Une recette sert à décider d'une mise en production sur des preuves, pas sur une impression.** On fixe avant de commencer ce qui est testé et ce qui fera dire « go ». On exécute des cas que n'importe qui peut rejouer, on garde la preuve de chaque résultat, puis on décide avec les chiffres. Les réserves sont écrites, datées et signées.

Laissé à lui-même, un modèle de langage fait l'inverse :
- il écrit « vérifier que la connexion fonctionne », sans données ni résultat attendu ;
- il ne relie rien aux exigences ;
- il note « OK » sans avoir observé le résultat ;
- il conclut « prêt pour la prod » à la place du métier.

Ce plugin existe pour empêcher ça.

## Ressources (dans le dossier de ce skill)

| Chemin | Quand le lire |
|---|---|
| `references/standard.md` | **Avant toute production ou vérification** : vocabulaire, étapes, formats des fichiers, bon cas de test, preuves, sévérités, go / no-go, PV, règles du script |
| `assets/templates/` | Les modèles à copier dans `recette/`, dont `a-tester.md` et un modèle de session exploratoire |
| `assets/exemple-rdv/` | Un cahier de recette complet et conforme : stratégie avec risques produit, 6 exigences avec critères d'acceptation, 8 cas (dont une session exploratoire et un cas d'exploitation), `a-tester.md`, 3 anomalies, une campagne avec ses preuves et son PV. Le lire pour voir le niveau de précision attendu d'un cas |
| `scripts/check_recette.py` | `python3 <ce dossier>/scripts/check_recette.py recette/ [--campagne NOM] [--pv]` : conformité, traçabilité, go / no-go proposé, PV |

Les autres skills `recette-*` accèdent à ces fichiers via `../recette/...`.

## Choisir le bon skill

| Situation | Skill |
|---|---|
| Pendant le développement : noter ce qu'un changement demandera de vérifier | ici même : une ligne dans `recette/a-tester.md` (section 4 du standard). Le hook de commit le rappelle aux agents |
| Préparer une recette : stratégie, exigences, cas de test, à partir de specs, tickets ou du code | **recette-plan** |
| Exécuter une campagne : jouer les cas, capturer les preuves, ouvrir les anomalies | **recette-run** |
| Faire le bilan : vérifier, calculer le go / no-go, produire le PV | **recette-pv** |

## Règles qui valent pour tous les skills recette

- **Ne jamais marquer un cas OK sans avoir observé chaque résultat attendu**, et sans en garder la preuve. Un résultat qu'on n'a pas pu observer donne un cas `bloqué` (avec la raison), jamais `OK`.
- **Ne jamais modifier un résultat attendu pendant l'exécution** pour qu'il colle à ce qu'on observe. Si l'attendu était faux, c'est une correction du cas, signalée à l'utilisateur, et le cas est rejoué.
- **Ne jamais corriger l'application pendant une campagne sans le dire.** Recetter et corriger sont deux rôles. Une correction change la version testée et oblige à rejouer.
- **Ne pas décider à la place des humains.** Le script propose go / no-go à partir des critères. La décision et la signature reviennent au métier.
- **Pas de données personnelles réelles** dans les cas, les preuves ou les captures. Données fictives ou anonymisées, et floutage si un écran en montre.
- **Pas de mot de passe** dans le cahier de recette : le nom du compte, et où trouver le secret.
- **Au fil du développement**, tout changement de comportement visible ajoute sa ligne à `recette/a-tester.md` : ce qu'il faudra vérifier, l'exigence, le risque. Si le hook bloque un commit, choisis « sans impact » seulement si rien ne change pour l'utilisateur. Dans le doute, ajoute la ligne.
