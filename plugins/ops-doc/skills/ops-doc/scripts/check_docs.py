#!/usr/bin/env python3
"""Vérifie la conformité d'un dossier docs/ au standard ops-doc.

Bibliothèque standard uniquement. Les règles sont décrites dans
references/standard.md, section « Règles vérifiées par le script ».

Usage :
    check_docs.py [REPO] [--docs DIR] [--manifests DIR ...]
                  [--today AAAA-MM-JJ] [--max-age-days N] [--json]

Code de sortie : 0 si aucune erreur, 1 s'il y a au moins une erreur,
2 si les arguments sont invalides.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import unquote

ERREUR, AVERT, INFO = "ERREUR", "AVERTISSEMENT", "INFO"

ROOT_FILES = ["README.md", "architecture.md", "config.md",
              "dimensionnement.md", "reprise.md", "checklist-production.md"]
DIRS = ["runbooks", "procedures", "adr", "postmortems"]
SKIP_DIRS = {".git", "node_modules", "vendor", ".terraform", ".venv", "venv",
             "__pycache__", ".idea", ".vscode", "charts-cache"}

# Sections obligatoires : chaque entrée est une liste d'alternatives
# (radicaux normalisés, sans accents). Une seule alternative suffit.
SECTIONS = {
    "README.md": [["liens"], ["composants"], ["dependances"], ["acces"]],
    "architecture.md": [["contexte"], ["donnees"], ["deploiement"], ["risque"]],
    "config.md": [["variables"], ["secrets"]],
    "dimensionnement.md": [["methode"], ["stockage"]],
    "reprise.md": [["scenario"], ["reconstruction"]],
}
FIELDS = {
    "README.md": ["Responsable", "Criticité", "RPO"],
}
RUNBOOK_SECTIONS = [["signification"], ["impact"], ["diagnostic"],
                    ["remediation"], ["verifi"], ["escalade"]]
ADR_SECTIONS = [["contexte"], ["decision"], ["consequences"]]
ADR_FIELDS = ["Statut", "Date"]
PM_SECTIONS = [["resume"], ["chronologie"], ["cause"], ["actions"]]

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
REVUE_RE = re.compile(r"derniere revue\s*:\s*\**\s*(\d{4}-\d{2}-\d{2}|aaaa-mm-jj)")
TODO_RE = re.compile(r"TODO\(ops-doc\)")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
WIKI_RE = re.compile(r"\[\[[^\]]+\]\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
INLINE_CODE_RE = re.compile(r"`[^`]*`")

SECRET_PATTERNS = [
    ("clé privée", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), None),
    ("clé d'accès AWS", re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), 1),
    ("mot de passe dans une URL",
     re.compile(r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|amqp)://[^:/\s@]+:([^@\s]+)@"), 1),
    ("secret en clair",
     re.compile(r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\s*[:=]\s*[\"']?([^\s\"'`|,]+)"), 1),
    ("secret en clair",
     re.compile(r"\b[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_KEY|ACCESS_KEY)[A-Z0-9_]*\s*[:=]\s*[\"']?([^\s\"'`|,]+)"), 1),
]
PLACEHOLDER_HINTS = ("<", ">", "$", "{", "}", "*", "xxx", "changeme", "change-me",
                     "example", "exemple", "todo", "redacted", "masque", "...", "…")


@dataclass
class Finding:
    level: str
    code: str
    message: str
    file: str = ""
    line: int = 0


@dataclass
class Report:
    docs: str
    findings: list[Finding] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def add(self, level, code, message, file="", line=0):
        self.findings.append(Finding(level, code, message, str(file), line))

    def count(self, level):
        return sum(1 for f in self.findings if f.level == level)


# ---------------------------------------------------------------- utilitaires

def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def prose_lines(text: str):
    """(numéro, ligne) hors des blocs de code délimités par ``` ou ~~~."""
    in_code = False
    for i, line in enumerate(text.splitlines(), 1):
        if re.match(r"^\s*(```|~~~)", line):
            in_code = not in_code
            continue
        if not in_code:
            yield i, line


