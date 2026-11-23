---
name: doc-screenshots
description: >
  Produit des captures d'écran annotées et reproductibles pour une documentation, un guide utilisateur,
  un tutoriel ou les preuves d'un cahier de recette, avec agent-browser : étapes numérotées, cadres,
  notes, flèches, mise en lumière, floutage des données personnelles, recadrage, en retina. Les
  annotations sont dessinées DANS la page et ancrées sur de vrais éléments (sélecteurs CSS), donc
  placées au pixel près, et une « recette de capture » versionnée permet de tout régénérer quand
  l'interface change. À utiliser dès qu'il faut des captures pour une doc (« fais les screenshots du
  guide », « illustre cette procédure », « capture l'écran avec des flèches », « mets à jour les
  images de la doc »), même sans dire doc-screenshots.
---

# doc-screenshots

**Ne jamais « dessiner » sur une image.** Un modèle qui place une flèche sur un PNG devine les coordonnées à l'œil, et elle tombe à côté. Ici, les annotations sont injectées **dans la page** avant la capture, ancrées sur des éléments réels. Elles tombent juste, quelle que soit la mise en page, et une recette de capture régénère toutes les images quand l'interface change.

## 0. Prérequis : agent-browser

```bash
command -v agent-browser && agent-browser --version
```
S'il est absent, **demande avant d'installer** : ça modifie la machine et télécharge environ 190 Mo de Chrome. Ensuite, au choix :
```bash
brew install agent-browser          # macOS / Linux avec Homebrew
npm install -g agent-browser        # ou via npm
agent-browser install               # dans les deux cas : télécharge Chrome for Testing (une fois)
```
`capture.py` a été testé avec agent-browser 0.43. Le script n'a besoin d'aucune dépendance Python.

## Ressources (dans le dossier de ce skill)

| Chemin | Rôle |
|---|---|
| `references/style.md` | **À lire avant de produire des captures** : ce qui fait une bonne capture de doc (cadrage, numérotation, une seule couleur, données de démo, floutage, texte alternatif, nommage) |
| `scripts/capture.py` | Lance une recette de capture : `python3 <ce dossier>/scripts/capture.py <recette.json> [--only nom] [--dry-run] [--keep-open]` |
| `scripts/annotate.js` | Le calque d'annotations injecté dans la page. Placement automatique qui évite les collisions avec le contenu, les autres cadres et les bords |
| `assets/demo/` | Une page de démo et sa recette (`captures.json`) : à lire comme exemple de recette complète |
| `assets/exemples/` | Le résultat : vue d'ensemble numérotée, étapes avec notes, mise en lumière avec flèche |

## Démarche

1. **Lire `references/style.md`.** Décider ce que chaque capture doit montrer : **une capture = une idée** (un écran, une étape).
2. **Accès à l'app** : URL locale ou de staging, jamais la prod avec de vraies données. Si l'app demande une connexion, crée un état d'authentification une fois :
   ```bash
   agent-browser --session doc open <url-de-login>     # se connecter avec un compte de démo
   agent-browser --session doc state save docs/captures/auth.json
   ```
   `auth.json` contient des cookies de session : ajoute-le au `.gitignore`.
3. **Trouver les sélecteurs** : `agent-browser --session doc snapshot -i` (arbre d'accessibilité) ou le code source. On préfère les sélecteurs stables : `id`, `data-testid`, attributs `name` ou `aria-label`. On évite les classes générées (`.css-1x2y3z`) et les `nth-child` fragiles.
4. **Écrire la recette** `docs/captures/<page>.json`, à partir de `assets/demo/captures.json`. Options :
   - `viewport [l, h, échelle]` ;
   - `wait`, `steps` (commandes agent-browser pour arriver à l'écran : `click`, `fill`, `press`…) ;
   - `annotations` : `box` (défaut), `spotlight`, `arrow`, `blur`, avec `label` (numéro), `note`, et éventuellement `side` / `badge` pour forcer un placement ;
   - `crop` : `true` (autour des annotations), un sélecteur (le conteneur, élargi aux annotations) ou `false` (écran entier) ;
   - `output`.
5. **Lancer et regarder chaque image** (`Read` sur le PNG). Si une pastille ou une note gêne malgré le placement automatique, force la position avec `badge` (`left`, `top-left`, `top`, `right`, `inside`) ou `side` (`right`, `left`, `top`, `bottom`). Si un sélecteur est introuvable, le script échoue et le nomme : corrige le sélecteur, n'ignore pas l'erreur.
6. **Intégrer dans la doc** : chaque numéro de l'image correspond à une étape numérotée du texte, avec un texte alternatif qui dit ce que montre l'image. Commite la recette avec les images.

## Pièges connus (constatés)

- **Le cache de session** : une session agent-browser réutilisée peut resservir une ancienne version de la page. Après une modification de l'app, `agent-browser --session <nom> close`, puis relancer.
- **L'ordre ouvrir / redimensionner** : `capture.py` ouvre la page **avant** de régler la fenêtre, parce que l'inverse produit des captures en mosaïque sur une session neuve. Si tu pilotes agent-browser à la main, garde cet ordre.
- **Les éléments en `position: fixed`** (bandeaux de cookies, chat) : ferme-les dans `steps`, ou masque-les par un `eval`, avant d'annoter.

## Rendre la main

Liste les images produites, avec ce que montre chacune et les numéros utilisés, pour que le texte de la doc s'y réfère. Donne la commande pour les régénérer. Signale les données sensibles que tu as floutées, et celles que tu n'as pas pu flouter.
