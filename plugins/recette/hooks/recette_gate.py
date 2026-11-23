#!/usr/bin/env python3
"""Hook Claude Code : alimenter la liste « à tester en recette » au fil du développement.

Quand un agent committe un changement de code applicatif dans un repo qui a un
dossier recette/, le commit ne passe que si :
  - recette/a-tester.md (ou un cas de recette/cas/) est modifié dans le même commit :
    on y a noté ce qu'il faudra vérifier en recette, ou « hors recette : raison » ;
  - OU le message de commit contient « Recette: sans impact (raison) », trace dans git log.

C'est le « tester tôt » : ce qu'il faudra vérifier est noté au moment où le changement
est connu, pas reconstitué de mémoire la veille de la recette.

Ce qui ne compte pas comme code : recette/, docs/, Markdown, tests, fichiers de lock,
CI, images. Réglable par projet dans recette/.recette.json :
  { "code": ["src/*", "app/*"],      seuls ces chemins comptent (globs fnmatch)
    "ignore": ["scripts/*"] }        chemins ignorés en plus

Mode : hook PreToolUse (JSON sur stdin). Code 2 = commit bloqué, message pour l'agent.
Bibliothèque standard uniquement.
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

COMMIT_RE = re.compile(r"(?:^|[;&|(]\s*|\s)git(?:\s+-C\s+\S+)?(?:\s+-c\s+\S+)*\s+commit\b")
SANS_IMPACT_RE = re.compile(r"recette\s*:\s*sans impact", re.I)
DEFAULT_IGNORE = [
    "recette/*", "docs/*", "*.md", "*.txt", "LICENSE*",
    "test/*", "tests/*", "*/test/*", "*/tests/*", "*/__tests__/*", "e2e/*", "*/e2e/*",
    "*.test.*", "*.spec.*", "*_test.go", "test_*.py", "*/test_*.py",
    "*.lock", "package-lock.json", "*/package-lock.json", "yarn.lock", "pnpm-lock.yaml", "go.sum",
    ".github/*", ".gitlab-ci.yml", ".gitlab/*", ".gitignore", ".editorconfig", ".prettierrc*", ".eslintrc*",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.ico",
]


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout


def repo_root(start: Path) -> Path | None:
    try:
        return Path(git(start, "rev-parse", "--show-toplevel").strip())
    except (RuntimeError, FileNotFoundError, NotADirectoryError):
        return None


def target_dir(command: str, cwd: Path) -> Path:
    for rx in (r"^\s*cd\s+(\S+)\s*&&", r"\bgit\s+-C\s+(\S+)"):
        m = re.search(rx, command)
        if m:
            p = Path(shlex.split(m.group(1))[0]).expanduser()
            cwd = p if p.is_absolute() else cwd / p
    return cwd


def changed_files(repo: Path) -> list[str]:
    """Ce que le commit va enregistrer : index + arbre de travail vs HEAD (couvre commit -a)."""
    has_head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "-q", "HEAD"],
                              capture_output=True).returncode == 0
    args = ["diff", "HEAD", "--name-only"] if has_head else ["diff", "--cached", "--name-only"]
    return [f for f in git(repo, *args).splitlines() if f]


def load_config(repo: Path) -> dict:
    p = repo / "recette" / ".recette.json"
    try:
        return json.loads(p.read_text()) if p.is_file() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def is_code(path: str, cfg: dict) -> bool:
    if cfg.get("code"):
        if not any(fnmatch(path, g) for g in cfg["code"]):
            return False
    ignore = DEFAULT_IGNORE + cfg.get("ignore", [])
    return not any(fnmatch(path, g) for g in ignore)


def gate(command: str, cwd: Path) -> int:
    repo = repo_root(target_dir(command, cwd))
    if not repo or not (repo / "recette").is_dir():
        return 0
    files = changed_files(repo)
    cfg = load_config(repo)
    code = [f for f in files if is_code(f, cfg)]
    if not code:
        return 0
    if any(f == "recette/a-tester.md" or f.startswith("recette/cas/") for f in files):
        return 0
    if SANS_IMPACT_RE.search(command):
        return 0

    liste = "\n".join(f"  - {f}" for f in code[:15]) + (f"\n  … et {len(code) - 15} autre(s)" if len(code) > 15 else "")
    exists = (repo / "recette" / "a-tester.md").is_file()
    print(
        "recette : commit en attente. Ce commit change du code applicatif, et rien n'indique ce qu'il "
        "faudra vérifier en recette :\n"
        f"{liste}\n\n"
        "Fais l'une des deux choses suivantes, puis relance le commit :\n"
        "1. Si le comportement visible change (fonctionnalité, règle métier, message, donnée, intégration, "
        "performance, sécurité) : ajoute une ligne à recette/a-tester.md"
        + ("" if exists else " (crée-le depuis le modèle du skill recette, assets/templates/a-tester.md)")
        + " et inclus-la dans ce commit :\n"
        "   | AAAA-MM-JJ | <changement, du point de vue de l'utilisateur> | <commit/MR> | <EX-xxx ou nouvelle> "
        "| <ce qu'il faudra observer en recette, y compris les cas d'erreur> | haut/moyen/bas | |\n"
        "   (la colonne Cas reste vide : elle sera remplie quand l'entrée deviendra un cas de test.)\n"
        "2. Si rien ne change pour l'utilisateur (refactoring, outillage, dépendance sans effet visible) : "
        "ajoute au message de commit la ligne « Recette: sans impact (<raison>) ».\n\n"
        "Ne choisis pas l'option 2 par facilité : en cas de doute, c'est l'option 1. "
        "Le risque est celui de l'utilisateur final : haut si une erreur bloque le métier ou touche les données.",
        file=sys.stderr)
    return 2


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    if not COMMIT_RE.search(command):
        return 0
    return gate(command, Path(data.get("cwd") or "."))


if __name__ == "__main__":
    sys.exit(main())