def headings(text: str) -> list[str]:
    out = []
    for _, line in prose_lines(text):
        m = HEADING_RE.match(line)
        if m:
            out.append(norm(m.group(2)))
    return out


LABELS = {"liens": "Liens", "composants": "Composants", "dependances": "Dépendances",
          "acces": "Accès", "contexte": "Contexte", "donnees": "Données",
          "deploiement": "Déploiement", "risque": "Risques", "variables": "Variables",
          "secrets": "Secrets", "methode": "Méthode", "stockage": "Stockage",
          "scenario": "Scénarios", "reconstruction": "Reconstruction",
          "signification": "Signification", "impact": "Impact", "diagnostic": "Diagnostic",
          "remediation": "Remédiation", "verifi": "Vérifier / Vérification",
          "escalade": "Escalade", "decision": "Décision", "consequences": "Conséquences",
          "resume": "Résumé", "chronologie": "Chronologie", "cause": "Cause",
          "actions": "Actions"}


def check_sections(report, rel, text, required, level=ERREUR):
    heads = headings(text)
    for alternatives in required:
        if not any(any(alt in h for h in heads) for alt in alternatives):
            label = LABELS.get(alternatives[0], alternatives[0])
            report.add(level, "SECTION", f"section obligatoire absente : « {label} »", rel)


def check_fields(report, rel, text, fields):
    ntext = norm(text)
    for f in fields:
        if f"**{norm(f)}" not in ntext:
            report.add(ERREUR, "CHAMP", f"champ obligatoire absent : **{f}**", rel)


def looks_placeholder(value: str) -> bool:
    v = value.strip().strip("\"'")
    lv = v.lower()
    if len(v) < 8:
        return True
    if any(h in lv for h in PLACEHOLDER_HINTS):
        return True
    # noms de ressources Kubernetes (rdv-pg-app) ou de clés (password)
    if re.fullmatch(r"[a-z0-9]+(?:[-.][a-z0-9]+)+", v):
        return True
    if re.fullmatch(r"[a-z_]+", v):
        return True
    return False


def mask(value: str) -> str:
    return value[:3] + "…" if len(value) > 3 else "…"


# ---------------------------------------------------------------- docs

def check_structure(report, docs: Path):
    for f in ROOT_FILES:
        if not (docs / f).is_file():
            report.add(ERREUR, "STRUCT-FICHIER", f"fichier obligatoire absent : {f}")
    for d in DIRS:
        p = docs / d
        if not p.is_dir():
            report.add(ERREUR, "STRUCT-DOSSIER", f"dossier obligatoire absent : {d}/")
        elif not (p / "_template.md").is_file():
            report.add(AVERT, "STRUCT-MODELE", f"{d}/_template.md absent")


