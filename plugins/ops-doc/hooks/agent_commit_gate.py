#!/usr/bin/env python3
"""Garde-fou Claude Code : un agent ne committe ni ne pousse de changement
d'exploitation sans avoir aligné puis relu la doc ops.

Deux étapes, deux niveaux d'exigence :

  git commit  -> ops-doc-check sur le diff : la doc est-elle alignée avec ce
                 que je viens de changer ? (léger, le contexte est frais)
  git push    -> ops-doc-review sur tout ce qui part : la doc tient-elle à
                 3 h du matin ? (une fois par lot, sur un état cohérent)

Modes :

  agent_commit_gate.py                       hook PreToolUse (JSON sur stdin)
  agent_commit_gate.py mark commit|push --report FICHIER [--repo DIR]
                                             enregistre l'étape pour l'état actuel

Le hook ne fait rien si la commande n'est ni un commit ni un push, si le repo
n'a pas adopté le standard (docs/README.md + docs/runbooks/), ou si aucun
fichier d'exploitation (docs/, *.yaml, *.yml, Dockerfile*, .gitlab-ci.yml)
n'est concerné. Sinon il bloque (code 2, message renvoyé à l'agent) tant que
le script de vérification trouve des erreurs ou que l'étape n'a pas été
enregistrée pour l'état EXACT des fichiers : toute modification après coup
invalide l'enregistrement.

Ce n'est pas un contrôle inviolable : un agent de mauvaise foi pourrait
enregistrer sans relire. C'est un rappel au bon moment, doublé du script en
CI comme filet de sécurité.

Bibliothèque standard uniquement.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE.parent / "skills" / "ops-doc" / "scripts" / "check_docs.py"
OPS_RE = re.compile(r"(^docs/|\.ya?ml$|(^|/)Dockerfile[^/]*$|(^|/)\.gitlab-ci\.yml$)")
GIT_PREFIX = r"(?:^|[;&|(]\s*|\s)git(?:\s+-C\s+\S+)?(?:\s+-c\s+\S+)*\s+"
COMMIT_RE = re.compile(GIT_PREFIX + r"commit\b")
PUSH_RE = re.compile(GIT_PREFIX + r"push\b")
BASE_CANDIDATES = ["@{upstream}", "origin/HEAD", "origin/main", "origin/master"]


# ------------------------------------------------------------------ git

def git(repo: Path, *args: str, check=True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout


def ok(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True).returncode == 0


def repo_root(start: Path) -> Path | None:
    try:
        return Path(git(start, "rev-parse", "--show-toplevel").strip())
    except (RuntimeError, FileNotFoundError, NotADirectoryError):
        return None


def adopted(repo: Path) -> bool:
    return (repo / "docs" / "README.md").is_file() and (repo / "docs" / "runbooks").is_dir()


def has_head(repo: Path) -> bool:
    return ok(repo, "rev-parse", "--verify", "-q", "HEAD")


def ops_only(names) -> list[str]:
    return sorted({n for n in names if n and OPS_RE.search(n)})


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ------------------------------------------------------------------ périmètres

def commit_scope(repo: Path) -> tuple[list[str], str]:
    """Ce que le commit va enregistrer : index + arbre de travail vs HEAD
    (couvre `git commit -a`)."""
    base = ["diff", "HEAD"] if has_head(repo) else ["diff", "--cached"]
    files = ops_only(git(repo, *base, "--name-only").splitlines())
    fp = sha(git(repo, *base, "--binary", "--", *files)) if files else "vide"
    return files, fp


def push_base(repo: Path) -> str | None:
    for ref in BASE_CANDIDATES:
        if ok(repo, "rev-parse", "--verify", "-q", ref):
            mb = git(repo, "merge-base", "HEAD", ref, check=False).strip()
            if mb:
                return mb
    return None


def push_scope(repo: Path) -> tuple[list[str], str, str]:
    """Ce qui part au push : HEAD vs la base distante. Sans base (premier
    push), tout le contenu d'exploitation de HEAD."""
    if not has_head(repo):
        return [], "vide", ""
    base = push_base(repo)
    if base:
        files = ops_only(git(repo, "diff", "--name-only", base, "HEAD").splitlines())
        fp = sha(git(repo, "diff", "--binary", base, "HEAD", "--", *files)) if files else "vide"
        return files, fp, f"{base[:10]}..HEAD"
    files = ops_only(git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    fp = sha(git(repo, "ls-tree", "-r", "HEAD", "--", *files)) if files else "vide"
    return files, fp, "tout HEAD (pas de base distante)"


# ------------------------------------------------------------------ état

def state_path(repo: Path) -> Path:
    return Path(git(repo, "rev-parse", "--absolute-git-dir").strip()) / "ops-doc" / "state.json"


def load_state(repo: Path) -> dict:
    try:
        return json.loads(state_path(repo).read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def run_check(repo: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(CHECK), str(repo)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


# ------------------------------------------------------------------ hook

def target_dir(command: str, cwd: Path) -> Path:
    """Gère `cd X && git ...` et `git -C X ...`."""
    for rx in (r"^\s*cd\s+(\S+)\s*&&", r"\bgit\s+-C\s+(\S+)"):
        m = re.search(rx, command)
        if m:
            p = Path(shlex.split(m.group(1))[0]).expanduser()
            cwd = p if p.is_absolute() else cwd / p
    return cwd


def block(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 2


def mark_cmd(stage: str, repo: Path) -> str:
    return f"python3 {Path(__file__).resolve()} mark {stage} --repo {repo} --report <fichier>"


FOOTER = ("Toute modification après l'enregistrement l'invalide. Ne contourne pas ce "
          "contrôle ; si tu penses que c'est un faux positif, demande à l'utilisateur.")


def gate(stage: str, repo: Path) -> int:
    if stage == "commit":
        files, fp = commit_scope(repo)
        scope = "ce commit"
    else:
        files, fp, rng = push_scope(repo)
        scope = f"ce push ({rng})"
    if not files:
        return 0

    code, out = run_check(repo)
    if code == 1:
        return block(
            f"ops-doc : {stage} bloqué, la doc d'exploitation n'est pas conforme.\n\n{out}\n"
            "Corrige les erreurs (skill ops-doc-check), puis relance. " + FOOTER)

    if load_state(repo).get(stage, {}).get("fingerprint") == fp:
        return 0

    liste = "\n".join(f"  - {f}" for f in files)
    if stage == "commit":
        todo = (
            "1. Utilise le skill ops-doc-check, en te limitant à ces changements : la doc "
            "est-elle encore vraie ? (noms dans les commandes, alertes et runbooks, "
            "config.md, dimensionnement, cases de la checklist)\n"
            "2. Mets la doc à jour dans ce même commit si nécessaire.\n")
    else:
        todo = (
            "1. Utilise le skill ops-doc-review sur les runbooks, procédures et fichiers "
            "de doc concernés par ces changements (pas toute la doc si elle n'est pas "
            "concernée).\n"
            "2. Applique les constats bloquants et importants dans un commit, ou "
            "explique à l'utilisateur pourquoi tu ne le fais pas.\n")
    return block(
        f"ops-doc : {stage} en attente. {scope.capitalize()} touche des fichiers "
        f"d'exploitation, et l'étape « {stage} » n'a pas été enregistrée pour cet état :\n"
        f"{liste}\n\nAvant de relancer :\n{todo}"
        "3. Écris ton rapport (avec une ligne « Verdict : ... ») dans un fichier, puis :\n"
        f"   {mark_cmd(stage, repo)}\n"
        f"4. Relance le {stage}.\n\n" + FOOTER)


def hook() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    stages = [s for s, rx in (("commit", COMMIT_RE), ("push", PUSH_RE)) if rx.search(command)]
    if not stages:
        return 0
    repo = repo_root(target_dir(command, Path(data.get("cwd") or ".")))
    if not repo or not adopted(repo):
        return 0
    for stage in stages:          # `git commit ... && git push` : les deux
        code = gate(stage, repo)
        if code:
            return code
    return 0


# ------------------------------------------------------------------ mark

def mark(argv) -> int:
    ap = argparse.ArgumentParser(prog="agent_commit_gate.py mark")
    ap.add_argument("stage", choices=["commit", "push"])
    ap.add_argument("--report", required=True)
    ap.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    repo = repo_root(Path(a.repo))
    if not repo:
        print("pas un repo git", file=sys.stderr)
        return 2
    report = Path(a.report)
    text = report.read_text(encoding="utf-8") if report.is_file() else ""
    if not re.search(r"(?im)^\W*verdict\W*:", text):
        print("rapport absent ou sans ligne « Verdict : … »", file=sys.stderr)
        return 2
    code, out = run_check(repo)
    if code == 1:
        print("la doc n'est pas conforme, rien n'est enregistré :\n" + out, file=sys.stderr)
        return 2

    if a.stage == "commit":
        files, fp = commit_scope(repo)
    else:
        files, fp, _ = push_scope(repo)
    sp = state_path(repo)
    sp.parent.mkdir(parents=True, exist_ok=True)
    rpath = sp.parent / f"rapport-{a.stage}.md"
    rpath.write_text(text, encoding="utf-8")
    state = load_state(repo)
    state[a.stage] = {"fingerprint": fp, "files": files, "report": str(rpath),
                      "date": dt.datetime.now().isoformat(timespec="seconds")}
    sp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    print(f"étape « {a.stage} » enregistrée pour {len(files)} fichier(s).")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "mark":
        sys.exit(mark(sys.argv[2:]))
    sys.exit(hook())
