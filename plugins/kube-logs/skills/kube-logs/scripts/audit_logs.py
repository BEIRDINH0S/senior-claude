#!/usr/bin/env python3
"""Audite le logging d'une app Kubernetes par rapport au standard kube-logs.

Analyse le code (JavaScript/TypeScript), package.json, les Dockerfile, les
manifests Kubernetes, la configuration Alloy (.alloy, ou ConfigMap qui en
contient) et la configuration Loki. Bibliothèque standard uniquement ;
détection par expressions régulières, donc heuristique.

Usage :
    audit_logs.py [REPO] [--json]

Code de sortie : 0 sans erreur, 1 avec au moins une erreur.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ERREUR, AVERT, INFO = "ERREUR", "AVERTISSEMENT", "INFO"
SKIP_DIRS = {".git", "node_modules", "dist", "build", "coverage", ".next", ".nuxt",
             "vendor", ".venv", "venv", "__pycache__", ".turbo", "out"}
CODE_EXT = (".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".jsx", ".tsx")
TEST_RE = re.compile(r"(^|/)(tests?|__tests__|spec|e2e|scripts?|bin|tools|fixtures?)/|\.(test|spec)\.[cm]?[jt]sx?$")

HIGH_CARD = r"(?:user(?:_?id)?|userid|req(?:uest)?_?id|trace_?id|span_?id|session(?:_?id)?|order_?id|path|url|uri|ip|client_?ip|email|pod|id)"

R = {
    "console": re.compile(r"\bconsole\.(log|info|warn|error|debug)\s*\("),
    "file_pino_dest": re.compile(r"pino\.destination\(\s*(?:\{[^}]*dest\s*:\s*)?['\"`]([^'\"`]+)['\"`]"),
    "file_pino_transport": re.compile(r"target\s*:\s*['\"]pino/file['\"][^}]*destination\s*:\s*['\"`]([^'\"`]+)['\"`]", re.S),
    "file_winston": re.compile(r"transports\.File\s*\(|new\s+DailyRotateFile\s*\(|winston-daily-rotate-file"),
    "file_stream": re.compile(r"createWriteStream\(\s*[^)]*\.log['\"`]"),
    "file_log4js": re.compile(r"type\s*:\s*['\"](file|dateFile|fileSync)['\"]"),
    "pino_use": re.compile(r"\bpino\s*\(|from\s+['\"]pino['\"]|require\(\s*['\"]pino['\"]\s*\)"),
    "pino_call": re.compile(r"\bpino\s*\("),
    "pretty": re.compile(r"pino-pretty"),
    "secret_call": re.compile(r"\b(?:log(?:ger)?|console|req\.log|this\.logger)\.(?:trace|debug|info|warn|error|fatal|log)\s*\([^;\n]*\b(password|passwd|token|authorization|secret|cookie)\b", re.I),
    "stack_text": re.compile(r"\b(?:log(?:ger)?|console|req\.log|this\.logger)\.\w+\s*\([^;\n]*\b(?:err|error|e)\.stack\b"),
}


@dataclass
class Finding:
    level: str
    code: str
    message: str
    file: str = ""
    line: int = 0


class Audit:
    def __init__(self, repo: Path):
        self.repo = repo
        self.findings: list[Finding] = []
        self.stats = {"fichiers_code": 0, "manifests": 0, "alloy": 0, "loki": 0}

    def add(self, level, code, msg, path: Path | None = None, line=0):
        rel = path.relative_to(self.repo).as_posix() if path else ""
        self.findings.append(Finding(level, code, msg, rel, line))

    def count(self, level):
        return sum(f.level == level for f in self.findings)


def walk(repo: Path):
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            yield Path(dirpath) / f


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def strip_comments(text: str) -> str:
    """Remplace les commentaires JS par des espaces (garde les numéros de ligne)."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"/\*.*?\*/", blank, text, flags=re.S)
    return re.sub(r"(?m)(^|[^:'\"`])//[^\n]*", lambda m: m.group(1) + " " * (len(m.group(0)) - len(m.group(1))), text)


# ------------------------------------------------------------------ code

