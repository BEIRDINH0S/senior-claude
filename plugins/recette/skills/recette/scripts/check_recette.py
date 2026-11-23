#!/usr/bin/env python3
"""Vérifie un cahier de recette (standard recette) et propose le go / no-go.

Usage :
    check_recette.py [DOSSIER]                   vérifie tout (défaut : ./recette)
    check_recette.py DOSSIER --campagne NOM      vérifie et calcule le go/no-go de cette campagne
    check_recette.py DOSSIER --campagne NOM --pv génère aussi le PV (pv.md, ou pv.proposition.md s'il existe)
    options : --json, --today AAAA-MM-JJ

Sans --campagne, le go/no-go porte sur la campagne la plus récente (ordre des noms de dossier).
Code de sortie : 0 sans erreur, 1 s'il y a au moins une erreur, 2 si usage invalide.
Bibliothèque standard uniquement. Le script PROPOSE une décision ; ce sont des humains qui décident.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import unquote

ERREUR, AVERT, INFO = "ERREUR", "AVERTISSEMENT", "INFO"
PRIORITES = {"haute", "moyenne", "basse"}
TYPES = {"fonctionnel", "non-regression", "securite", "performance", "technique"}
SEVERITES = {"bloquante", "majeure", "mineure"}
STATUTS_ANO = {"ouverte", "en correction", "corrigee", "fermee", "rejetee"}
ANO_FERMEES = {"fermee", "rejetee"}
STATUTS_EXEC = {"ok", "ko", "bloque", "non execute"}
STRAT_SECTIONS = [("perimetre", "Périmètre"), ("hors perimetre", "Hors périmètre"), ("environnement", "Environnement"),
                  ("donnees", "Données de test"), ("roles", "Rôles"), ("criteres d'entree", "Critères d'entrée"),
                  ("criteres de sortie", "Critères de sortie")]
DEFAULT_CRITERES = {"go_bloquantes_max": 0, "go_majeures_max": 0, "go_taux_reussite_min": 95,
                    "go_priorite_haute_executee": 100}
VAGUE_RE = re.compile(
    r"^(ok|ras|ca marche|ca fonctionne|fonctionne( bien| correctement)?|tout fonctionne|correct(ement)?|"
    r"conforme|bien|valide|c'est bon|pas d'erreur|aucune erreur|comme prevu|comme attendu|resultat attendu|"
    r"l'ecran s'affiche( correctement| bien)?|la page s'affiche( correctement| bien)?|s'affiche( correctement| bien)?|"
    r"le traitement (est )?ok|succes|reussi)\.?$")


@dataclass
class Finding:
    level: str
    code: str
    message: str
    file: str = ""


@dataclass
class Report:
    root: str
    findings: list = field(default_factory=list)

    def add(self, level, code, msg, file=""):
        self.findings.append(Finding(level, code, msg, str(file)))

    def count(self, level):
        return sum(f.level == level for f in self.findings)


# ------------------------------------------------------------------ lecture

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def front_matter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        line = line.split("#", 1)[0].rstrip()
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip("[]").strip()
    return meta, text[m.end():]


def headings(text: str) -> list[str]:
    return [norm(m.group(1)) for m in re.finditer(r"^#{1,6}\s+(.+)$", text, re.M)]


def section(text: str, keyword: str) -> str:
    """Contenu sous le premier titre contenant keyword (jusqu'au titre suivant de même niveau ou plus haut)."""
    lines = text.splitlines()
    out, level = [], None
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            if level is not None and len(m.group(1)) <= level:
                break
            if level is None and keyword in norm(m.group(2)):
                level = len(m.group(1))
                continue
        if level is not None:
            out.append(line)
    return "\n".join(out)


def tables(text: str) -> list[list[dict]]:
    """Tous les tableaux Markdown : liste de lignes {entête normalisée: cellule}."""
    result, block = [], []
    for line in text.splitlines() + [""]:
        if line.strip().startswith("|"):
            block.append(line.strip())
            continue
        if len(block) >= 2 and re.match(r"^\|[\s:|-]+\|$", block[1]):
            head = [norm(c) for c in block[0].strip("|").split("|")]
            rows = []
            for row in block[2:]:
                cells = [c.strip() for c in row.strip("|").split("|")]
                cells += [""] * (len(head) - len(cells))
                rows.append(dict(zip(head, cells)))
            result.append(rows)
        block = []
    return result


def col(row: dict, *names) -> str:
    for n in names:
        for k, v in row.items():
            if k.startswith(n):
                return v
    return ""


def split_list(v: str) -> list[str]:
    return [x.strip() for x in re.split(r"[,\s]+", v or "") if x.strip()]


# ------------------------------------------------------------------ modèle

def load(root: Path, rep: Report):
    data = {"criteres": dict(DEFAULT_CRITERES), "exigences": {}, "cas": {}, "anomalies": {}, "application": ""}

    strat = root / "strategie.md"
    if not strat.is_file():
        rep.add(ERREUR, "STRUCT", "strategie.md absent")
    else:
        meta, body = front_matter(read(strat))
        data["application"] = meta.get("application", "")
        heads = headings(body)
        for key, label in STRAT_SECTIONS:
            if not any(key in h for h in heads):
                rep.add(ERREUR, "STRAT-SECTION", f"section « {label} » absente", "strategie.md")
        for k, default in DEFAULT_CRITERES.items():
            if k in meta:
                try:
                    data["criteres"][k] = float(meta[k])
                except ValueError:
                    rep.add(ERREUR, "STRAT-CRITERES", f"{k} n'est pas un nombre : {meta[k]}", "strategie.md")
            else:
                rep.add(AVERT, "STRAT-CRITERES", f"{k} absent de l'en-tête : valeur par défaut {default}", "strategie.md")

    ex = root / "exigences.md"
    if not ex.is_file():
        rep.add(ERREUR, "STRUCT", "exigences.md absent")
    else:
        for t in tables(read(ex)):
            for row in t:
                eid = col(row, "id")
                if not re.match(r"^EX-\d+", eid):
                    continue
                if eid in data["exigences"]:
                    rep.add(ERREUR, "EXIG-DOUBLON", f"{eid} défini deux fois", "exigences.md")
                prio = norm(col(row, "priorite"))
                if prio not in PRIORITES:
                    rep.add(ERREUR, "EXIG-PRIORITE", f"{eid} : priorité « {col(row, 'priorite')} » (haute, moyenne, basse)", "exigences.md")
                data["exigences"][eid] = {"texte": col(row, "exigence"), "priorite": prio}

    cdir = root / "cas"
    if not cdir.is_dir():
        rep.add(ERREUR, "STRUCT", "dossier cas/ absent")
    else:
        for p in sorted(cdir.glob("*.md")):
            if p.name.startswith("_"):
                continue
            load_case(p, root, data, rep)

    an = root / "anomalies.md"
    if an.is_file():
        for t in tables(read(an)):
            for row in t:
                aid = col(row, "id")
                if not re.match(r"^AN-\d+", aid):
                    continue
                sev, st = norm(col(row, "severite")), norm(col(row, "statut"))
                if sev not in SEVERITES:
                    rep.add(ERREUR, "ANO-SEVERITE", f"{aid} : sévérité « {col(row, 'severite')} » (bloquante, majeure, mineure)", "anomalies.md")
                if st not in STATUTS_ANO:
                    rep.add(ERREUR, "ANO-STATUT", f"{aid} : statut « {col(row, 'statut')} »", "anomalies.md")
                data["anomalies"][aid] = {"titre": col(row, "titre"), "severite": sev, "statut": st,
                                          "cas": split_list(col(row, "cas")), "echeance": col(row, "echeance"),
                                          "ticket": col(row, "ticket")}
    return data


def load_case(p: Path, root: Path, data: dict, rep: Report):
    rel = p.relative_to(root).as_posix()
    meta, body = front_matter(read(p))
    for k in ("id", "titre", "exigences", "priorite"):
        if not meta.get(k):
            rep.add(ERREUR, "CAS-CHAMP", f"champ « {k} » absent de l'en-tête", rel)
    cid = meta.get("id", p.stem)
    if meta.get("id") and not p.stem.startswith(meta["id"]):
        rep.add(AVERT, "CAS-ID-FICHIER", f"id {meta['id']} ≠ nom de fichier", rel)
    prio = norm(meta.get("priorite", ""))
    if meta.get("priorite") and prio not in PRIORITES:
        rep.add(ERREUR, "CAS-CHAMP", f"priorité « {meta['priorite']} » (haute, moyenne, basse)", rel)
    if meta.get("type") and norm(meta["type"]) not in TYPES:
        rep.add(AVERT, "CAS-CHAMP", f"type « {meta['type']} » ({', '.join(sorted(TYPES))})", rel)
    exigs = split_list(meta.get("exigences", ""))
    heads = headings(body)
    for key, label in (("precondition", "Préconditions"), ("donnees", "Données"), ("etapes", "Étapes")):
        if not any(key in h for h in heads):
            rep.add(ERREUR, "CAS-SECTION", f"section « {label} » absente", rel)
    if any("donnees" in h for h in heads):
        d = norm(re.sub(r"<!--.*?-->", "", section(body, "donnees"), flags=re.S))
        if not d or d in ("-", "n/a", "na", "aucune", "todo"):
            rep.add(AVERT, "CAS-DONNEES-VIDES", "section Données vide : préciser compte, jeu de données, valeurs saisies", rel)
    steps = []
    for t in tables(section(body, "etapes")):
        steps += t
    if any("etapes" in h for h in heads) and not steps:
        rep.add(ERREUR, "CAS-ETAPES", "aucune étape dans le tableau", rel)
    for i, row in enumerate(steps, 1):
        att = col(row, "resultat attendu", "attendu")
        n = col(row, "#") or str(i)
        if not att.strip():
            rep.add(ERREUR, "CAS-ATTENDU-VIDE", f"étape {n} sans résultat attendu", rel)
        elif VAGUE_RE.match(norm(att)):
            rep.add(AVERT, "CAS-ATTENDU-VAGUE", f"étape {n} : « {att} » n'est pas vérifiable (quelle valeur, quel libellé, quel état ?)", rel)
    data["cas"][cid] = {"titre": meta.get("titre", ""), "exigences": exigs, "priorite": prio, "fichier": rel}


def check_links(data: dict, rep: Report):
    for cid, c in data["cas"].items():
        for e in c["exigences"]:
            if e not in data["exigences"]:
                rep.add(ERREUR, "CAS-EXIGENCE-INCONNUE", f"{cid} couvre {e}, absente d'exigences.md", c["fichier"])
    covered = {e for c in data["cas"].values() for e in c["exigences"]}
    for e in data["exigences"]:
        if e not in covered:
            rep.add(ERREUR, "EXIGENCE-NON-COUVERTE", f"{e} n'est couverte par aucun cas", "exigences.md")
    for aid, a in data["anomalies"].items():
        for c in a["cas"]:
            if c not in data["cas"]:
                rep.add(AVERT, "ANO-CAS-INCONNU", f"{aid} rattachée à {c}, cas inexistant", "anomalies.md")
        if a["statut"] not in ANO_FERMEES and not re.match(r"\d{4}-\d{2}-\d{2}", a["echeance"]):
            rep.add(AVERT, "ANO-SANS-ECHEANCE", f"{aid} ouverte sans échéance (AAAA-MM-JJ) : impossible d'en faire une réserve", "anomalies.md")


# ------------------------------------------------------------------ campagnes

def load_campaign(cdir: Path, root: Path, data: dict, rep: Report):
    f = cdir / "campagne.md"
    rel = f.relative_to(root).as_posix()
    if not f.is_file():
        rep.add(ERREUR, "STRUCT", "campagne.md absent", cdir.relative_to(root).as_posix())
        return None
    meta, body = front_matter(read(f))
    for k in ("version", "environnement"):
        if not meta.get(k):
            rep.add(ERREUR, "CAMP-CHAMP", f"« {k} » absent de l'en-tête", rel)
    rows = []
    for t in tables(section(body, "execution") or body):
        rows += [r for r in t if re.match(r"^CT-\d+", col(r, "cas"))]
    execs = {}
    for r in rows:
        cid, st = col(r, "cas"), norm(col(r, "statut"))
        if cid not in data["cas"]:
            rep.add(ERREUR, "CAMP-CAS-INCONNU", f"{cid} n'existe pas dans cas/", rel)
        if st not in STATUTS_EXEC:
            rep.add(ERREUR, "CAMP-STATUT", f"{cid} : statut « {col(r, 'statut')} » (OK, KO, bloqué, non exécuté)", rel)
        anos = re.findall(r"AN-\d+", col(r, "anomalie"))
        if st == "ko" and not anos:
            rep.add(ERREUR, "CAMP-KO-SANS-ANOMALIE", f"{cid} en KO sans anomalie référencée", rel)
        for a in anos:
            if a not in data["anomalies"]:
                rep.add(ERREUR, "CAMP-ANOMALIE-INCONNUE", f"{cid} référence {a}, absente d'anomalies.md", rel)
        proof = col(r, "preuve")
        links = re.findall(r"\]\(([^)]+)\)", proof)
        if st in ("ok", "ko") and not (links or proof.strip()):
            rep.add(AVERT, "CAMP-PREUVE-MANQUANTE", f"{cid} ({col(r, 'statut')}) sans preuve", rel)
        for l in links:
            if not re.match(r"^[a-z]+://", l) and not (cdir / unquote(l)).exists():
                rep.add(ERREUR, "CAMP-PREUVE-INTROUVABLE", f"{cid} : preuve « {l} » introuvable", rel)
        execs[cid] = st
    for cid in data["cas"]:
        if cid not in execs:
            rep.add(INFO, "CAMP-CAS-ABSENT", f"{cid} n'apparaît pas dans la campagne", rel)
    camp = {"nom": cdir.name, "dir": cdir, "meta": meta, "execs": execs}
    pv = cdir / "pv.md"
    if pv.is_file():
        opened = [a for a, x in data["anomalies"].items() if x["statut"] not in ANO_FERMEES]
        if "sans reserve" in norm(read(pv)) and opened and re.search(r"\[x\]\s*go\s*$|\[x\]\s*go sans reserve", norm(read(pv)), re.M):
            rep.add(ERREUR, "PV-INCOHERENT", f"PV « sans réserve » coché alors que {len(opened)} anomalie(s) restent ouvertes : {', '.join(opened)}",
                    pv.relative_to(root).as_posix())
    return camp


def decide(camp: dict, data: dict) -> dict:
    cr = data["criteres"]
    ex = camp["execs"]
    n = {s: sum(1 for v in ex.values() if v == s) for s in STATUTS_EXEC}
    executed = n["ok"] + n["ko"] + n["bloque"]
    taux = 100.0 * n["ok"] / executed if executed else 0.0
    hautes = [c for c, x in data["cas"].items() if x["priorite"] == "haute"]
    hautes_exec = [c for c in hautes if ex.get(c) in ("ok", "ko")]
    taux_haute = 100.0 * len(hautes_exec) / len(hautes) if hautes else 100.0
    opened = {a: x for a, x in data["anomalies"].items() if x["statut"] not in ANO_FERMEES}
    by_sev = {s: sorted(a for a, x in opened.items() if x["severite"] == s) for s in SEVERITES}
    covered = {e for c in ex if c in data["cas"] for e in data["cas"][c]["exigences"]
               if ex[c] in ("ok", "ko")}
    crit = [
        ("Anomalies bloquantes ouvertes", f"≤ {cr['go_bloquantes_max']:g}", len(by_sev["bloquante"]), len(by_sev["bloquante"]) <= cr["go_bloquantes_max"]),
        ("Anomalies majeures ouvertes", f"≤ {cr['go_majeures_max']:g}", len(by_sev["majeure"]), len(by_sev["majeure"]) <= cr["go_majeures_max"]),
        ("Taux de réussite des cas exécutés", f"≥ {cr['go_taux_reussite_min']:g} %", f"{taux:.1f} %", taux >= cr["go_taux_reussite_min"]),
        ("Cas de priorité haute exécutés", f"≥ {cr['go_priorite_haute_executee']:g} %", f"{taux_haute:.0f} % ({len(hautes_exec)}/{len(hautes)})", taux_haute >= cr["go_priorite_haute_executee"]),
    ]
    if not all(c[3] for c in crit):
        decision = "NO-GO"
    elif opened:
        decision = "GO AVEC RÉSERVES"
    else:
        decision = "GO"
    return {"n": n, "executes": executed, "taux": taux, "taux_haute": taux_haute, "ouvertes": opened,
            "par_severite": by_sev, "criteres": crit, "decision": decision,
            "couverture": (len(covered), len(data["exigences"]))}


# ------------------------------------------------------------------ PV

def pv_markdown(camp: dict, data: dict, d: dict, today: str) -> str:
    m = camp["meta"]
    n = d["n"]
    L = [f"# PV de recette : {data['application'] or 'application'} v{m.get('version', '?')}", "",
         "> Généré par `check_recette.py` le " + today + ". La décision ci-dessous est une **proposition** calculée "
         "à partir des critères de la stratégie : elle est relue, complétée et **signée par des humains**.", "",
         "| | |", "|---|---|",
         f"| **Application** | {data['application'] or '—'} |",
         f"| **Version recettée** | {m.get('version', '—')} |",
         f"| **Environnement** | {m.get('environnement', '—')} |",
         f"| **Période** | {m.get('debut', '—')} → {m.get('fin', '—')} |",
         f"| **Campagne** | `{camp['nom']}` |", "",
         "## Bilan", "",
         "| Cas prévus | OK | KO | Bloqués | Non exécutés | Taux de réussite | Exigences couvertes |",
         "|---|---|---|---|---|---|---|",
         f"| {len(camp['execs'])} | {n['ok']} | {n['ko']} | {n['bloque']} | {n['non execute']} | {d['taux']:.1f} % | {d['couverture'][0]} / {d['couverture'][1]} |", "",
         "## Critères de sortie", "", "| Critère | Seuil | Constaté | Respecté |", "|---|---|---|---|"]
    for name, seuil, val, ok in d["criteres"]:
        L.append(f"| {name} | {seuil} | {val} | {'oui' if ok else '**NON**'} |")
    L += ["", "## Anomalies ouvertes", ""]
    if not d["ouvertes"]:
        L.append("Aucune.")
    else:
        L += ["| ID | Titre | Sévérité | Statut | Échéance | Ticket |", "|---|---|---|---|---|---|"]
        for a, x in sorted(d["ouvertes"].items(), key=lambda kv: (["bloquante", "majeure", "mineure"].index(kv[1]["severite"]) if kv[1]["severite"] in SEVERITES else 9, kv[0])):
            L.append(f"| {a} | {x['titre']} | {x['severite']} | {x['statut']} | {x['echeance'] or '**à fixer**'} | {x['ticket']} |")
    L += ["", "## Réserves", ""]
    reserves = {a: x for a, x in d["ouvertes"].items() if x["severite"] in ("majeure", "mineure")}
    if d["decision"] == "GO AVEC RÉSERVES" and reserves:
        L.append("En cas d'acceptation, les anomalies suivantes sont levées comme **réserves**, à corriger avant leur échéance :")
        L.append("")
        for a, x in sorted(reserves.items()):
            L.append(f"- **{a}** ({x['severite']}) : {x['titre']}. Échéance : {x['echeance'] or '**à fixer**'}.")
    else:
        L.append("Sans objet." if d["decision"] == "GO" else "Sans objet tant que la décision est NO-GO.")
    L += ["", "## Décision", "",
          f"**Décision proposée par les critères : {d['decision']}**", "",
          "Décision prise :", "",
          "- [ ] GO sans réserve",
          "- [ ] GO avec réserves (liste ci-dessus)",
          "- [ ] NO-GO",
          "", "Justification (obligatoire si la décision prise diffère de la proposition) :", "", "> ", "",
          "## Prérequis de mise en production", "",
          "- [ ] Procédure de rollback écrite et testée",
          "- [ ] Sauvegarde des données prévue juste avant la MEP",
          "- [ ] Checklist de mise en production revue",
          "- [ ] Utilisateurs et support informés (date, impacts, contact)", "",
          "## Signatures", "",
          "| Rôle | Nom | Fonction | Date | Signature |", "|---|---|---|---|---|",
          "| Métier (MOA) | | | | |", "| Équipe projet (MOE) | | | | |", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ sortie

def render(rep: Report, camp, d) -> str:
    e, w, i = rep.count(ERREUR), rep.count(AVERT), rep.count(INFO)
    out = [f"# Vérification de la recette : {rep.root}", "",
           f"**{'CONFORME' if e == 0 else 'NON CONFORME'}** : {e} erreur(s), {w} avertissement(s), {i} info(s)"]
    if camp and d:
        out += ["", f"## Go / no-go : campagne `{camp['nom']}` (v{camp['meta'].get('version', '?')})", "",
                f"**Décision proposée : {d['decision']}**", ""]
        for name, seuil, val, ok in d["criteres"]:
            out.append(f"- {'✔' if ok else '✘'} {name} : {val} (seuil {seuil})")
        if d["ouvertes"]:
            out.append("- Anomalies ouvertes : " + ", ".join(f"{a} ({x['severite']})" for a, x in sorted(d["ouvertes"].items())))
    for lvl in (ERREUR, AVERT, INFO):
        items = [f for f in rep.findings if f.level == lvl]
        if items:
            out += ["", f"## {lvl} ({len(items)})", ""]
            out += [f"- `{f.code}` {f.file + ' : ' if f.file else ''}{f.message}" for f in items]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier", nargs="?", default="recette")
    ap.add_argument("--campagne")
    ap.add_argument("--pv", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    root = Path(a.dossier)
    if not root.is_dir():
        print(f"dossier introuvable : {root}", file=sys.stderr)
        return 2
    today = a.today or dt.date.today().isoformat()
    rep = Report(str(root))
    data = load(root, rep)
    check_links(data, rep)

    camps_dir = root / "campagnes"
    dirs = sorted(p for p in camps_dir.iterdir() if p.is_dir()) if camps_dir.is_dir() else []
    if a.campagne:
        target = camps_dir / a.campagne if not Path(a.campagne).is_dir() else Path(a.campagne)
        if not target.is_dir():
            print(f"campagne introuvable : {a.campagne}", file=sys.stderr)
            return 2
        dirs = [target]
    camps = [c for c in (load_campaign(dd, root, data, rep) for dd in dirs) if c]
    camp = camps[-1] if camps else None
    d = decide(camp, data) if camp else None

    pv_path = None
    if a.pv:
        if not camp:
            print("--pv demande une campagne", file=sys.stderr)
            return 2
        pv_path = camp["dir"] / ("pv.proposition.md" if (camp["dir"] / "pv.md").exists() else "pv.md")
        pv_path.write_text(pv_markdown(camp, data, d, today), encoding="utf-8")

    if a.json:
        print(json.dumps({"racine": rep.root, "findings": [asdict(f) for f in rep.findings],
                          "campagne": camp["nom"] if camp else None,
                          "decision": d["decision"] if d else None,
                          "criteres": [{"critere": c[0], "seuil": c[1], "constate": str(c[2]), "respecte": c[3]} for c in d["criteres"]] if d else [],
                          "pv": str(pv_path) if pv_path else None}, ensure_ascii=False, indent=2))
    else:
        print(render(rep, camp, d), end="")
        if pv_path:
            print(f"\nPV écrit : {pv_path}")
    return 1 if rep.count(ERREUR) else 0


if __name__ == "__main__":
    sys.exit(main())
