#!/usr/bin/env python3
"""Captures d'écran annotées et reproductibles pour la documentation, via agent-browser.

Une « recette de capture » (JSON, versionnée à côté de la doc) décrit chaque image :
URL, taille de fenêtre, actions pour arriver à l'écran, annotations ancrées sur des
sélecteurs CSS, recadrage, fichier de sortie. Relancer le script régénère toutes les
images quand l'interface change.

Usage :
    capture.py RECETTE.json [--only NOM] [--dry-run] [--agent-browser CMD] [--keep-open]

Format :
{
  "defaults": { "viewport": [1280, 800, 2], "session": "doc", "state": "auth.json",
                "style": { "color": "#E5484D" }, "crop": true },
  "captures": [
    {
      "name": "connexion-1",
      "url": "http://localhost:3000/login",
      "wait": { "selector": "form#login" },
      "steps": [["fill", "#email", "demo@example.org"]],
      "annotations": [
        { "selector": "#email", "label": 1 },
        { "selector": "button[type=submit]", "label": 2, "note": "Valider" },
        { "selector": ".user-email", "type": "blur" }
      ],
      "output": "docs/img/connexion-1.png"
    }
  ]
}
Types d'annotation : box (défaut), spotlight, blur. Options : label, note, side.
Recadrage : "crop": true (défaut, autour des annotations), "crop": "<sélecteur>"
(sur un conteneur, ex. "main" ou ".modal"), "crop": false (écran entier).

Bibliothèque standard uniquement (plus agent-browser). Code de sortie 1 si une
capture échoue (sélecteur introuvable, commande en erreur).
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

ANNOTATE_JS = HERE / "annotate.js"


def build_eval(spec: dict) -> str:
    """Expression JS autonome : pose la spec puis exécute le calque d'annotations."""
    src = ANNOTATE_JS.read_text(encoding="utf-8")
    src = re.sub(r"^\s*/\*.*?\*/\s*", "", src, count=1, flags=re.S)   # pas de saut de ligne après return
    return "(function(){window.__DOC_SPEC__=" + json.dumps(spec, ensure_ascii=False) + ";return " + src.strip() + ";})()"


class Runner:
    def __init__(self, cmd: str, dry: bool):
        self.base = shlex.split(cmd)
        self.dry = dry
        self.log: list[list[str]] = []

    def __call__(self, args: list[str], glob: list[str] | None = None, want_json=False):
        full = self.base + (glob or []) + (["--json"] if want_json else []) + args
        self.log.append(full)
        if self.dry:
            print("  $ " + " ".join(shlex.quote(a) if len(a) < 120 else "'<js…>'" for a in full))
            return {"ok": True, "missing": [], "box": None, "dpr": 1} if want_json else ""
        p = subprocess.run(full, capture_output=True, text=True, timeout=120)
        if p.returncode != 0:
            raise RuntimeError(f"{' '.join(full[:3])}… a échoué : {(p.stderr or p.stdout).strip()[:400]}")
        if not want_json:
            return p.stdout
        return parse_eval(p.stdout)


def parse_eval(out: str):
    """agent-browser --json renvoie {"data": {"result": …}} ; on accepte aussi une sortie brute."""
    out = out.strip()
    try:
        obj = json.loads(out)
    except json.JSONDecodeError:
        raise RuntimeError(f"sortie d'eval illisible : {out[:300]}")
    while isinstance(obj, dict) and "ok" not in obj and ("data" in obj or "result" in obj):
        obj = obj.get("data", obj.get("result"))
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except json.JSONDecodeError:
            pass
    return obj


def merged(defaults: dict, cap: dict) -> dict:
    c = dict(defaults)
    c.update(cap)
    c["style"] = {**defaults.get("style", {}), **cap.get("style", {})}
    return c


def capture_one(run: Runner, c: dict, base_dir: Path, keep_open: bool) -> list[str]:
    errors = []
    glob = []
    if c.get("session"):
        glob += ["--session", c["session"]]
    if c.get("state"):
        glob += ["--state", str((base_dir / c["state"]).resolve())]
    if c.get("color_scheme"):
        glob += ["--color-scheme", c["color_scheme"]]

    vp = c.get("viewport", [1280, 800, 2])
    w, h = vp[0], vp[1]
    scale = vp[2] if len(vp) > 2 else 1
    # Ouvrir la page AVANT de régler la fenêtre : sur une session neuve, régler l'échelle retina
    # sans page ouverte produit des captures en mosaïque (constaté avec agent-browser 0.43).
    run(["open", c["url"]], glob)
    run(["set", "viewport", str(w), str(h), str(scale)], glob)

    wait = c.get("wait") or {"load": "load"}
    if "selector" in wait:
        run(["wait", wait["selector"]], glob)
    elif "text" in wait:
        run(["wait", "--text", wait["text"]], glob)
    elif "load" in wait:
        run(["wait", "--load", wait["load"]], glob)
    if wait.get("ms"):
        run(["wait", str(wait["ms"])], glob)

    for step in c.get("steps", []):
        run([str(s) for s in step], glob)

    crop = c.get("crop", True)
    spec = {"items": c.get("annotations", []), "style": c.get("style", {}), "crop": bool(crop)}
    if isinstance(crop, str):
        spec["crop_to"] = crop               # recadrer sur ce conteneur (élargi aux annotations)
    res = run(["eval", build_eval(spec)], glob, want_json=True) or {}
    if not isinstance(res, dict):
        return [f"résultat d'eval inattendu : {res!r}"[:200]]
    if res.get("missing"):
        errors.append("sélecteur(s) introuvable(s) : " + ", ".join(res["missing"]))

    out = (base_dir / c["output"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    if crop and res.get("box"):
        run(["screenshot", "#__doc_crop__", str(out)], glob)      # Chrome capture la zone, à la bonne échelle
    else:
        run(["screenshot", str(out)] + (["--full"] if c.get("full") else []), glob)
    if not keep_open:
        run(["eval", build_eval({"clear": True})], glob, want_json=True)
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recette")
    ap.add_argument("--only", action="append", help="ne faire que cette capture (répétable)")
    ap.add_argument("--dry-run", action="store_true", help="afficher les commandes sans les lancer")
    ap.add_argument("--agent-browser", default="agent-browser", help="commande agent-browser (défaut : agent-browser)")
    ap.add_argument("--keep-open", action="store_true", help="laisser les annotations dans la page (mise au point)")
    a = ap.parse_args(argv)

    path = Path(a.recette)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"recette illisible : {e}", file=sys.stderr)
        return 2
    defaults = doc.get("defaults", {})
    caps = doc.get("captures", [doc] if "url" in doc else [])
    if a.only:
        caps = [c for c in caps if c.get("name") in a.only]
    if not caps:
        print("aucune capture à faire", file=sys.stderr)
        return 2

    run = Runner(a.agent_browser, a.dry_run)
    failed = 0
    for cap in caps:
        c = merged(defaults, cap)
        name = c.get("name") or c.get("output")
        missing_keys = [k for k in ("url", "output") if not c.get(k)]
        if missing_keys:
            print(f"✗ {name} : champ(s) manquant(s) {missing_keys}")
            failed += 1
            continue
        print(f"→ {name}")
        try:
            errs = capture_one(run, c, path.parent, a.keep_open)
        except (RuntimeError, subprocess.TimeoutExpired, KeyError, ValueError) as e:
            errs = [str(e)]
        if errs:
            failed += 1
            for e in errs:
                print(f"✗ {name} : {e}")
        elif not a.dry_run:
            print(f"✓ {name} → {c['output']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