def audit_code(a: Audit, p: Path, rel: str):
    raw = read(p)
    if not raw:
        return
    a.stats["fichiers_code"] += 1
    text = strip_comments(raw)
    is_app = not TEST_RE.search(rel)

    if is_app:
        hits = [m for m in R["console"].finditer(text)]
        if hits:
            a.add(AVERT, "LOG-CONSOLE",
                  f"{len(hits)} appel(s) console.* : non structuré, contourne le logger (utiliser le logger, ESLint no-console)",
                  p, line_of(text, hits[0].start()))

    for key, label in (("file_pino_dest", "pino.destination vers un fichier"),
                       ("file_pino_transport", "transport pino/file vers un fichier")):
        for m in R[key].finditer(text):
            dest = m.group(1)
            if dest not in ("1", "2", "/dev/stdout", "/dev/stderr"):
                a.add(ERREUR, "LOG-FICHIER", f"{label} ({dest}) : écrire sur stdout", p, line_of(text, m.start()))
    for key, label in (("file_winston", "transport fichier winston"),
                       ("file_stream", "createWriteStream vers un .log"),
                       ("file_log4js", "appender fichier log4js")):
        for m in R[key].finditer(text):
            a.add(ERREUR, "LOG-FICHIER", f"{label} : écrire sur stdout", p, line_of(text, m.start()))

    if is_app:
        for m in R["pretty"].finditer(text):
            ctx = text[max(0, m.start() - 200): m.end() + 50]
            if re.search(r"isTTY|NODE_ENV|isProd|isDev|production|development", ctx):
                continue   # pino-pretty conditionné à l'environnement : la pratique recommandée
            a.add(AVERT, "LOG-PRETTY",
                  "pino-pretty dans le code applicatif : vérifier qu'il n'est actif qu'en local (TTY), jamais en conteneur",
                  p, line_of(text, m.start()))

    for m in R["secret_call"].finditer(text):
        a.add(AVERT, "LOG-SECRET", f"appel de log qui mentionne « {m.group(1)} » : vérifier qu'aucune valeur sensible n'est loguée",
              p, line_of(text, m.start()))
    for m in R["stack_text"].finditer(text):
        a.add(AVERT, "LOG-STACK-TEXTE", "stack passée en texte : loguer { err } pour qu'elle reste dans un champ JSON",
              p, line_of(text, m.start()))

    # pino : configuration du niveau et du masquage, sur l'appel pino(...)
    for m in R["pino_call"].finditer(text):
        window = text[m.start(): m.start() + 2000]
        ln = line_of(text, m.start())
        if not re.search(r"formatters\s*:\s*\{[^}]*\blevel\b", window, re.S):
            a.add(AVERT, "LOG-NIVEAU-NUMERIQUE", "pino sans formatters.level : le niveau sort en nombre (30, 50)", p, ln)
        if not re.search(r"\bredact\s*:", window):
            a.add(AVERT, "LOG-REDACT", "pino sans redact : aucun masquage garanti des secrets et données personnelles", p, ln)


def audit_package_json(a: Audit, p: Path):
    try:
        pkg = json.loads(read(p))
    except json.JSONDecodeError:
        return
    if "pino-pretty" in (pkg.get("dependencies") or {}):
        a.add(AVERT, "LOG-PRETTY", "pino-pretty en dépendance de prod : le passer en devDependencies", p)


def audit_dockerfile(a: Audit, p: Path):
    text = read(p)
    for m in re.finditer(r"(?im)^\s*(CMD|ENTRYPOINT)\s+(.+)$", text):
        instr, arg = m.group(1).upper(), m.group(2).strip()
        ln = line_of(text, m.start())
        if re.search(r"\b(npm|yarn|pnpm)\b[^\n]*\b(start|run)\b", arg):
            a.add(AVERT, "LOG-NPM-START",
                  f"{instr} via npm/yarn/pnpm : lignes parasites dans les logs et SIGTERM mal transmis (CMD [\"node\", \"dist/main.js\"])",
                  p, ln)
        elif not arg.startswith("[") and re.match(r"node\b", arg):
            a.add(AVERT, "LOG-NPM-START",
                  f"{instr} en forme shell : /bin/sh devient PID 1 et ne transmet pas SIGTERM (utiliser la forme [\"node\", ...])",
                  p, ln)


# ------------------------------------------------------------------ manifests

