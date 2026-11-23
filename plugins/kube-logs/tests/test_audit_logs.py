"""Tests du script audit_logs.py.  Lancer : python3 -m unittest discover -s tests"""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "kube-logs" / "scripts"))
import audit_logs  # noqa: E402

TESTS = Path(__file__).resolve().parent


def run(path):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = audit_logs.main([str(path), "--json"])
    return code, json.loads(buf.getvalue())["findings"]


class AppALAncienne(unittest.TestCase):
    """Logs dans des fichiers sur un PVC, console.log, npm start… tout doit sortir."""

    @classmethod
    def setUpClass(cls):
        cls.code, cls.f = run(TESTS / "fixture-mauvais")

    def has(self, code, fragment=""):
        self.assertTrue(any(x["code"] == code and fragment in x["message"] + x["file"] for x in self.f),
                        f"{code} / {fragment} attendu : {[(x['code'], x['message']) for x in self.f]}")

    def test_code_retour(self):
        self.assertEqual(self.code, 1)

    def test_fichiers_et_volume(self):
        self.has("LOG-FICHIER", "pino.destination")
        self.has("LOG-FICHIER", "winston")
        self.has("LOG-VOLUME", "/var/log/app")
        self.has("LOG-SIDECAR-TAIL")

    def test_code(self):
        self.has("LOG-CONSOLE", "2 appel(s)")       # commentaire et fichier de test ignorés
        self.has("LOG-SECRET", "password")
        self.has("LOG-STACK-TEXTE")
        self.has("LOG-NIVEAU-NUMERIQUE")
        self.has("LOG-REDACT")
        self.has("LOG-PRETTY", "package.json")

    def test_dockerfile(self):
        self.has("LOG-NPM-START")

    def test_alloy_et_loki(self):
        self.has("LOKI-LABEL-CARDINALITE", "user_id")
        self.has("LOKI-LABEL-CARDINALITE", "trace_id")
        self.has("LOKI-LABEL-CARDINALITE", "pod")
        self.has("LOKI-RETENTION")

    def test_level_n_est_pas_signale(self):
        self.assertFalse(any("« level »" in x["message"] for x in self.f))

    def test_console_dans_les_tests_ignore(self):
        self.assertFalse(any(x["file"].startswith("test/") for x in self.f))


class AppJsonSurStdout(unittest.TestCase):
    """La pratique cible : aucun constat."""

    def test_aucun_constat(self):
        code, f = run(TESTS / "fixture-bon")
        self.assertEqual(code, 0)
        self.assertEqual([(x["code"], x["file"], x["message"]) for x in f], [])


class Dockerfile(unittest.TestCase):
    def check(self, content):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            Path(d, "Dockerfile").write_text(content)
            return [x["code"] for x in run(d)[1]]

    def test_forme_shell(self):
        self.assertIn("LOG-NPM-START", self.check("FROM node\nCMD node dist/main.js\n"))

    def test_forme_exec(self):
        self.assertEqual(self.check('FROM node\nCMD ["node", "dist/main.js"]\n'), [])

    def test_yarn(self):
        self.assertIn("LOG-NPM-START", self.check('FROM node\nCMD ["yarn", "start"]\n'))


if __name__ == "__main__":
    unittest.main()
