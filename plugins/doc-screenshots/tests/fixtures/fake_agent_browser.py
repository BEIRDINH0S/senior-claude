#!/usr/bin/env python3
"""Faux agent-browser pour les tests : journalise les appels, simule eval et screenshot."""
import json, os, shutil, sys
from pathlib import Path
args = sys.argv[1:]
log = os.environ["FAKE_AB_LOG"]
with open(log, "a") as f:
    f.write(json.dumps(args) + "\n")
cmd = [a for a in args if not a.startswith("--")]
glob_vals = {"--session", "--state", "--color-scheme"}
clean, skip = [], False
for a in args:
    if skip: skip = False; continue
    if a in glob_vals: skip = True; continue
    if a == "--json": continue
    clean.append(a)
if clean[0] == "eval":
    if '"clear":true' in clean[1] or '"clear": true' in clean[1]:
        print(json.dumps({"success": True, "data": {"result": {"ok": True, "cleared": True}}}))
    elif os.environ.get("FAKE_AB_MISSING"):
        print(json.dumps({"success": True, "data": {"result": {"ok": False, "missing": ["#absent"], "box": None, "dpr": 2}}}))
    else:
        print(json.dumps({"success": True, "data": {"result": {"ok": True, "missing": [],
              "box": {"x": 100, "y": 150, "w": 300, "h": 120, "scrollX": 0, "scrollY": 50}, "dpr": 2}}}))
elif clean[0] == "screenshot":
    target = clean[2] if len(clean) > 2 and clean[1].startswith("#") else clean[1]
    shutil.copy(os.environ["FAKE_AB_PNG"], target)
