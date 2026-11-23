# Contribuer

Merci de votre intérêt. Quelques repères pour que l'ensemble reste cohérent.

## Organisation

```
.claude-plugin/marketplace.json   catalogue : une entrée par plugin
.github/workflows/tests.yml       lance les tests de chaque plugins/*/tests
.pre-commit-hooks.yaml            hooks exposés au framework pre-commit
plugins/<nom>/
├── .claude-plugin/plugin.json    nom, version, description du plugin
├── skills/                       un dossier par skill (SKILL.md + ressources)
├── hooks/                        hooks.json + scripts (facultatif)
├── tests/                        tests unittest, bibliothèque standard
└── README.md
```

## Règles communes

1. **Un plugin = un problème** qu'on peut nommer en une phrase, et quelque chose qui s'exécute. Un texte de bonnes pratiques seul n'est pas un plugin.
2. **Des plugins autonomes** : pas de dépendance entre plugins, chacun embarque ses scripts.
3. **Des scripts sans dépendance** : bibliothèque standard Python uniquement, pour qu'ils tournent partout, y compris dans une image CI minimale.
4. **Chaque règle a son test**, avec un test de non-faux-positif quand la règle est heuristique.
5. **Des skills qui expliquent le pourquoi** plutôt que d'empiler des « TOUJOURS / JAMAIS » : le modèle s'adapte mieux aux cas imprévus quand il comprend l'intention.
6. **Pas de données réelles** : exemples et fixtures sont fictifs, sans nom, domaine ni secret réel.
7. **Versionner** : on monte la `version` du `plugin.json` à chaque changement de comportement.

## Tester

```bash
for t in plugins/*/tests; do python3 -m unittest discover -s "$t"; done
claude plugin validate plugins/<nom>
```

## Règles propres à ops-doc

- Le standard (`skills/ops-doc/references/standard.md`) est la source de vérité. Une nouvelle exigence s'écrit d'abord là, puis dans les modèles, l'exemple et le script.
- L'exemple `exemple-rdv/` reste sans erreur ni avertissement (vérifié en CI).
- Une règle du script = un cas fautif dans `tests/fixture-repo/` + une assertion.

## Ajouter un plugin

1. Créer `plugins/<nom>/` en suivant l'organisation ci-dessus.
2. L'ajouter au catalogue `.claude-plugin/marketplace.json`.
3. Ajouter une ligne au tableau du README racine.
