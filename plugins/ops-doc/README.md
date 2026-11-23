# ops-doc

Des skills [Claude Code](https://claude.com/claude-code) pour écrire et maintenir la **documentation d'exploitation** d'une application, surtout sur Kubernetes : fiche service, architecture, config et secrets, dimensionnement, plan de reprise (RPO/RTO), runbooks liés aux alertes, procédures, ADR et post-mortems.

L'objectif d'une telle doc : qu'une personne compétente qui **ne connaît pas l'app** puisse la faire tourner, diagnostiquer une panne et la réparer **sans appeler l'auteur**, même à 3 h du matin.

> *English summary: Claude Code skills to scaffold, import, check and review operational documentation (runbooks, DR plan, ADRs, postmortems) for Kubernetes apps. Skills and templates are written in French; contributions for other languages are welcome.*

## Les skills

Un skill par état de la doc :

| Skill | État de la doc | Ce qu'il fait |
|---|---|---|
| **ops-doc** | n'importe lequel | Le standard commun, les modèles, un exemple complet et le script de vérification. Oriente vers le bon skill |
| **ops-doc-init** | inexistante | Lit le repo (manifests, CNPG, PrometheusRule, ArgoCD, CI) et génère `docs/` avec les vrais noms ; ce qui ne se devine pas devient `TODO(ops-doc): question` |
| **ops-doc-import** | existante mais en vrac (gros README, wiki, Word, notes) | Découpe en informations, les classe, les confronte au repo (obsolète, contradictions, secrets en clair), fait valider le plan, puis écrit les fichiers en gardant la trace de la source |
| **ops-doc-check** | structurée | Conformité au standard (script déterministe), puis cohérence entre la doc et le repo : noms dans les commandes, dimensionnement, checklist qui ne ment pas… |
| **ops-doc-review** | conforme | Relecture du point de vue de l'astreinte : simule chaque runbook, repère les étapes implicites et les commandes dangereuses, propose des réécritures |

```
init ou import  →  check  →  review  →  check à chaque MR
```

## Le standard

```
docs/
├── README.md                 fiche service
├── architecture.md           contexte, conteneurs (Mermaid), flux, données, déploiement, risques
├── config.md                 variables et secrets (les noms, jamais les valeurs)
├── dimensionnement.md        ressources et stockage mesurés, méthode, date de revue
├── reprise.md                RPO/RTO, scénarios, reconstruction complète
├── checklist-production.md   Production Readiness Review
├── runbooks/<Alerte>.md      un par alerte, lié par l'annotation runbook_url
├── procedures/               opérations planifiées
├── adr/NNNN-titre.md         décisions d'architecture
└── postmortems/AAAA-MM-JJ-titre.md
```

Le détail (sections obligatoires, conventions, règles vérifiées) est dans [`skills/ops-doc/references/standard.md`](skills/ops-doc/references/standard.md). Un exemple complet et conforme, pour une app fictive avec CloudNativePG et ArgoCD, se trouve dans [`skills/ops-doc/references/exemple-rdv/`](skills/ops-doc/references/exemple-rdv/README.md).

Les principes :
- la doc vit dans le repo et se relit en MR ;
- une alerte = un runbook ;
- **rien d'inventé** : un chiffre ou une décision inconnue devient un `TODO` ;
- jamais de valeur de secret ;
- des dates de revue.

## Installation

### Comme plugin Claude Code
```
/plugin marketplace add BEIRDINH0S/kube-ops-plugins
/plugin install ops-doc@kube-ops-plugins
```

### À la main
```bash
git clone https://github.com/BEIRDINH0S/kube-ops-plugins.git
mkdir -p ~/.claude/skills
for s in kube-ops-plugins/plugins/ops-doc/skills/*/; do ln -s "$PWD/$s" ~/.claude/skills/; done
```
Les skills doivent rester **côte à côte** : `ops-doc-init`, `-import`, `-check` et `-review` utilisent les ressources de `ops-doc` via `../ops-doc/`.

## Utilisation

Il suffit de demander, les skills se déclenchent tout seuls :
- « Documente cette app pour l'exploitation »
- « Voilà notre vieux wiki d'exploitation, remets-le au propre dans le repo »
- « Vérifie que la doc ops est à jour »
- « Relis les runbooks comme si tu étais d'astreinte »

Ou explicitement : `/ops-doc-init`, `/ops-doc-check`, etc.

### Le script de vérification, sans Claude
Python 3.9+, bibliothèque standard uniquement :
```bash
python3 plugins/ops-doc/skills/ops-doc/scripts/check_docs.py /chemin/du/repo            # docs/ + manifests du repo
python3 plugins/ops-doc/skills/ops-doc/scripts/check_docs.py . --manifests ../gitops    # alertes dans un autre repo
python3 plugins/ops-doc/skills/ops-doc/scripts/check_docs.py . --json                   # pour la CI
```
Code de sortie 1 en cas d'erreur. Exemple de job GitLab CI :
```yaml
ops-doc:
  image: python:3.12-slim
  script:
    - python3 tools/check_docs.py .
  rules:
    - changes: [docs/**/*, "**/*.yaml"]
```

## Garder la doc alignée : les hooks

Une doc mise à jour à la release est fausse : on a oublié le pourquoi, et tout s'accumule. Il faut la mettre à jour **au moment du changement**, surtout quand c'est un agent qui modifie les manifests. Trois niveaux, du plus fin au plus large :

| Moment | Qui | Quoi | Coût |
|---|---|---|---|
| `git commit` | agent Claude | **ops-doc-check** limité au diff : la doc est-elle encore vraie après ce que je viens de changer ? | léger : le contexte est frais, le périmètre petit |
| `git push` | agent Claude | **ops-doc-review** sur ce qui part : la doc tient-elle à 3 h du matin ? | une fois par lot, sur un état cohérent |
| commit (tous) / MR (CI) | tout le monde | `check_docs.py`, déterministe, sans IA | quelques secondes : c'est le filet de sécurité |

**Pourquoi la review n'a pas lieu à chaque commit :** les commits intermédiaires (WIP, fixup, squash) ne survivent pas, et la qualité d'un runbook s'apprécie sur un changement complet. Relire à chaque commit, ce serait payer plusieurs fois pour des états jetables.

### Hook agent (Claude Code)
Il est livré avec le plugin (`hooks/hooks.json`) et s'active à l'installation. Il intercepte les `git commit` et `git push` de l'agent, et ne se déclenche que si :
- le repo a adopté le standard (`docs/README.md` et `docs/runbooks/`) ;
- des fichiers d'exploitation sont concernés (`docs/`, `*.yaml`, `Dockerfile*`, `.gitlab-ci.yml`).

L'agent est alors bloqué avec la consigne de lancer le skill adapté et de mettre la doc à jour. Il enregistre ensuite son rapport (`agent_commit_gate.py mark commit|push --report …`). L'enregistrement est lié à l'**empreinte exacte** des changements : toute modification faite après coup oblige à recommencer.

Installation manuelle sans le plugin, dans `~/.claude/settings.json` :
```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python3 /chemin/kube-ops-plugins/plugins/ops-doc/hooks/agent_commit_gate.py", "timeout": 60 }] }
    ]
  }
}
```

> Ce n'est pas un contrôle inviolable : un agent pourrait enregistrer une review sans la faire. C'est un rappel au bon moment, et la CI sert de filet de sécurité.

### Hook git (tout le monde)
```bash
ln -s /chemin/kube-ops-plugins/plugins/ops-doc/hooks/git-pre-commit .git/hooks/pre-commit
```
Ou avec le framework [pre-commit](https://pre-commit.com) :
```yaml
repos:
  - repo: https://github.com/BEIRDINH0S/kube-ops-plugins
    rev: main
    hooks:
      - id: ops-doc-check
```

## Contribuer

Les contributions sont bienvenues : nouvelles règles, autres outils (Helm, Flux, Velero, Sealed Secrets…), traductions, retours d'expérience. Voir [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Licence

[MIT](../../LICENSE)
