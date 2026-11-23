"""Tests de doc-screenshots : recadrage PNG, construction du JS, orchestration agent-browser."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "doc-screenshots" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import capture  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"
REAL = FIX / "capture-reelle.png"
FAKE = FIX / "fake_agent_browser.py"


class ExpressionJS(unittest.TestCase):
    def test_syntaxe_valide(self):
        if not shutil.which("node"):
            self.skipTest("node absent")
        js = capture.build_eval({"items": [{"selector": "#a", "label": 1, "note": "l'étape \"1\""}], "style": {}})
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(js)
        p = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_return_sans_saut_de_ligne(self):
        js = capture.build_eval({"clear": True})
        self.assertIn(";return (function (spec)", js)


class Orchestration(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.log = self.d / "log.jsonl"
        self.recipe = self.d / "captures.json"
        self.recipe.write_text(json.dumps({
            "defaults": {"viewport": [1280, 800, 2], "session": "doc", "state": "auth.json"},
            "captures": [{"name": "connexion", "url": "http://localhost:3000/login",
                          "wait": {"selector": "form"}, "steps": [["fill", "#email", "demo@example.org"]],
                          "annotations": [{"selector": "#email", "label": 1}], "output": "img/connexion.png"}]}))
        self.env = {**os.environ, "FAKE_AB_LOG": str(self.log), "FAKE_AB_PNG": str(REAL)}

    def tearDown(self):
        shutil.rmtree(self.d)

    def run_capture(self, *extra, env=None):
        return subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), str(self.recipe),
                               "--agent-browser", f"{sys.executable} {FAKE}", *extra],
                              capture_output=True, text=True, env=env or self.env)

    def calls(self):
        return [json.loads(l) for l in self.log.read_text().splitlines()]

    def test_sequence_et_recadrage(self):
        p = self.run_capture()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        flat = [" ".join(c) for c in self.calls()]
        self.assertTrue(any("set viewport 1280 800 2" in c for c in flat))
        self.assertTrue(any("open http://localhost:3000/login" in c for c in flat))
        self.assertTrue(any("wait form" in c for c in flat))
        self.assertTrue(any("fill #email demo@example.org" in c for c in flat))
        self.assertTrue(all("--session doc" in c for c in flat))
        self.assertTrue(all(str((self.d / "auth.json").resolve()) in c for c in flat))
        # recadrage délégué à Chrome : capture de l'élément #__doc_crop__ posé par le calque
        shot = [c for c in flat if " screenshot " in f" {c} "][0]
        self.assertIn("screenshot #__doc_crop__ " + str((self.d / "img" / "connexion.png").resolve()), shot)
        self.assertTrue((self.d / "img" / "connexion.png").exists())
        self.assertIn('"clear": true', flat[-1])

    def test_sans_recadrage(self):
        r = json.loads(self.recipe.read_text()); r["captures"][0]["crop"] = False
        self.recipe.write_text(json.dumps(r))
        self.assertEqual(self.run_capture().returncode, 0)
        shot = [" ".join(c) for c in self.calls() if "screenshot" in c][0]
        self.assertNotIn("#__doc_crop__", shot)

    def test_ouvre_avant_le_viewport(self):
        # régler l'échelle retina avant d'ouvrir une page produit des captures en mosaïque
        self.run_capture()
        flat = [" ".join(c) for c in self.calls()]
        i_open = next(i for i, c in enumerate(flat) if " open " in f" {c} ")
        i_vp = next(i for i, c in enumerate(flat) if "set viewport" in c)
        self.assertLess(i_open, i_vp)

    def test_selecteur_introuvable(self):
        p = self.run_capture(env={**self.env, "FAKE_AB_MISSING": "1"})
        self.assertEqual(p.returncode, 1)
        self.assertIn("#absent", p.stdout)

    def test_dry_run(self):
        p = self.run_capture("--dry-run")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("set viewport", p.stdout)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
