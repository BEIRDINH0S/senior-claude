"""Tests du script check_docs.py.  Lancer : python3 -m unittest discover tests"""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "ops-doc" / "scripts"))
import check_docs  # noqa: E402

EXEMPLE = ROOT / "skills" / "ops-doc" / "references" / "exemple-rdv"
FIXTURE = ROOT / "tests" / "fixture-repo"
TODAY = "2026-11-23"


def run(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = check_docs.main([*args, "--json", "--today", TODAY])
    return code, json.loads(buf.getvalue())


def codes(result, level=None):
    return [(f["code"], f["message"]) for f in result["findings"]
            if level is None or f["level"] == level]


class ExempleDeReference(unittest.TestCase):
    def test_exemple_conforme(self):
        code, res = run(str(EXEMPLE), "--docs", str(EXEMPLE), "--manifests", str(EXEMPLE / "adr"))
        self.assertEqual(code, 0, codes(res))
        self.assertEqual(codes(res, "AVERTISSEMENT"), [])

    def test_modeles_conformes_structurellement(self):
        tpl = ROOT / "skills" / "ops-doc" / "assets" / "templates"
        code, res = run(str(tpl), "--docs", str(tpl), "--manifests", str(tpl / "adr"))
        erreurs = [c for c, _ in codes(res, "ERREUR")]
        self.assertNotIn("STRUCT-FICHIER", erreurs)
        self.assertNotIn("SECTION", erreurs)
        self.assertNotIn("LIEN-CASSE", erreurs)


class FixtureAvecErreurs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.res = run(str(FIXTURE))
        cls.found = codes(cls.res)

    def has(self, code, fragment):
        self.assertTrue(any(c == code and fragment in m for c, m in self.found),
                        f"{code} / {fragment} attendu dans {self.found}")

    def test_code_retour(self):
        self.assertEqual(self.code, 1)

    def test_secret_dans_url(self):
        self.has("SECRET", "URL")

    def test_pas_de_faux_positif_secret(self):
        secrets = [m for c, m in self.found if c == "SECRET"]
        self.assertEqual(len(secrets), 1, secrets)

    def test_lien_casse_et_wikilink(self):
        self.has("LIEN-CASSE", "wiki/ancien.md")
        self.has("WIKILINK", "")

    def test_alertes(self):
        self.has("ALERTE-SANS-URL", "RdvHighErrorRate")
        self.has("ALERTE-SANS-RUNBOOK", "RdvSlowRequests")
        self.has("RUNBOOK-EXTERNE", "KubePodCrashLooping")
        self.has("RUNBOOK-ORPHELIN", "PVCFillingUp")

    def test_record_rule_ignoree(self):
        self.assertFalse(any("job:http_errors" in m for _, m in self.found))

    def test_config(self):
        self.has("CONFIG-VAR", "STRIPE_KEY")
        self.has("CONFIG-VAR", "FEATURE_FLAGS")
        self.has("CONFIG-SECRET", "rdv-stripe")
        self.assertFalse(any("DATABASE_URL" in m or "rdv-tls" in m for _, m in self.found))

    def test_date_perimee(self):
        self.has("DATE-PERIMEE", "2025-01-10")


if __name__ == "__main__":
    unittest.main()
