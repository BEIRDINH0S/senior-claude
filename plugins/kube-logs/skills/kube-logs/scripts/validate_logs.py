#!/usr/bin/env python3
"""Valide des lignes de log RÉELLES contre le standard kube-logs.

Là où audit_logs.py lit le code, cet outil lit ce que l'app a vraiment écrit :
chaque ligne doit être un objet JSON sur une seule ligne, avec les champs
attendus, un niveau en texte, une date ISO, sans secret ni donnée personnelle,
avec des messages stables.

Sources (une seule à la fois) :
    validate_logs.py [FICHIER ...]          fichiers, ou stdin si aucun (préfixe CRI retiré automatiquement)
    validate_logs.py --kubectl "-n ns -l app.kubernetes.io/name=api --since=1h"
    validate_logs.py --loki http://loki:3100 --query '{app="api"}' [--since 1h] [--limit 5000]

Options :
    --config FICHIER     règles (JSON) ; défaut : ./.kube-logs.json s'il existe
    --tolerance R        part de lignes en erreur tolérée avant code de sortie 1 (défaut 0)
    --exemples N         exemples affichés par règle (défaut 3)
    --json               rapport JSON

Code de sortie : 0 si conforme (dans la tolérance), 1 sinon, 2 si erreur d'usage.
Bibliothèque standard uniquement. Lecture seule : ne modifie rien, nulle part.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ERREUR, AVERT = "ERREUR", "AVERTISSEMENT"

DEFAULTS = {
    "required": ["time", "level", "msg"],
    "levels": ["trace", "debug", "info", "warn", "error", "fatal"],
    "time_field": "time",
    "level_field": "level",
    "msg_field": "msg",
    "error_field": "err",
    "max_line_bytes": 16384,
    "sensitive_keys": ["password", "passwd", "pwd", "secret", "token", "access_token", "refresh_token",
                       "authorization", "cookie", "set-cookie", "api_key", "apikey", "client_secret",
                       "private_key"],
    "censor_values": ["[masqué]", "[redacted]", "[REDACTED]", "***", "[Redacted]", "[FILTERED]", ""],
    "pii_email": True,
    "msg_variable_min_distinct": 5,
}

CRI_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\S+)\s+(stdout|stderr)\s+([FP])\s?(.*)$")
STACK_FRAME_RE = re.compile(r"^\s+at\s+\S|^\s*(\w*Error|Exception)(:|\s)|^\s*\.\.\. \d+ more")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})$")
SECRET_VALUE_PATTERNS = [
    ("JWT", re.compile(r"\beyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}")),
    ("en-tête Bearer", re.compile(r"\bBearer\s+[\w\-.=~+/]{12,}", re.I)),
    ("clé AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("clé privée", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("mot de passe dans une URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s@/]{3,}@", re.I)),
]
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
TEMPLATE_SUBS = [
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<uuid>"),
    (re.compile(r"\b[0-9a-f]{12,}\b", re.I), "<hex>"),
    (EMAIL_RE, "<email>"),
    (re.compile(r"\d+(\.\d+)?"), "<n>"),
]


@dataclass
class Report:
    source: str
    total: int = 0
    valid: int = 0
    lines_in_error: int = 0
    levels: Counter = field(default_factory=Counter)
    rules: dict = field(default_factory=lambda: defaultdict(lambda: {"level": "", "count": 0, "examples": []}))
    msg_templates: dict = field(default_factory=lambda: defaultdict(set))

    def hit(self, code, level, example, max_examples):
        r = self.rules[code]
        r["level"] = level
        r["count"] += 1
        if len(r["examples"]) < max_examples:
            r["examples"].append(example[:300])


# ------------------------------------------------------------------ sources

def iter_files(paths):
    if not paths:
        yield from sys.stdin
        return
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as fh:
            yield from fh


def strip_cri(lines):
    """Retire le préfixe CRI des fichiers de /var/log/pods et recolle les lignes partielles (P)."""
    buf = ""
    for raw in lines:
        raw = raw.rstrip("\n")
        m = CRI_RE.match(raw)
        if not m:
            if buf:
                yield buf
                buf = ""
            yield raw
            continue
        buf += m.group(4)
        if m.group(3) == "F":
            yield buf
            buf = ""
    if buf:
        yield buf


def iter_kubectl(args: str):
    cmd = ["kubectl", "logs", *shlex.split(args)]
    if "--prefix" in cmd:
        raise SystemExit("--prefix ajoute un préfixe non JSON : retirez-le")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        raise SystemExit("kubectl introuvable")
    if p.returncode != 0:
        raise SystemExit(f"kubectl logs a échoué : {p.stderr.strip()}")
    yield from p.stdout.splitlines()


def parse_duration(s: str) -> int:
    m = re.fullmatch(r"(\d+)([smhd])", s)
    if not m:
        raise SystemExit(f"durée invalide : {s} (ex. 30m, 1h, 2d)")
    return int(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


def iter_loki(url: str, query: str, since: str, limit: int, headers: list[str]):
    end = time.time_ns()
    start = end - parse_duration(since) * 10**9
    qs = urllib.parse.urlencode({"query": query, "start": start, "end": end,
                                 "limit": limit, "direction": "backward"})
    req = urllib.request.Request(f"{url.rstrip('/')}/loki/api/v1/query_range?{qs}")
    for h in headers:
        k, _, v = h.partition(":")
        req.add_header(k.strip(), v.strip())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
    except Exception as e:  # noqa: BLE001 - message lisible pour l'utilisateur
        raise SystemExit(f"requête Loki échouée : {e}")
    if data.get("status") != "success":
        raise SystemExit(f"Loki a répondu : {data}")
    for stream in data.get("data", {}).get("result", []):
        for value in stream.get("values", []):
            yield value[1]   # [ts, ligne] ou [ts, ligne, structured_metadata]


# ------------------------------------------------------------------ règles

def template(msg: str) -> str:
    t = msg
    for rx, rep in TEMPLATE_SUBS:
        t = rx.sub(rep, t)
    return t


def walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            yield p, k, v
            yield from walk(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")


def check_line(line: str, rep: Report, cfg: dict, ex: int, prev_was_json: bool) -> bool:
    """Retourne True si la ligne était un JSON valide (pour détecter les stacks éclatées)."""
    rep.total += 1
    errors = []

    def err(code, level, msg=None):
        rep.hit(code, level, msg or line, ex)
        if level == ERREUR:
            errors.append(code)

    if not line.strip():
        rep.total -= 1
        return prev_was_json

    if len(line.encode()) > cfg["max_line_bytes"]:
        err("TAILLE", AVERT, f"{len(line.encode())} octets : {line[:120]}…")

    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        obj = None
    if not isinstance(obj, dict):
        if STACK_FRAME_RE.search(line):
            err("STACK-ECLATEE", ERREUR)
        else:
            err("PAS-JSON", ERREUR)
        rep.lines_in_error += 1
        return False

    for f in cfg["required"]:
        if f not in obj:
            err("CHAMP-MANQUANT", ERREUR, f"« {f} » absent : {line}")

    lvl = obj.get(cfg["level_field"])
    if lvl is not None:
        if isinstance(lvl, (int, float)):
            err("NIVEAU-NUMERIQUE", ERREUR, f"level={lvl} : {line}")
        elif str(lvl).lower() not in cfg["levels"]:
            err("NIVEAU-INCONNU", ERREUR, f"level={lvl!r} : {line}")
        else:
            rep.levels[str(lvl).lower()] += 1

    t = obj.get(cfg["time_field"])
    if t is not None and not (isinstance(t, str) and ISO_RE.match(t)):
        err("TIME-NON-ISO", AVERT, f"time={t!r} : {line}")

    msg = obj.get(cfg["msg_field"])
    if cfg["msg_field"] in obj and (not isinstance(msg, str) or not msg.strip()):
        err("MSG-VIDE", AVERT)
    elif isinstance(msg, str):
        rep.msg_templates[template(msg)].add(msg)

    e = obj.get(cfg["error_field"])
    if e is not None and not (isinstance(e, dict) and "message" in e):
        err("ERR-NON-SERIALISEE", AVERT, f"{cfg['error_field']}={str(e)[:80]!r} : objet {{type, message, stack}} attendu")
    if isinstance(obj.get("stack"), str) and cfg["error_field"] not in obj:
        err("ERR-NON-SERIALISEE", AVERT, "« stack » à la racine : loguer { err } pour une erreur structurée")

    sens = {k.lower() for k in cfg["sensitive_keys"]}
    censors = set(cfg["censor_values"])
    for path, key, value in walk(obj):
        if str(key).lower() in sens and not isinstance(value, (dict, list)) and value not in censors and value is not None:
            err("SECRET-CLE", ERREUR, f"« {path} » non masqué : {line[:160]}")
        if isinstance(value, str):
            for label, rx in SECRET_VALUE_PATTERNS:
                if rx.search(value):
                    err("SECRET-VALEUR", ERREUR, f"{label} dans « {path} »")
                    break
            if cfg["pii_email"] and EMAIL_RE.search(value):
                err("PII-EMAIL", AVERT, f"adresse e-mail dans « {path} »")

    if errors:
        rep.lines_in_error += 1
    else:
        rep.valid += 1
    return True


def finalize(rep: Report, cfg: dict, ex: int):
    for tpl, variants in rep.msg_templates.items():
        if len(variants) >= cfg["msg_variable_min_distinct"]:
            r = rep.rules["MSG-VARIABLE"]
            r["level"] = AVERT
            r["count"] += 1
            if len(r["examples"]) < ex:
                sample = ", ".join(sorted(variants)[:3])
                r["examples"].append(f"« {tpl} » ({len(variants)} variantes, ex. {sample})"[:300])


# ------------------------------------------------------------------ sortie

EXPLAIN = {
    "PAS-JSON": "ligne qui n'est pas un objet JSON : sortie hors logger (console.log, npm, runtime)",
    "STACK-ECLATEE": "ligne de stack trace isolée : une erreur écrite en texte multi-lignes, à loguer en { err }",
    "CHAMP-MANQUANT": "champ obligatoire absent",
    "NIVEAU-NUMERIQUE": "niveau en nombre (pino sans formatters.level)",
    "NIVEAU-INCONNU": "niveau hors de la liste autorisée",
    "TIME-NON-ISO": "horodatage non ISO 8601 (epoch en ms ?)",
    "MSG-VIDE": "message vide ou non textuel",
    "MSG-VARIABLE": "message non stable : des valeurs variables dans msg, à mettre dans des champs",
    "ERR-NON-SERIALISEE": "erreur non structurée",
    "SECRET-CLE": "champ sensible non masqué (redact)",
    "SECRET-VALEUR": "valeur qui ressemble à un secret",
    "PII-EMAIL": "donnée personnelle (e-mail)",
    "TAILLE": "ligne trop longue (objet entier logué ?)",
}


def render(rep: Report, tolerance: float) -> str:
    ratio = rep.lines_in_error / rep.total if rep.total else 0
    ok = rep.total > 0 and ratio <= tolerance
    out = [f"# Validation des logs : {rep.source}", "",
           f"**{'CONFORME' if ok else 'NON CONFORME'}** : {rep.valid}/{rep.total} lignes conformes, "
           f"{rep.lines_in_error} en erreur ({ratio:.1%}, tolérance {tolerance:.1%})"]
    if rep.total == 0:
        out.append("\nAucune ligne lue : vérifiez la source (sélecteur, période, labels).")
    if rep.levels:
        out.append("\nNiveaux : " + ", ".join(f"{k} = {v}" for k, v in rep.levels.most_common()))
    for level in (ERREUR, AVERT):
        items = sorted(((c, r) for c, r in rep.rules.items() if r["level"] == level), key=lambda x: -x[1]["count"])
        if items:
            out += ["", f"## {level}", ""]
            for code, r in items:
                out.append(f"- `{code}` × {r['count']} : {EXPLAIN.get(code, '')}")
                for e in r["examples"]:
                    out.append(f"    - {e}")
    return "\n".join(out) + "\n"


def load_config(path: str | None) -> dict:
    cfg = dict(DEFAULTS)
    p = Path(path) if path else Path(".kube-logs.json")
    if path or p.is_file():
        try:
            cfg.update(json.loads(p.read_text()))
        except (OSError, json.JSONDecodeError) as e:
            raise SystemExit(f"config illisible ({p}) : {e}")
    return cfg


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--kubectl", metavar="ARGS")
    ap.add_argument("--loki", metavar="URL")
    ap.add_argument("--query")
    ap.add_argument("--since", default="1h")
    ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--header", action="append", default=[], help="en-tête HTTP pour Loki, ex. 'X-Scope-OrgID: prod'")
    ap.add_argument("--config")
    ap.add_argument("--tolerance", type=float, default=0.0)
    ap.add_argument("--exemples", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if sum(bool(x) for x in (a.files, a.kubectl, a.loki)) > 1:
        ap.error("une seule source à la fois : fichiers/stdin, --kubectl ou --loki")
    if a.loki and not a.query:
        ap.error("--loki demande --query")
    cfg = load_config(a.config)

    if a.kubectl:
        source, lines = f"kubectl logs {a.kubectl}", iter_kubectl(a.kubectl)
    elif a.loki:
        source, lines = f"Loki {a.query} ({a.since})", iter_loki(a.loki, a.query, a.since, a.limit, a.header)
    else:
        source, lines = (", ".join(a.files) or "stdin"), strip_cri(iter_files(a.files))

    rep = Report(source=source)
    prev = True
    for line in lines:
        prev = check_line(line.rstrip("\n"), rep, cfg, a.exemples, prev)
    finalize(rep, cfg, a.exemples)

    ratio = rep.lines_in_error / rep.total if rep.total else 0
    ok = rep.total > 0 and ratio <= a.tolerance
    if a.json:
        print(json.dumps({"source": rep.source, "conforme": ok, "total": rep.total, "valides": rep.valid,
                          "en_erreur": rep.lines_in_error, "niveaux": dict(rep.levels),
                          "regles": {k: v for k, v in rep.rules.items()}}, ensure_ascii=False, indent=2))
    else:
        print(render(rep, a.tolerance), end="")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