def audit_yaml(a: Audit, p: Path):
    text = read(p)
    if not text:
        return
    if re.search(r"(?m)^\s*kind:\s*(Deployment|StatefulSet|DaemonSet|Job|CronJob|Pod)\b", text) or "containers:" in text:
        a.stats["manifests"] += 1
        for m in re.finditer(r"(?m)^\s*-?\s*mountPath:\s*[\"']?([^\"'\s]+)", text):
            if re.search(r"log", m.group(1), re.I):
                a.add(ERREUR, "LOG-VOLUME", f"volume monté sur {m.group(1)} : les logs vont sur stdout, pas dans un volume",
                      p, line_of(text, m.start()))
        for m in re.finditer(r"tail\s+-[fF]", text):
            a.add(AVERT, "LOG-SIDECAR-TAIL", "conteneur qui fait tail -f : sidecar de recopie, à réserver aux apps non modifiables",
                  p, line_of(text, m.start()))
    if "loki.process" in text or "loki.source" in text:
        audit_alloy_text(a, p, text)
    if re.search(r"(?m)^\s*(schema_config|limits_config|compactor)\s*:", text) and re.search(r"(?m)^\s*(storage_config|common|schema_config)\s*:", text):
        audit_loki_text(a, p, text)


def audit_alloy_text(a: Audit, p: Path, text: str):
    a.stats["alloy"] += 1
    # stage.labels { values = { a = "", b = "x" } }
    for blk in re.finditer(r"stage\.labels\s*\{(.*?)\n\s*\}", text, re.S):
        body = blk.group(1)
        for k in re.finditer(r"[\"']?([A-Za-z_][\w.-]*)[\"']?\s*=", body):
            name = k.group(1)
            if name == "values":
                continue
            if re.fullmatch(HIGH_CARD, name, re.I):
                a.add(ERREUR, "LOKI-LABEL-CARDINALITE",
                      f"label « {name} » à forte cardinalité : le garder dans le JSON ou en structured metadata",
                      p, line_of(text, blk.start() + k.start()))
    for m in re.finditer(r"target_label\s*=\s*[\"']([^\"']+)[\"']", text):
        name = m.group(1)
        if name == "pod":
            # pod en label est toléré s'il est ensuite déplacé en structured metadata
            if re.search(r"stage\.structured_metadata\s*\{[^}]*\bpod\b", text, re.S):
                continue
        if re.fullmatch(HIGH_CARD, name, re.I):
            a.add(ERREUR, "LOKI-LABEL-CARDINALITE",
                  f"target_label « {name} » à forte cardinalité (déplacer en structured metadata)",
                  p, line_of(text, m.start()))
    if "loki.process" in text and not re.search(r"stage\.(json|logfmt)\b", text):
        a.add(INFO, "LOKI-PAS-DE-PARSING", "loki.process sans stage.json ni stage.logfmt", p)


def audit_loki_text(a: Audit, p: Path, text: str):
    a.stats["loki"] += 1
    if not re.search(r"retention_enabled\s*:\s*true", text):
        a.add(AVERT, "LOKI-RETENTION",
              "pas de compactor.retention_enabled: true : Loki garde les logs indéfiniment", p)


# ------------------------------------------------------------------ main

def run(repo: Path) -> Audit:
    a = Audit(repo)
    for p in walk(repo):
        rel = p.relative_to(repo).as_posix()
        name = p.name
        if name.endswith(CODE_EXT) and not name.endswith(".d.ts"):
            audit_code(a, p, rel)
        elif name == "package.json":
            audit_package_json(a, p)
        elif name == "Dockerfile" or name.startswith("Dockerfile.") or name.endswith(".Dockerfile"):
            audit_dockerfile(a, p)
        elif name.endswith((".yaml", ".yml")):
            audit_yaml(a, p)
        elif name.endswith((".alloy", ".river")):
            audit_alloy_text(a, p, read(p))
    return a


def render(a: Audit) -> str:
    e, w, i = a.count(ERREUR), a.count(AVERT), a.count(INFO)
    out = [f"# Audit kube-logs : {a.repo}", "",
           f"**{'CONFORME' if e == 0 else 'NON CONFORME'}** : {e} erreur(s), {w} avertissement(s), {i} info(s)", "",
           "Analysé : " + ", ".join(f"{k} = {v}" for k, v in a.stats.items())]
    for level in (ERREUR, AVERT, INFO):
        items = [f for f in a.findings if f.level == level]
        if items:
            out += ["", f"## {level} ({len(items)})", ""]
            for f in items:
                loc = f.file + (f":{f.line}" if f.line else "")
                out.append(f"- `{f.code}` {loc} : {f.message}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"dossier introuvable : {repo}", file=sys.stderr)
        return 2
    a = run(repo)
    if args.json:
        print(json.dumps({"repo": str(repo), "stats": a.stats, "findings": [asdict(f) for f in a.findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(render(a), end="")
    return 1 if a.count(ERREUR) else 0


if __name__ == "__main__":
    sys.exit(main())
