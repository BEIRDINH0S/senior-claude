"""Tests du linter de dashboards.  Lancer : python3 -m unittest discover -s tests"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "grafana-dashboards" / "scripts"))
import lint_dashboard  # noqa: E402

T = Path(__file__).resolve().parent
EXEMPLE = ROOT / "skills" / "grafana-dashboards" / "assets" / "exemple-rdv-overview.json"


def run(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = lint_dashboard.main([*map(str, args), "--json"])
    return code, json.loads(buf.getvalue())["findings"]


def codes(findings, level=None):
    return [f["code"] for f in findings if level is None or f["level"] == level]


class ExempleDeReference(unittest.TestCase):
    def test_exemple_v2_sans_constat(self):
        code, f = run(EXEMPLE)
        self.assertEqual(code, 0)
        self.assertEqual([(x["code"], x["panel"], x["message"]) for x in f], [])

    def test_exemple_cite_les_runbooks(self):
        code, f = run(EXEMPLE, "--runbooks", T / "runbooks")
        self.assertEqual(codes(f), ["RUNBOOK-NON-REFERENCE"])      # seul RdvSlowRequests n'a pas de panneau
        self.assertIn("RdvSlowRequests", f[0]["message"])

    def test_v1_correct(self):
        code, f = run(T / "dashboards" / "v1-correct.json")
        self.assertEqual(code, 0, f)
        self.assertEqual(codes(f, "AVERTISSEMENT"), [])


class DashboardGenereParIA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.f = run(T / "dashboards" / "v1-genere-par-ia.json", "--runbooks", T / "runbooks")
        cls.c = set(codes(cls.f))

    def test_erreurs(self):
        self.assertEqual(self.code, 1)
        for c in ("RATE-MANQUANT", "QUANTILE-SANS-LE", "TITRE-MANQUANT", "RUNBOOK-INTROUVABLE"):
            self.assertIn(c, self.c)

    def test_avertissements(self):
        for c in ("UID-MANQUANT", "REFRESH-COURT", "TROP-DE-PANNEAUX", "DS-EN-DUR", "DESCRIPTION-MANQUANTE",
                  "UNITE-MANQUANTE", "NAMESPACE-EN-DUR", "CAMEMBERT", "SERIE-PAR-POD"):
            self.assertIn(c, self.c)

    def test_infos(self):
        for c in ("PAS-DE-VARIABLE", "PAS-DE-LIEN-LOGS", "RATE-INTERVAL"):
            self.assertIn(c, self.c)

    def test_jauge_memoire_sans_rate_acceptee(self):
        # container_memory_working_set_bytes est une jauge : pas de RATE-MANQUANT sur "Memory"
        self.assertFalse(any(x["code"] == "RATE-MANQUANT" and x["panel"] == "Memory" for x in self.f))


class V2(unittest.TestCase):
    def test_bandeau_dans_un_onglet(self):
        code, f = run(T / "dashboards" / "v2-bandeau-cache.json")
        self.assertIn("BANDEAU-CACHE", codes(f))

    def test_v2_sans_enveloppe_kubernetes(self):
        doc = json.loads(EXEMPLE.read_text())
        spec = doc["spec"]; spec["uid"] = "brut"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "brut.json"); p.write_text(json.dumps(spec))
            code, f = run(p)
            self.assertEqual(code, 0, f)


class Regles(unittest.TestCase):
    def one(self, expr, **extra):
        panel = {"id": 1, "type": "timeseries", "title": "t", "description": "d",
                 "targets": [{"refId": "A", "expr": expr}], "fieldConfig": {"defaults": {"unit": "short"}}}
        panel.update(extra)
        dash = {"uid": "x", "title": "x", "templating": {"list": [{"name": "datasource"}]},
                "links": [{"url": "/explore"}], "panels": [panel]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "d.json"); p.write_text(json.dumps(dash))
            return codes(run(p)[1])

    def test_rate_present(self):
        self.assertNotIn("RATE-MANQUANT", self.one("sum(rate(x_total[$__rate_interval]))"))

    def test_increase(self):
        self.assertNotIn("RATE-MANQUANT", self.one("sum(increase(x_total[1h]))"))

    def test_jauge_connue(self):
        self.assertNotIn("RATE-MANQUANT", self.one('sum(cnpg_backends_total{namespace="$namespace"})'))

    def test_jauge_option(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "d.json")
            p.write_text(json.dumps({"uid": "x", "panels": [{"type": "stat", "title": "t", "description": "d",
                "targets": [{"expr": "my_queue_items_total"}], "fieldConfig": {"defaults": {"unit": "short"}}}]}))
            self.assertIn("RATE-MANQUANT", codes(run(p)[1]))
            self.assertNotIn("RATE-MANQUANT", codes(run(p, "--gauge", "my_queue_items_total")[1]))

    def test_quantile_avec_le(self):
        self.assertNotIn("QUANTILE-SANS-LE", self.one("histogram_quantile(0.99, sum by (le, route) (rate(h_bucket[$__rate_interval])))"))

    def test_latence_moyenne_seule(self):
        self.assertIn("LATENCE-MOYENNE", self.one("sum(rate(http_request_duration_seconds_sum[$__rate_interval])) / sum(rate(http_request_duration_seconds_count[$__rate_interval]))"))

    def test_seuil_rouge_sans_runbook(self):
        th = {"defaults": {"unit": "short", "thresholds": {"steps": [{"value": None, "color": "green"}, {"value": 1, "color": "red"}]}}}
        self.assertIn("SEUIL-SANS-RUNBOOK", self.one("up", fieldConfig=th))
        self.assertNotIn("SEUIL-SANS-RUNBOOK", self.one("up", fieldConfig=th, description="Si rouge : runbook RdvApiDown"))

    def test_fichier_json_non_dashboard_ignore(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "package.json").write_text('{"name": "x"}')
            Path(d, "dash.json").write_text(EXEMPLE.read_text())
            code, f = run(d)
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
