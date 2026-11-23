#!/usr/bin/env python3
"""Linter de dashboards Grafana (JSON) selon le standard grafana-dashboards.

Lit le schéma v1 (`panels[]`, rows comprises) et le schéma v2 (`elements` +
`layout`), brut ou enveloppé en ressource Kubernetes (apiVersion/kind/spec).
Bibliothèque standard uniquement.

Usage :
    lint_dashboard.py CHEMIN [CHEMIN ...] [--runbooks DIR] [--max-panels N] [--gauge NOM ...] [--json]

CHEMIN : un fichier .json ou un dossier (parcouru récursivement).
--runbooks : dossier docs/runbooks (plugin ops-doc) pour vérifier les liens
             vers les runbooks et repérer ceux qu'aucun dashboard ne cite.
--gauge    : métrique qui finit par _total/_count mais qui est une jauge
             (répétable) ; s'ajoute à la liste KNOWN_GAUGES.

Code de sortie : 0 sans erreur, 1 avec au moins une erreur, 2 si usage invalide.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ERREUR, AVERT, INFO = "ERREUR", "AVERTISSEMENT", "INFO"

COUNTER_RE = re.compile(r"\b([a-zA-Z_:][\w:]*_(?:total|count|sum|bucket))\b")
RATE_FN_RE = re.compile(r"\b(rate|irate|increase|delta|idelta|resets|changes|deriv)\s*\(")
QUANTILE_RE = re.compile(r"histogram_quantile\s*\(")
FIXED_WINDOW_RE = re.compile(r"\b(?:rate|irate|increase)\s*\([^()]*\[\s*\d+[smhd]\s*\]")
AVG_LATENCY_RE = re.compile(r"_sum\b[^/]*\)?\s*/\s*[^/]*_count\b")
NS_LITERAL_RE = re.compile(r"\bnamespace\s*=~?\s*\"(?!\$)[^\"]+\"")
PER_POD_RE = re.compile(r"\bby\s*\(([^)]*)\)", re.I)
VIZ_NEEDS_UNIT = {"timeseries", "stat", "gauge", "bargauge", "graph"}
STRUCTURAL = {"row", "text", "news", "dashlist", "welcome", "alertlist", "annolist", "nodeGraph"}
# Jauges dont le nom finit comme un compteur : pas de rate() attendu.
KNOWN_GAUGES = {"cnpg_backends_total", "cnpg_pg_replication_slots_total", "kube_node_status_capacity_total",
                "node_filesystem_files_total", "pg_settings_max_connections_total"}
RED_COLORS = re.compile(r"red|#f2495c|#e02f44|#c4162a", re.I)
REFRESH_RE = re.compile(r"^(\d+)(ms|s|m|h|d)$")


@dataclass
class Panel:
    title: str
    kind: str
    raw: dict
    exprs: list[str] = field(default_factory=list)
    hidden: bool = False          # dans une row repliée ou un onglet non premier


@dataclass
class Finding:
    level: str
    code: str
    message: str
    file: str = ""
    panel: str = ""


# ------------------------------------------------------------------ extraction

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from all_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from all_strings(v)


def exprs_of(obj) -> list[str]:
    out = []
    for d in walk(obj):
        for k in ("expr", "query"):
            v = d.get(k)
            if isinstance(v, str) and v.strip():
                out.append(v)
    return out


def unit_of(panel_raw) -> str | None:
    for d in walk(panel_raw):
        fc = d.get("fieldConfig")
        if isinstance(fc, dict):
            u = (fc.get("defaults") or {}).get("unit")
            if u:
                return u
    return None


def unwrap(doc: dict) -> tuple[dict, str]:
    """Retourne (dashboard, schéma) ; gère l'enveloppe Kubernetes et l'export {dashboard: …}."""
    if "spec" in doc and isinstance(doc["spec"], dict) and ("kind" in doc or "apiVersion" in doc):
        spec = dict(doc["spec"])
        spec.setdefault("uid", (doc.get("metadata") or {}).get("name"))
        return spec, "v2" if "elements" in spec else "v1"
    if "dashboard" in doc and isinstance(doc["dashboard"], dict):
        doc = doc["dashboard"]
    return doc, "v2" if "elements" in doc else "v1"


def panels_v1(dash: dict) -> tuple[list[Panel], bool]:
    out = []
    has_collapsed_first = False
    items = sorted(dash.get("panels") or [], key=lambda p: ((p.get("gridPos") or {}).get("y", 0), (p.get("gridPos") or {}).get("x", 0)))
    collapsed_section = False
    for i, p in enumerate(items):
        if p.get("type") == "row":
            collapsed_section = bool(p.get("collapsed"))
            if i == 0 and collapsed_section:
                has_collapsed_first = True
            for sub in p.get("panels") or []:
                out.append(Panel(sub.get("title", ""), sub.get("type", ""), sub, exprs_of(sub.get("targets")), hidden=True))
            continue
        out.append(Panel(p.get("title", ""), p.get("type", ""), p, exprs_of(p.get("targets")), hidden=False))
    return out, has_collapsed_first


def viz_kind_v2(spec: dict) -> str:
    vc = spec.get("vizConfig") or {}
    if vc.get("kind") == "VizConfig":
        return vc.get("group", "")
    return vc.get("kind", "") or vc.get("group", "")


def layout_refs(layout, hidden=False, acc=None):
    """Associe chaque nom d'élément à sa visibilité, en parcourant le layout v2."""
    acc = {} if acc is None else acc
    if not isinstance(layout, dict):
        return acc
    kind, spec = layout.get("kind", ""), layout.get("spec") or {}
    if kind == "ElementReference":
        acc.setdefault(layout.get("name"), hidden)
        return acc
    if kind in ("TabsLayout",):
        for i, tab in enumerate(spec.get("tabs") or []):
            layout_refs((tab.get("spec") or {}).get("layout"), hidden or i > 0, acc)
        return acc
    if kind in ("RowsLayout",):
        for row in spec.get("rows") or []:
            rs = row.get("spec") or {}
            layout_refs(rs.get("layout"), hidden or bool(rs.get("collapse") or rs.get("collapsed")), acc)
        return acc
    for item in spec.get("items") or []:
        el = (item.get("spec") or {}).get("element")
        if el:
            layout_refs(el, hidden, acc)
        sub = (item.get("spec") or {}).get("layout")
        if sub:
            layout_refs(sub, hidden, acc)
    return acc


