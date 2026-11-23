# Ce qui fait une bonne capture de documentation

> Une capture sert à **montrer où agir**. Le texte dit **quoi faire et pourquoi**. Si une capture a besoin d'un paragraphe d'explication pour être comprise, elle montre trop de choses.

## 1. Une capture = une idée
- Une étape, ou un écran présenté. Pas trois actions sur la même image.
- **Recadrer** sur la zone utile (un formulaire, un panneau) plutôt que l'écran entier. L'écran entier est réservé à la vue d'ensemble, quand on présente la structure d'une page.
- Garder assez de contexte autour pour que le lecteur se repère : le titre de la carte, la barre au-dessus.

## 2. Numéroter plutôt qu'écrire
- **Des pastilles numérotées** ①②③ qui renvoient aux étapes numérotées du texte. Le texte est traduisible, recherchable et accessible ; le texte incrusté dans une image ne l'est pas.
- Au maximum **4 ou 5 numéros** par image. Au-delà, il faut découper.
- **Les notes incrustées** (« Valider ») sont l'exception : quelques mots, quand l'action n'est pas évidente.
- **La flèche** sert quand la cible est petite ou noyée dans un ensemble (un bouton dans une ligne de tableau). Sinon, un cadre suffit.
- **La mise en lumière** (`spotlight`) isole un élément dans un écran chargé, sans ajouter de texte.

## 3. Une seule couleur, toujours la même
- Une couleur d'annotation dans toute la doc (rouge `#E5484D` par défaut), contrastée avec l'interface. Si l'app est déjà rouge, choisir une autre couleur et s'y tenir partout.
- Pas d'arc-en-ciel : le lecteur cherche « le rouge » sans réfléchir.

## 4. Des données de démo, jamais de vraies données
- Un compte et un jeu de données de démonstration réalistes : des noms plausibles, des dates cohérentes, aucun « test test » ni « aaaa ».
- **Flouter** (`blur`) tout ce qui reste sensible : e-mails, noms, téléphones, adresses, jetons, identifiants internes. Le floutage se fait dans la page, avant la capture, donc la donnée n'existe pas en clair dans le PNG.
- Ne jamais capturer la prod avec des données réelles, même floutées : un flou partiel ou un oubli suffit à exposer quelqu'un.

## 5. Cohérence entre toutes les images
- **Même taille de fenêtre** pour toutes les captures (`viewport` dans `defaults`), en **échelle 2** (retina) pour la netteté.
- **Même thème** (`color_scheme: light` en général), même langue, même compte de démo.
- **Même état** de l'app : pas de notifications parasites, de bandeau de cookies ou de chat ouvert. Les fermer dans `steps`.

## 6. Nommage et emplacement
```
docs/
├── img/
│   ├── connexion-1-formulaire.png      <page>-<étape>-<sujet>.png
│   └── agenda-2-annuler.png
└── captures/
    ├── connexion.json                  recette qui produit les images
    └── auth.json                       état de connexion (gitignoré)
```
On commite la recette avec les images : quand l'interface change, on relance `capture.py`, sans rien refaire à la main.

## 7. Dans le texte
```markdown
1. Saisissez votre adresse dans le champ **E-mail** ①.
2. Cliquez sur **Se connecter** ②.

![Formulaire de connexion : champ E-mail (1) et bouton Se connecter (2)](img/connexion-1-formulaire.png)
```
- Le **texte alternatif** décrit ce que montre l'image, numéros compris : il sert aux lecteurs d'écran, et quand l'image ne charge pas.
- Les libellés de l'interface sont en **gras**, et écrits exactement comme à l'écran.
