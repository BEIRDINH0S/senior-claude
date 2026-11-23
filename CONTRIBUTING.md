# Contribuer

Merci de votre intérêt. Quelques repères pour que les contributions restent cohérentes.

## Organisation

```
.claude-plugin/          manifestes du plugin et de la marketplace
skills/
├── ops-doc/             standard, modèles, exemple et script partagés
│   ├── SKILL.md
│   ├── references/standard.md      ← la source de vérité
│   ├── references/exemple-rdv/     ← exemple conforme
│   ├── assets/templates/           ← modèles copiés dans docs/
│   └── scripts/check_docs.py
├── ops-doc-init/
├── ops-doc-import/
├── ops-doc-check/
└── ops-doc-review/
hooks/
├── hooks.json           hook PreToolUse du plugin (commit/push des agents)
├── agent_commit_gate.py logique du hook + commande `mark`
└── git-pre-commit       hook git classique (script déterministe)
tests/
├── fixture-repo/        faux repo avec des erreurs volontaires
├── test_check_docs.py
└── test_agent_gate.py   hook agent, sur des repos git temporaires
```

## Règles

1. **Le standard d'abord.** Toute nouvelle exigence (section, champ, règle) s'écrit dans `references/standard.md`, puis dans les modèles, l'exemple et le script. Les quatre doivent rester alignés.
2. **L'exemple reste conforme.** La CI vérifie que `check_docs.py` ne remonte aucune erreur ni aucun avertissement sur `exemple-rdv/`.
3. **Le script reste sans dépendance.** Bibliothèque standard Python uniquement, pour qu'il tourne partout, y compris dans une image CI minimale.
4. **Chaque règle a son test.** Ajoutez le cas fautif dans `tests/fixture-repo/` et l'assertion dans `tests/test_check_docs.py`. Ajoutez aussi un test qui vérifie l'absence de faux positif quand la règle est heuristique.
5. **Des skills qui expliquent le pourquoi.** Dans un `SKILL.md`, expliquez la raison d'une consigne plutôt que d'empiler des « TOUJOURS / JAMAIS » : le modèle s'adapte mieux aux cas imprévus quand il comprend l'intention.
6. **Pas de données réelles.** Exemples et fixtures sont fictifs : aucun nom, domaine ou secret réel.

## Tester

```bash
python3 -m unittest discover tests -v
```

Pour tester un skill dans Claude Code, installez votre copie locale (voir l'installation manuelle dans le README), puis lancez-le sur un vrai repo ou sur `tests/fixture-repo/`.

## Idées bienvenues

- Support de Helm (lecture des `values.yaml`), de Flux, de Velero, de Sealed Secrets et d'External Secrets dans `ops-doc-init`
- Traduction anglaise des skills et des modèles
- Nouvelles règles du script : runbook_url vers la bonne branche, labels recommandés sur les workloads…
- Retours d'usage : ce qui a manqué pendant un vrai incident
