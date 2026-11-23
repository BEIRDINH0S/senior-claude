---
name: ops-doc-review
description: >
  Relecture qualitative d'une doc d'exploitation (runbooks, procédures, plan de reprise, fiche service,
  ADR, post-mortems) du point de vue de l'astreinte : quelqu'un qui ne connaît pas l'app, réveillé à
  3 h du matin, peut-il diagnostiquer et réparer avec cette doc seule ? Simule le déroulé de chaque
  runbook, vérifie que les commandes sont justes et copiables, repère les étapes implicites, les commandes
  dangereuses sans garde-fou, les retours arrière manquants, le savoir détenu par une seule personne. Rend
  des constats priorisés avec des réécritures proposées. À utiliser pour « relis ma doc », « review des
  runbooks », « est-ce que c'est exploitable », « prépare-moi pour l'astreinte », ou après ops-doc-check.
---

# ops-doc-review : la doc tient-elle à 3 h du matin ?

**ops-doc-check** répond à « est-ce conforme ? ». Ici, on répond à « est-ce que ça marche ? ». Une doc peut avoir toutes ses sections et laisser l'astreinte sans solution, parce qu'il manque l'étape que l'auteur fait de mémoire.

## Le point de vue à adopter

Relis en te mettant à la place de **l'ingénieur d'astreinte** : compétent sur Kubernetes, Postgres et Prometheus, mais qui **n'a jamais vu cette app**. Il a été réveillé par une alerte, et l'auteur ne répond pas. Il a la doc, un terminal et les accès décrits. À chaque phrase, demande-toi s'il peut agir avec ce qui est écrit, ou s'il lui manque quelque chose que seul l'auteur sait.

## 1. Point de départ

Lance d'abord le script de conformité :
```bash
python3 <dossier de ce skill>/../ops-doc/scripts/check_docs.py <repo>
```
S'il y a beaucoup d'erreurs structurelles, dis-le et propose de passer par **ops-doc-check** ou **ops-doc-import** d'abord : relire le fond d'une doc à qui il manque la moitié des fichiers n'a pas de sens. S'il y a quelques erreurs, mentionne-les brièvement et continue.

## 2. Relire, fichier par fichier

La grille détaillée est dans `references/grille.md` (dans le dossier de ce skill). L'ordre suit l'importance pour l'astreinte :

1. **Les runbooks : simule-les.** Pour chacun, imagine que l'alerte vient de sonner et déroule le diagnostic dans l'ordre :
   - chaque commande peut-elle se copier-coller telle quelle (vrais noms, bon namespace, pas de `<placeholder>` laissé sans explication) ?
   - est-elle **syntaxiquement juste** (kubectl, plugin `kubectl cnpg`, argocd CLI, PromQL, LogQL, SQL) ? En cas de doute sur une option, vérifie-la (`--help`, doc officielle) plutôt que de l'affirmer ;
   - pour chaque résultat possible d'une étape, la doc dit-elle quoi faire ensuite ? Un diagnostic qui s'arrête sur « regarder les logs » sans dire quoi chercher laisse l'astreinte sans suite ;
   - la remédiation couvre-t-elle les causes listées au diagnostic ?
   - « Vérifier que c'est résolu » est-il observable ?
   - l'escalade dit-elle **qui** et **à partir de quand** ?
2. **Les procédures** : les prérequis sont-ils complets ? Les étapes risquées sont-elles signalées ? Le retour arrière fonctionne-t-il **à chaque étape**, et le point de non-retour est-il clairement marqué ?
3. **reprise.md** : le paradoxe du bootstrap. Tout ce qui sert à reconstruire (clé de déchiffrement, kubeconfig, credentials S3, accès Git) est-il disponible **hors du cluster perdu** ? Les durées viennent-elles d'un vrai test ?
4. **README.md** : en 30 secondes, sait-on ce que fait l'app, à quel point c'est grave, qui appeler et où regarder ?
5. **architecture.md, config.md, dimensionnement.md** : sont-ils compréhensibles sans l'auteur ? Les chiffres sont-ils justifiés ?
6. **ADR et post-mortems** : les options écartées et les conséquences sont-elles réelles ? Les post-mortems sont-ils sans blâme, avec des actions suivies ?

Pour finir, une **lecture transversale** :
- quelqu'un d'autre que l'auteur peut-il intervenir (le savoir détenu par une seule personne) ?
- les alertes qu'on attendrait pour cette archi existent-elles ? Par exemple, pas d'alerte sur l'archivage WAL alors qu'il y a CNPG ;
- la doc et le repo racontent-ils la même histoire ?

## 3. Le rendu

Classe chaque constat :
- **Bloquant** : à 3 h du matin, l'astreinte reste coincée ou aggrave la situation. Commande fausse, étape manquante, commande destructrice sans avertissement, clé de reprise uniquement dans le cluster.
- **Important** : l'astreinte s'en sort, mais lentement ou en devinant.
- **Suggestion** : plus clair, plus rapide, plus robuste.

````markdown
# Review ops-doc : <repo> (<date>)

**Résumé** : 3 à 5 lignes. La doc permet-elle de tenir une astreinte aujourd'hui ? Les deux ou trois priorités.

## Bloquant
### runbooks/RdvApiDown.md:42 : titre du constat
**Problème** : ce qui coince, du point de vue de l'astreinte.
**Proposition** :
```diff
- ancienne ligne
+ nouvelle ligne
```

## Important
## Suggestions
## Ce qui est bien fait
Deux ou trois points, concrets. Ça indique ce qu'il faut conserver.
````

Chaque constat cite le fichier et la ligne, et propose une **réécriture concrète**, pas seulement « à améliorer ». Si une proposition demande une info que tu n'as pas, formule-la comme une question (« quel est le délai d'escalade ? ») plutôt que de l'inventer.

Ne modifie pas la doc sans qu'on te le demande. Si l'utilisateur dit d'appliquer, applique les blocs validés, relance le script, puis récapitule ce qui a changé.