def panels_v2(dash: dict) -> tuple[list[Panel], bool]:
    elements = dash.get("elements") or {}
    layout = dash.get("layout") or {}
    vis = layout_refs(layout)
    out = []
    for name, el in elements.items():
        if (el.get("kind") or "Panel") not in ("Panel", "LibraryPanel"):
            continue
        spec = el.get("spec") or {}
        out.append(Panel(spec.get("title", ""), viz_kind_v2(spec), spec, exprs_of(spec.get("data")),
                         hidden=vis.get(name, False)))
    return out, layout.get("kind") == "TabsLayout"


# ------------------------------------------------------------------ règles

class Linter:
    def __init__(self, max_panels: int, runbooks: Path | None, gauges=()):
        self.gauges = KNOWN_GAUGES | set(gauges)
        self.findings: list[Finding] = []
        self.max_panels = max_panels
        self.runbooks = runbooks
        self.runbook_names = ({p.stem for p in runbooks.glob("*.md") if not p.name.startswith("_")}
                              if runbooks and runbooks.is_dir() else set())
        self.referenced: set[str] = set()
        self.files = 0

    def add(self, level, code, msg, file="", panel=""):
        self.findings.append(Finding(level, code, msg, file, panel))

    def lint_file(self, path: Path, display: str):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            self.add(ERREUR, "JSON-INVALIDE", f"illisible : {e}", display)
            return
        if not isinstance(doc, dict):
            self.add(ERREUR, "JSON-INVALIDE", "pas un objet JSON de dashboard", display)
            return
        dash, schema = unwrap(doc)
        if "panels" not in dash and "elements" not in dash:
            return   # pas un dashboard (autre fichier JSON du repo)
        self.files += 1
        panels, top_hidden = panels_v2(dash) if schema == "v2" else panels_v1(dash)
        self.dashboard_rules(dash, schema, panels, top_hidden, display)
        all_exprs = [e for p in panels for e in p.exprs]
        has_quantile = any(QUANTILE_RE.search(e) for e in all_exprs)
        for p in panels:
            self.panel_rules(p, display, has_quantile)

    def dashboard_rules(self, dash, schema, panels, top_hidden, f):
        if not dash.get("uid"):
            self.add(AVERT, "UID-MANQUANT", "pas d'UID fixe : les liens des runbooks et des alertes casseront à chaque réimport", f)
        variables = dash.get("variables") if schema == "v2" else (dash.get("templating") or {}).get("list")
        if not variables:
            self.add(INFO, "PAS-DE-VARIABLE", "aucune variable (datasource, namespace) : dashboard figé sur un environnement", f)
        refresh = dash.get("refresh") or ((dash.get("timeSettings") or {}).get("autoRefresh"))
        if isinstance(refresh, str):
            m = REFRESH_RE.match(refresh)
            if m:
                secs = int(m.group(1)) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]
                if secs < 30:
                    self.add(AVERT, "REFRESH-COURT", f"rafraîchissement {refresh} : 30 s à 1 min suffisent", f)
        if schema == "v2" and top_hidden:
            self.add(AVERT, "BANDEAU-CACHE",
                     "premier niveau du layout en onglets : mettre le bandeau de santé dans une row au-dessus des onglets", f)
        if schema == "v1" and top_hidden:
            self.add(AVERT, "BANDEAU-CACHE", "la première row est repliée : l'état de santé n'est pas visible à l'ouverture", f)
        visible = [p for p in panels if not p.hidden and p.kind not in STRUCTURAL]
        if len(visible) > self.max_panels:
            self.add(AVERT, "TROP-DE-PANNEAUX",
                     f"{len(visible)} panneaux visibles sans repli (max {self.max_panels}) : rows repliées ou onglets pour le détail", f)
        text = json.dumps(dash).lower()
        if "loki" not in text and "/explore" not in text and "drilldown" not in text:
            self.add(INFO, "PAS-DE-LIEN-LOGS", "aucun lien vers Loki / Explore : ajouter un lien de données vers les logs", f)
        # source de données en dur
        bad = set()
        for d in walk(dash):
            ds = d.get("datasource")
            if isinstance(ds, dict):
                ref = ds.get("uid") or ds.get("name")
                if isinstance(ref, str) and ref and not ref.startswith("$") and not ref.startswith("${") \
                        and ref not in ("-- Grafana --", "-- Mixed --", "-- Dashboard --", "grafana") \
                        and ds.get("type") != "datasource":
                    bad.add(ref)
            elif isinstance(ds, str) and ds and not ds.startswith("$") and ds not in ("-- Grafana --", "-- Mixed --"):
                bad.add(ds)
        if bad:
            self.add(AVERT, "DS-EN-DUR", f"source(s) de données en dur ({', '.join(sorted(bad))[:80]}) : utiliser ${{datasource}}", f)

    def panel_rules(self, p: Panel, f, has_quantile):
        name = p.title or "(sans titre)"
        if p.kind in STRUCTURAL:
            self.collect_runbook_refs(p, f, name)
            return
        if not p.title.strip():
            self.add(ERREUR, "TITRE-MANQUANT", "panneau sans titre", f, name)
        if not (p.raw.get("description") or "").strip():
            self.add(AVERT, "DESCRIPTION-MANQUANTE", "pas de description (montre / normal / si anormal → runbook)", f, name)
        if p.kind in VIZ_NEEDS_UNIT and not unit_of(p.raw):
            self.add(AVERT, "UNITE-MANQUANTE", "pas d'unité", f, name)
        if p.kind == "piechart":
            self.add(AVERT, "CAMEMBERT", "camembert : préférer une bar gauge triée", f, name)

        for e in p.exprs:
            counters = [c for c in COUNTER_RE.findall(e) if c not in self.gauges]
            if counters and not RATE_FN_RE.search(e):
                self.add(ERREUR, "RATE-MANQUANT", f"compteur {counters[0]} sans rate()/increase() : la valeur brute n'a pas de sens", f, name)
            if QUANTILE_RE.search(e) and not re.search(r"\ble\b", e):
                self.add(ERREUR, "QUANTILE-SANS-LE", "histogram_quantile sans « le » dans l'agrégation : résultat faux", f, name)
            if FIXED_WINDOW_RE.search(e):
                self.add(INFO, "RATE-INTERVAL", "fenêtre fixe dans rate() : préférer [$__rate_interval]", f, name)
            if AVG_LATENCY_RE.search(e) and not has_quantile and re.search(r"duration|latency|seconds|time", e):
                self.add(AVERT, "LATENCE-MOYENNE", "latence en moyenne sans percentile dans le dashboard : ajouter p95/p99", f, name)
            if NS_LITERAL_RE.search(e):
                self.add(AVERT, "NAMESPACE-EN-DUR", "namespace littéral : utiliser $namespace", f, name)
            for grp in PER_POD_RE.findall(e):
                if re.search(r"\b(pod|instance|container)\b", grp):
                    self.add(AVERT, "SERIE-PAR-POD", f"agrégation par ({grp.strip()}) : une série par pod, à réserver au niveau 2", f, name)
                    break
        for d in walk(p.raw):
            lf = d.get("legendFormat")
            if isinstance(lf, str) and re.search(r"\{\{\s*(pod|instance|container)\s*\}\}", lf):
                self.add(AVERT, "SERIE-PAR-POD", f"légende {lf} : une série par pod", f, name)
                break

        has_red = False
        for d in walk(p.raw):
            for step in (d.get("thresholds") or {}).get("steps", []) if isinstance(d.get("thresholds"), dict) else []:
                if isinstance(step, dict) and RED_COLORS.search(str(step.get("color", ""))):
                    has_red = True
        mentions_runbook = self.collect_runbook_refs(p, f, name)
        if has_red and not mentions_runbook:
            self.add(AVERT, "SEUIL-SANS-RUNBOOK", "peut virer au rouge mais ne dit pas quoi faire : lien vers le runbook", f, name)

    def collect_runbook_refs(self, p: Panel, f, name) -> bool:
        found = False
        for s in all_strings(p.raw):
            if "runbook" in s.lower():
                found = True
            for m in re.finditer(r"runbooks/([A-Za-z0-9_.-]+?)(?:\.md)?(?=[)#?\s\"']|$)", s):
                rb = m.group(1)
                self.referenced.add(rb)
                if self.runbooks and self.runbook_names is not None and rb not in self.runbook_names:
                    self.add(ERREUR, "RUNBOOK-INTROUVABLE", f"lien vers runbooks/{rb}.md introuvable dans {self.runbooks}", f, name)
        return found

    def finish(self):
        if self.runbooks:
            for rb in sorted(self.runbook_names - self.referenced):
                self.add(INFO, "RUNBOOK-NON-REFERENCE", f"aucun dashboard ne renvoie au runbook {rb} : son diagnostic n'a pas de panneau", f"runbooks/{rb}.md")


