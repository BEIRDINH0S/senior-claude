"""Tests de validate_logs.py : fichiers, CRI, stdin, faux serveur Loki, config."""
import contextlib
import http.server
import io
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "kube-logs" / "scripts" / "validate_logs.py"
sys.path.insert(0, str(SCRIPT.parent))
import validate_logs  # noqa: E402

LOGS = Path(__file__).resolve().parent / "logs"


def run(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = validate_logs.main([*args, "--json"])
    return code, json.loads(buf.getvalue())


class LogsALAncienne(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.r = run(str(LOGS / "mauvais.log"))
        cls.rules = cls.r["regles"]

    def test_non_conforme(self):
        self.assertEqual(self.code, 1)
        self.assertFalse(self.r["conforme"])

    def test_lignes_hors_logger(self):
        self.assertEqual(self.rules["PAS-JSON"]["count"], 2)          # lignes de npm start
        self.assertEqual(self.rules["STACK-ECLATEE"]["count"], 2)     # stack en texte

    def test_format(self):
        for code in ("NIVEAU-NUMERIQUE", "NIVEAU-INCONNU", "CHAMP-MANQUANT", "TIME-NON-ISO", "ERR-NON-SERIALISEE"):
            self.assertIn(code, self.rules)

    def test_secrets_et_pii(self):
        self.assertEqual(self.rules["SECRET-CLE"]["count"], 2)
        self.assertIn("SECRET-VALEUR", self.rules)
        self.assertIn("PII-EMAIL", self.rules)

    def test_message_variable(self):
        self.assertIn("commande <n> créée pour client <n>", self.rules["MSG-VARIABLE"]["examples"][0])


class LogsConformes(unittest.TestCase):
    def test_cri_et_ligne_partielle(self):
        code, r = run(str(LOGS / "bon-cri.log"))
        self.assertEqual(code, 0, r["regles"])
        self.assertEqual(r["total"], 4)      # les morceaux P+F recollés en une ligne
        self.assertEqual(r["regles"], {})

    def test_stdin(self):
        p = subprocess.run([sys.executable, str(SCRIPT)], input=(LOGS / "bon-cri.log").read_text(),
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_valeur_masquee_acceptee(self):
        line = '{"level":"info","time":"2026-11-23T14:02:11Z","msg":"x","password":"[masqué]"}\n'
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
            f.write(line)
        self.assertEqual(run(f.name)[0], 0)


class Options(unittest.TestCase):
    def test_tolerance(self):
        code, r = run(str(LOGS / "mauvais.log"), "--tolerance", "0.9")
        self.assertEqual(code, 0)

    def test_config_personnalisee(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d, "cfg.json")
            cfg.write_text(json.dumps({"required": ["time", "level", "msg", "service"]}))
            code, r = run(str(LOGS / "bon-cri.log"), "--config", str(cfg))
            self.assertEqual(code, 0)          # service présent partout
            code, r = run(str(LOGS / "mauvais.log"), "--config", str(cfg))
            self.assertIn("service", " ".join(r["regles"]["CHAMP-MANQUANT"]["examples"]))

    def test_aucune_ligne(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
            pass
        code, r = run(f.name)
        self.assertEqual(code, 1)
        self.assertEqual(r["total"], 0)


class FauxLoki(unittest.TestCase):
    """Valide ce qui est réellement arrivé dans Loki, via l'API query_range."""

    @classmethod
    def setUpClass(cls):
        lines = (LOGS / "mauvais.log").read_text().splitlines()

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                cls.path = self.path
                cls.org = self.headers.get("X-Scope-OrgID")
                body = {"status": "success", "data": {"resultType": "streams", "result": [
                    {"stream": {"app": "rdv-api"},
                     "values": [[str(1763906531482000000 + i), l] for i, l in enumerate(lines)]}]}}
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_loki(self):
        code, r = run("--loki", self.url, "--query", '{app="rdv-api"}', "--since", "1h",
                      "--header", "X-Scope-OrgID: prod")
        self.assertEqual(code, 1)
        self.assertIn("SECRET-CLE", r["regles"])
        self.assertIn("/loki/api/v1/query_range", self.path)
        self.assertIn("query=%7Bapp%3D%22rdv-api%22%7D", self.path)
        self.assertEqual(self.org, "prod")


if __name__ == "__main__":
    unittest.main()