def doc_files(docs: Path):
    for p in sorted(docs.rglob("*.md")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def is_template(p: Path) -> bool:
    return p.name.startswith("_")


def check_content(report, docs: Path, today: dt.date, max_age: int):
    for name, req in SECTIONS.items():
        p = docs / name
        if p.is_file():
            check_sections(report, name, read(p), req)
    for name, flds in FIELDS.items():
        p = docs / name
        if p.is_file():
            check_fields(report, name, read(p), flds)

    # reprise : RPO / RTO n'importe où (titre ou tableau)
    p = docs / "reprise.md"
    if p.is_file():
        t = read(p)
        for k in ("RPO", "RTO"):
            if k not in t:
                report.add(ERREUR, "CHAMP", f"{k} absent", "reprise.md")
        past = [d for d in parse_dates(t) if d <= today]
        if not past:
            report.add(AVERT, "DATE-MANQUANTE", "aucune date de dernier test", "reprise.md")
        elif (today - max(past)).days > max_age:
            report.add(AVERT, "DATE-PERIMEE",
                       f"dernier test le {max(past)} (> {max_age} jours)", "reprise.md")

    for name in ("dimensionnement.md", "checklist-production.md"):
        p = docs / name
        if not p.is_file():
            continue
        m = REVUE_RE.search(norm(read(p)))
        if not m or m.group(1) == "aaaa-mm-jj":
            report.add(AVERT, "DATE-MANQUANTE", "ligne « Dernière revue : AAAA-MM-JJ » absente ou non remplie", name)
        else:
            d = safe_date(m.group(1))
            if d and (today - d).days > max_age:
                report.add(AVERT, "DATE-PERIMEE", f"dernière revue le {d} (> {max_age} jours)", name)

    p = docs / "checklist-production.md"
    if p.is_file():
        t = read(p)
        total = len(re.findall(r"^\s*[-*] \[[ xX]\]", t, re.M))
        done = len(re.findall(r"^\s*[-*] \[[xX]\]", t, re.M))
        if total == 0:
            report.add(AVERT, "CHECKLIST-VIDE", "aucune case à cocher", "checklist-production.md")
        else:
            report.stats["checklist"] = f"{done}/{total}"

    p = docs / "architecture.md"
    if p.is_file() and "```mermaid" not in read(p):
        report.add(INFO, "MERMAID", "aucun schéma Mermaid", "architecture.md")

    for p in (docs / "runbooks").glob("*.md") if (docs / "runbooks").is_dir() else []:
        if not is_template(p):
            check_sections(report, f"runbooks/{p.name}", read(p), RUNBOOK_SECTIONS)

    for p in (docs / "procedures").glob("*.md") if (docs / "procedures").is_dir() else []:
        if is_template(p):
            continue
        rel = f"procedures/{p.name}"
        t = read(p)
        heads = headings(t)
        has_steps = any("etape" in h for h in heads) or any(
            re.match(r"^\s*\d+\.\s", l) for _, l in prose_lines(t))
        if not has_steps:
            report.add(ERREUR, "SECTION", "ni section « Étapes » ni liste numérotée", rel)
        if not any("verifi" in h for h in heads):
            report.add(ERREUR, "SECTION", "section obligatoire absente : « Vérification »", rel)
        nt = norm(t)
        if not any(k in nt for k in ("retour arriere", "rollback", "irreversible")):
            report.add(AVERT, "SECTION", "aucune mention de retour arrière / rollback / irréversible", rel)

    for p in (docs / "adr").glob("*.md") if (docs / "adr").is_dir() else []:
        if is_template(p):
            continue
        rel = f"adr/{p.name}"
        if not re.fullmatch(r"\d{4}-[a-z0-9][a-z0-9-]*\.md", p.name):
            report.add(AVERT, "NOM-FICHIER", "attendu : NNNN-titre-court.md", rel)
        t = read(p)
        check_sections(report, rel, t, ADR_SECTIONS)
        check_fields(report, rel, t, ADR_FIELDS)

    for p in (docs / "postmortems").glob("*.md") if (docs / "postmortems").is_dir() else []:
        if is_template(p):
            continue
        rel = f"postmortems/{p.name}"
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md", p.name):
            report.add(AVERT, "NOM-FICHIER", "attendu : AAAA-MM-JJ-titre-court.md", rel)
        check_sections(report, rel, read(p), PM_SECTIONS)


def parse_dates(text):
    out = []
    for s in DATE_RE.findall(text):
        d = safe_date(s)
        if d:
            out.append(d)
    return out


def safe_date(s):
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


def check_links_secrets_todos(report, docs: Path):
    todos = {}
    for p in doc_files(docs):
        rel = p.relative_to(docs).as_posix()
        text = read(p)
        template = is_template(p)

        for i, line in prose_lines(text):
            clean = INLINE_CODE_RE.sub("", line)
            for target in ([] if template else LINK_RE.findall(clean)):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                    continue
                path = unquote(target.split("#", 1)[0])
                if path and not (p.parent / path).exists():
                    report.add(ERREUR, "LIEN-CASSE", f"lien vers « {target} » introuvable", rel, i)
            if WIKI_RE.search(clean):
                report.add(AVERT, "WIKILINK", "[[wikilink]] : non affiché par GitLab/GitHub, utiliser [texte](fichier.md)", rel, i)

        if not template:
            for i, line in enumerate(text.splitlines(), 1):
                for label, rx, grp in SECRET_PATTERNS:
                    for m in rx.finditer(line):
                        value = m.group(grp) if grp else m.group(0)
                        if grp and looks_placeholder(value):
                            continue
                        report.add(ERREUR, "SECRET", f"{label} probable ({mask(value)})", rel, i)
            n = len(TODO_RE.findall(text))
            if n:
                todos[rel] = n

    for rel, n in todos.items():
        report.add(INFO, "TODO", f"{n} marqueur(s) TODO(ops-doc)", rel)
    report.stats["todo"] = sum(todos.values())


# ---------------------------------------------------------------- manifests

def yaml_files(roots, exclude: Path):
    exclude = exclude.resolve()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dp = Path(dirpath).resolve()
            dirnames[:] = [d for d in dirnames
                           if d not in SKIP_DIRS and (dp / d).resolve() != exclude]
            for f in filenames:
                if f.endswith((".yaml", ".yml")):
                    yield Path(dirpath) / f


def scan_manifests(roots, docs: Path):
    alerts = {}      # nom -> (fichier, ligne, runbook_url | None)
    env_vars = {}    # nom -> (fichier, ligne)
    secrets = {}     # nom -> (fichier, ligne)
    for f in yaml_files(roots, docs):
        lines = read(f).splitlines()
        cur = None
        for i, line in enumerate(lines):
            m = re.match(r"^\s*-\s*(alert|record):\s*[\"']?([A-Za-z0-9_:]+)", line)
            if m or line.startswith("---"):
                cur = None
            if m and m.group(1) == "alert":
                cur = m.group(2)
                alerts[cur] = (str(f), i + 1, None)
                continue
            if cur:
                u = re.match(r"^\s*runbook_url:\s*[\"']?([^\"'\s]+)", line)
                if u:
                    fi, li, _ = alerts[cur]
                    alerts[cur] = (fi, li, u.group(1))

            e = re.match(r"^\s*-\s*name:\s*[\"']?([A-Z_][A-Z0-9_]*)[\"']?\s*$", line)
            if e:
                nxt = next((l for l in lines[i + 1:i + 3] if l.strip()), "")
                if re.match(r"^\s*(value|valueFrom):", nxt):
                    env_vars.setdefault(e.group(1), (str(f), i + 1))

            if re.match(r"^\s*(secretKeyRef|secretRef):\s*$", line):
                for l in lines[i + 1:i + 4]:
                    n = re.match(r"^\s*name:\s*[\"']?([a-z0-9][a-z0-9.-]*)[\"']?\s*$", l)
                    if n:
                        secrets.setdefault(n.group(1), (str(f), i + 1))
                        break
            s = re.match(r"^\s*secretName:\s*[\"']?([a-z0-9][a-z0-9.-]*)[\"']?\s*$", line)
            if s:
                secrets.setdefault(s.group(1), (str(f), i + 1))
    return alerts, env_vars, secrets


def check_manifests(report, docs: Path, roots, repo: Path):
    alerts, env_vars, secrets = scan_manifests(roots, docs)
    report.stats.update(alertes=len(alerts), variables=len(env_vars), secrets=len(secrets))

    def relrepo(f):
        try:
            return Path(f).resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            return f

    rb_dir = docs / "runbooks"
    runbooks = {p.stem for p in rb_dir.glob("*.md") if not is_template(p)} if rb_dir.is_dir() else set()

    for name, (f, line, url) in sorted(alerts.items()):
        local = name in runbooks
        if not url:
            report.add(ERREUR, "ALERTE-SANS-URL", f"alerte {name} sans annotation runbook_url", relrepo(f), line)
            if not local:
                report.add(ERREUR, "ALERTE-SANS-RUNBOOK", f"alerte {name} : runbooks/{name}.md absent", relrepo(f), line)
            continue
        points_here = "runbooks/" in url and ("docs/" in url or not url.startswith("http"))
        if local:
            if name not in url:
                report.add(AVERT, "RUNBOOK-URL", f"alerte {name} : runbook_url ({url}) ne pointe pas vers runbooks/{name}.md", relrepo(f), line)
        elif points_here:
            report.add(ERREUR, "ALERTE-SANS-RUNBOOK", f"alerte {name} : runbook_url pointe vers la doc mais runbooks/{name}.md absent", relrepo(f), line)
        else:
            report.add(INFO, "RUNBOOK-EXTERNE", f"alerte {name} : runbook externe ({url})", relrepo(f), line)

    if alerts:
        for rb in sorted(runbooks - set(alerts)):
            report.add(AVERT, "RUNBOOK-ORPHELIN", f"aucune alerte « {rb} » trouvée dans les manifests", f"runbooks/{rb}.md")
    elif runbooks:
        report.add(INFO, "ALERTES", "aucune alerte trouvée dans les manifests : lien alertes/runbooks non vérifié (voir --manifests)")

    cfg = docs / "config.md"
    if cfg.is_file():
        text = read(cfg)
        for v, (f, line) in sorted(env_vars.items()):
            if v not in text:
                report.add(AVERT, "CONFIG-VAR", f"variable {v} absente de config.md", relrepo(f), line)
        for s, (f, line) in sorted(secrets.items()):
            if s not in text:
                report.add(AVERT, "CONFIG-SECRET", f"Secret {s} absent de config.md", relrepo(f), line)


# ---------------------------------------------------------------- sortie

def render(report: Report) -> str:
    out = [f"# Vérification ops-doc : {report.docs}", ""]
    e, w, i = report.count(ERREUR), report.count(AVERT), report.count(INFO)
    verdict = "CONFORME" if e == 0 else "NON CONFORME"
    out.append(f"**{verdict}** : {e} erreur(s), {w} avertissement(s), {i} info(s)")
    if report.stats:
        out.append("")
        out.append("Statistiques : " + ", ".join(f"{k} = {v}" for k, v in report.stats.items()))
    for level in (ERREUR, AVERT, INFO):
        items = [f for f in report.findings if level == f.level]
        if not items:
            continue
        out += ["", f"## {level} ({len(items)})", ""]
        for f in items:
            loc = f.file + (f":{f.line}" if f.line else "")
            out.append(f"- `{f.code}` {loc + ' : ' if loc else ''}{f.message}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".", help="racine du repo (défaut : .)")
    ap.add_argument("--docs", help="dossier de doc (défaut : REPO/docs)")
    ap.add_argument("--manifests", action="append",
                    help="dossier de manifests/alertes à analyser (répétable ; défaut : REPO hors docs)")
    ap.add_argument("--today", help="date de référence AAAA-MM-JJ (défaut : aujourd'hui)")
    ap.add_argument("--max-age-days", type=int, default=180)
    ap.add_argument("--json", action="store_true", help="sortie JSON")
    a = ap.parse_args(argv)

    repo = Path(a.repo)
    docs = Path(a.docs) if a.docs else repo / "docs"
    if not docs.is_dir():
        print(f"dossier de doc introuvable : {docs}", file=sys.stderr)
        return 2
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    roots = [Path(m) for m in a.manifests] if a.manifests else [repo]

    report = Report(docs=str(docs))
    check_structure(report, docs)
    check_content(report, docs, today, a.max_age_days)
    check_links_secrets_todos(report, docs)
    check_manifests(report, docs, roots, repo)

    if a.json:
        print(json.dumps({"docs": report.docs, "stats": report.stats,
                          "findings": [asdict(f) for f in report.findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(render(report), end="")
    return 1 if report.count(ERREUR) else 0


if __name__ == "__main__":
    sys.exit(main())