def collect(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for f in sorted(p.rglob("*.json")):
                if not any(part in ("node_modules", ".git") for part in f.parts):
                    yield f
        elif p.is_file():
            yield p


def render(lin: Linter) -> str:
    c = {lvl: sum(f.level == lvl for f in lin.findings) for lvl in (ERREUR, AVERT, INFO)}
    out = ["# Lint des dashboards Grafana", "",
           f"**{'CONFORME' if c[ERREUR] == 0 else 'NON CONFORME'}** : {lin.files} dashboard(s), "
           f"{c[ERREUR]} erreur(s), {c[AVERT]} avertissement(s), {c[INFO]} info(s)"]
    by_code = {}
    for f in lin.findings:
        by_code.setdefault((f.level, f.code), 0)
        by_code[(f.level, f.code)] += 1
    if by_code:
        order = {ERREUR: 0, AVERT: 1, INFO: 2}
        out += ["", "Par règle : " + ", ".join(f"{code} × {n}" for (lvl, code), n in
                                              sorted(by_code.items(), key=lambda x: (order[x[0][0]], -x[1])))]
    for lvl in (ERREUR, AVERT, INFO):
        items = [f for f in lin.findings if f.level == lvl]
        if items:
            out += ["", f"## {lvl} ({len(items)})", ""]
            for f in items:
                where = f.file + (f" › {f.panel}" if f.panel else "")
                out.append(f"- `{f.code}` {where} : {f.message}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--runbooks")
    ap.add_argument("--max-panels", type=int, default=12)
    ap.add_argument("--gauge", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    lin = Linter(a.max_panels, Path(a.runbooks) if a.runbooks else None, a.gauge)
    files = list(collect(a.paths))
    if not files:
        print("aucun fichier .json trouvé", file=sys.stderr)
        return 2
    for f in files:
        lin.lint_file(f, f.as_posix())
    lin.finish()
    if a.json:
        print(json.dumps({"dashboards": lin.files, "findings": [asdict(x) for x in lin.findings]}, ensure_ascii=False, indent=2))
    else:
        print(render(lin), end="")
    return 1 if any(f.level == ERREUR for f in lin.findings) else 0


if __name__ == "__main__":
    sys.exit(main())
