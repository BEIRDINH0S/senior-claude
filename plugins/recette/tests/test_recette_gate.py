"""Tests du hook recette_gate.py sur de vrais repos git temporaires."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parent.parent / "hooks" / "recette_gate.py"


def sh(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


def hook(repo, command, cwd=None):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd or repo)})
    r = subprocess.run([sys.executable, str(GATE)], input=payload, capture_output=True, text=True)
    return r.returncode, r.stderr


class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "app"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "recette").mkdir()
        sh(self.repo, "init", "-q", "-b", "main")
        sh(self.repo, "config", "user.email", "t@example.org"); sh(self.repo, "config", "user.name", "t")
        sh(self.repo, "config", "commit.gpgsign", "false")
        (self.repo / "src" / "rdv.ts").write_text("export const a = 1;\n")
        (self.repo / "recette" / "a-tester.md").write_text("# À tester\n")
        sh(self.repo, "add", "-A"); sh(self.repo, "commit", "-qm", "init")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def change(self, rel, content="x\n"):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        sh(self.repo, "add", rel)

    def test_code_sans_rien_bloque(self):
        self.change("src/rdv.ts", "export const a = 2;\n")
        code, err = hook(self.repo, "git commit -m 'feat: annulation'")
        self.assertEqual(code, 2)
        self.assertIn("src/rdv.ts", err)
        self.assertIn("a-tester.md", err)

    def test_a_tester_modifie_passe(self):
        self.change("src/rdv.ts", "export const a = 2;\n")
        self.change("recette/a-tester.md", "# À tester\n| 2026-11-24 | Annulation | !1 | EX-003 | SMS | haut | |\n")
        self.assertEqual(hook(self.repo, "git commit -m 'feat: annulation'")[0], 0)

    def test_cas_modifie_passe(self):
        self.change("src/rdv.ts", "export const a = 3;\n")
        self.change("recette/cas/CT-009-x.md", "---\nid: CT-009\n---\n")
        self.assertEqual(hook(self.repo, "git commit -m x")[0], 0)

    def test_trailer_sans_impact(self):
        self.change("src/rdv.ts", "export const a = 4;\n")
        cmd = "git commit -m 'refactor: extraction' -m 'Recette: sans impact (refactoring sans changement de comportement)'"
        self.assertEqual(hook(self.repo, cmd)[0], 0)

    def test_hors_code_ignore(self):
        for rel in ("docs/guide.md", "README.md", "src/rdv.test.ts", "tests/test_api.py", "package-lock.json", ".gitlab-ci.yml"):
            self.change(rel)
        self.assertEqual(hook(self.repo, "git commit -m docs")[0], 0)

    def test_repo_sans_recette_inactif(self):
        shutil.rmtree(self.repo / "recette")
        self.change("src/rdv.ts", "export const a = 5;\n")
        self.assertEqual(hook(self.repo, "git commit -m x")[0], 0)

    def test_commit_a_couvert(self):
        (self.repo / "src" / "rdv.ts").write_text("export const a = 6;\n")   # non indexé, commit -a
        self.assertEqual(hook(self.repo, "git commit -am x")[0], 2)

    def test_config_code(self):
        (self.repo / "recette" / ".recette.json").write_text(json.dumps({"code": ["src/*"]}))
        sh(self.repo, "add", "-A"); sh(self.repo, "commit", "-qm", "cfg")
        self.change("scripts/outil.sh")
        self.assertEqual(hook(self.repo, "git commit -m x")[0], 0)
        self.change("src/rdv.ts", "export const a = 7;\n")
        self.assertEqual(hook(self.repo, "git commit -m x")[0], 2)

    def test_autres_commandes_et_cd(self):
        self.change("src/rdv.ts", "export const a = 8;\n")
        self.assertEqual(hook(self.repo, "git status")[0], 0)
        self.assertEqual(hook(self.repo, f"cd {self.repo} && git commit -m x", cwd=self.tmp)[0], 2)


if __name__ == "__main__":
    unittest.main()
