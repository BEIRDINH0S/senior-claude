"""Tests du hook agent_commit_gate.py sur de vrais repos git temporaires."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "hooks" / "agent_commit_gate.py"
EXEMPLE = ROOT / "skills" / "ops-doc" / "references" / "exemple-rdv"


def sh(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def hook(repo, command):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(repo)})
    r = subprocess.run([sys.executable, str(GATE)], input=payload, capture_output=True, text=True)
    return r.returncode, r.stderr


def mark(repo, stage, verdict=True):
    rep = repo / ".." / f"rapport-{stage}.md"
    rep.write_text("Verdict : OK\n" if verdict else "rien\n")
    r = subprocess.run([sys.executable, str(GATE), "mark", stage, "--repo", str(repo), "--report", str(rep)],
                       capture_output=True, text=True)
    return r.returncode, r.stderr


class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.remote = self.tmp / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.remote)], check=True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        sh(self.repo, "init", "-q", "-b", "main")
        sh(self.repo, "config", "user.email", "t@example.org")
        sh(self.repo, "config", "user.name", "test")
        sh(self.repo, "config", "commit.gpgsign", "false")
        shutil.copytree(EXEMPLE, self.repo / "docs")
        (self.repo / "app.py").write_text("print(1)\n")
        sh(self.repo, "add", "-A")
        sh(self.repo, "commit", "-q", "-m", "init")
        sh(self.repo, "remote", "add", "origin", str(self.remote))
        sh(self.repo, "push", "-q", "-u", "origin", "main")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def touch_manifest(self, content="replicas: 2\n"):
        (self.repo / "deploy.yaml").write_text(content)
        sh(self.repo, "add", "deploy.yaml")

    # -- commandes ignorées

    def test_commande_quelconque(self):
        self.touch_manifest()
        self.assertEqual(hook(self.repo, "git status")[0], 0)
        self.assertEqual(hook(self.repo, "echo 'git commit'")[0], 0)

    def test_repo_sans_standard(self):
        shutil.rmtree(self.repo / "docs" / "runbooks")
        self.touch_manifest()
        self.assertEqual(hook(self.repo, "git commit -m x")[0], 0)

    def test_changement_hors_exploitation(self):
        (self.repo / "app.py").write_text("print(2)\n")
        sh(self.repo, "add", "app.py")
        self.assertEqual(hook(self.repo, "git commit -m x")[0], 0)

    # -- commit

    def test_commit_bloque_puis_passe_apres_mark(self):
        self.touch_manifest()
        code, err = hook(self.repo, "git commit -m x")
        self.assertEqual(code, 2)
        self.assertIn("ops-doc-check", err)
        self.assertIn("deploy.yaml", err)
        self.assertEqual(mark(self.repo, "commit")[0], 0)
        self.assertEqual(hook(self.repo, "git commit -m x")[0], 0)

    def test_modif_apres_mark_invalide(self):
        self.touch_manifest()
        mark(self.repo, "commit")
        (self.repo / "deploy.yaml").write_text("replicas: 3\n")   # non indexé : couvert (commit -a)
        self.assertEqual(hook(self.repo, "git commit -am x")[0], 2)

    def test_mark_exige_un_verdict(self):
        self.touch_manifest()
        self.assertEqual(mark(self.repo, "commit", verdict=False)[0], 2)

    def test_doc_non_conforme_bloque_meme_apres_mark(self):
        self.touch_manifest()
        (self.repo / "docs" / "config.md").unlink()
        sh(self.repo, "add", "-A")
        code, err = hook(self.repo, "git commit -m x")
        self.assertEqual(code, 2)
        self.assertIn("pas conforme", err)
        self.assertEqual(mark(self.repo, "commit")[0], 2)

    def test_cd_et_git_C(self):
        self.touch_manifest()
        other = self.tmp
        payload = json.dumps({"tool_name": "Bash", "cwd": str(other),
                              "tool_input": {"command": f"cd {self.repo} && git commit -m x"}})
        r = subprocess.run([sys.executable, str(GATE)], input=payload, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        payload = json.dumps({"tool_name": "Bash", "cwd": str(other),
                              "tool_input": {"command": f"git -C {self.repo} commit -m x"}})
        r = subprocess.run([sys.executable, str(GATE)], input=payload, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    # -- push

    def test_push_demande_la_review(self):
        self.touch_manifest()
        mark(self.repo, "commit")
        sh(self.repo, "commit", "-q", "-m", "manifest")
        code, err = hook(self.repo, "git push")
        self.assertEqual(code, 2)
        self.assertIn("ops-doc-review", err)
        self.assertEqual(mark(self.repo, "push")[0], 0)
        self.assertEqual(hook(self.repo, "git push")[0], 0)

    def test_push_sans_changement_exploitation(self):
        (self.repo / "app.py").write_text("print(3)\n")
        sh(self.repo, "commit", "-qam", "code")
        self.assertEqual(hook(self.repo, "git push")[0], 0)

    def test_nouveau_commit_apres_review_invalide_le_push(self):
        self.touch_manifest()
        sh(self.repo, "commit", "-q", "-m", "a")
        mark(self.repo, "push")
        self.touch_manifest("replicas: 4\n")
        sh(self.repo, "commit", "-q", "-m", "b")
        self.assertEqual(hook(self.repo, "git push")[0], 2)

    def test_commit_et_push_enchaines(self):
        self.touch_manifest()
        code, err = hook(self.repo, "git commit -m x && git push")
        self.assertEqual(code, 2)
        self.assertIn("commit", err)


if __name__ == "__main__":
    unittest.main()
