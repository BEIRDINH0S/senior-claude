"""Tests de check_recette.py : on part de l'exemple conforme et on y introduit une erreur à la fois."""
import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "recette" / "scripts"))
import check_recette  # noqa: E402

EXEMPLE = ROOT / "skills" / "recette" / "assets" / "exemple-rdv"
CAMP = "campagnes/2026-11-24-v1.4.0"


def run(path, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = check_recette.main([str(path), "--json", "--today", "2026-11-26", *args])
    return code, json.loads(buf.getvalue())


def codes(res, level=None):
    return [f["code"] for f in res["findings"] if level is None or f["level"] == level]


class Exemple(unittest.TestCase):
    def test_conforme_et_go_avec_reserves(self):
        code, res = run(EXEMPLE)
        self.assertEqual(code, 0, res["findings"])
        self.assertEqual(codes(res, "ERREUR") + codes(res, "AVERTISSEMENT"), [])
        self.assertEqual(res["decision"], "GO AVEC RÉSERVES")

    def test_modeles_lisibles(self):
        tpl = ROOT / "skills" / "recette" / "assets" / "templates"
        code, res = run(tpl)
        # les modèles sont volontairement vides : pas de plantage, et la structure est reconnue
        self.assertNotIn("STRUCT", codes(res))
        self.assertNotIn("STRAT-SECTION", codes(res))


class Mutations(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp()) / "recette"
        shutil.copytree(EXEMPLE, self.d)
        (self.d / CAMP / "pv.md").unlink()

    def tearDown(self):
        shutil.rmtree(self.d.parent)

    def edit(self, rel, old, new, count=1):
        p = self.d / rel
        s = p.read_text()
        self.assertIn(old, s, f"motif absent de {rel}")
        p.write_text(s.replace(old, new, count))

    def test_resultat_vague(self):
        self.edit("cas/CT-001-connexion-valide.md",
                  "| L'agenda du jour s'affiche, titre « Agenda du jour », avec l'adresse du compte en haut à droite |",
                  "| Ça fonctionne |")
        self.assertIn("CAS-ATTENDU-VAGUE", codes(run(self.d)[1]))

    def test_resultat_vide(self):
        self.edit("cas/CT-006-export-csv.md", "| Un fichier `agenda-2026-11-24.csv` est téléchargé |", "|  |")
        code, res = run(self.d)
        self.assertEqual(code, 1)
        self.assertIn("CAS-ATTENDU-VIDE", codes(res))

    def test_exigence_non_couverte(self):
        self.edit("exigences.md", "| EX-005 |", "| EX-006 | Nouvelle exigence | haute | US-40 |\n| EX-005 |")
        self.assertIn("EXIGENCE-NON-COUVERTE", codes(run(self.d)[1]))

    def test_exigence_inconnue(self):
        self.edit("cas/CT-005-rappel-veille.md", "exigences: EX-004", "exigences: EX-004, EX-099")
        self.assertIn("CAS-EXIGENCE-INCONNUE", codes(run(self.d)[1]))

    def test_section_manquante(self):
        self.edit("cas/CT-003-creer-rendez-vous.md", "## Préconditions", "## Contexte")
        self.assertIn("CAS-SECTION", codes(run(self.d)[1]))
        self.edit("strategie.md", "## Hors périmètre", "## Exclusions")
        self.assertIn("STRAT-SECTION", codes(run(self.d)[1]))

    def test_ko_sans_anomalie_et_preuve(self):
        self.edit(f"{CAMP}/campagne.md", "| CT-004 | KO | Camille R. | 2026-11-24 | AN-001 |", "| CT-004 | KO | Camille R. | 2026-11-24 |  |")
        self.edit(f"{CAMP}/campagne.md", "preuves/CT-001-connexion.png", "preuves/absente.png")
        c = codes(run(self.d)[1])
        self.assertIn("CAMP-KO-SANS-ANOMALIE", c)
        self.assertIn("CAMP-PREUVE-INTROUVABLE", c)

    def test_preuve_manquante_et_anomalie_inconnue(self):
        self.edit(f"{CAMP}/campagne.md", "| [journal SMS](preuves/CT-005-rappels.txt) |", "|  |")
        self.edit(f"{CAMP}/campagne.md", "| AN-002 |", "| AN-777 |")
        c = codes(run(self.d)[1])
        self.assertIn("CAMP-PREUVE-MANQUANTE", c)
        self.assertIn("CAMP-ANOMALIE-INCONNUE", c)

    def test_statuts_invalides(self):
        self.edit("anomalies.md", "| majeure | CT-004 |", "| critique | CT-004 |")
        self.edit(f"{CAMP}/campagne.md", "| CT-005 | OK |", "| CT-005 | passé |")
        c = codes(run(self.d)[1])
        self.assertIn("ANO-SEVERITE", c)
        self.assertIn("CAMP-STATUT", c)

    def test_bloquante_ouverte_no_go(self):
        self.edit("anomalies.md", "| bloquante | CT-002 | fermée |", "| bloquante | CT-002 | corrigée |")
        res = run(self.d)[1]
        self.assertEqual(res["decision"], "NO-GO")

    def test_trop_de_majeures_no_go(self):
        self.edit("anomalies.md", "| mineure | CT-003 |", "| majeure | CT-003 |")
        self.assertEqual(run(self.d)[1]["decision"], "NO-GO")

    def test_haute_non_executee_no_go(self):
        self.edit(f"{CAMP}/campagne.md", "| CT-005 | OK |", "| CT-005 | OK |")   # inchangé
        self.edit(f"{CAMP}/campagne.md", "| CT-001 | OK | Camille R. | 2026-11-24 | | [capture](preuves/CT-001-connexion.png) |",
                  "| CT-001 | non exécuté | | | | |")
        res = run(self.d)[1]
        self.assertEqual(res["decision"], "NO-GO")
        self.assertFalse(next(c for c in res["criteres"] if "priorité haute" in c["critere"])["respecte"])

    def test_tout_ferme_go(self):
        p = self.d / "anomalies.md"
        p.write_text(re.sub(r"\| (en correction|ouverte) \|", "| fermée |", p.read_text()))
        self.assertEqual(run(self.d)[1]["decision"], "GO")

    def test_echeance_manquante(self):
        self.edit("anomalies.md", "| 2026-12-18 |", "|  |")
        self.assertIn("ANO-SANS-ECHEANCE", codes(run(self.d)[1]))

    def test_pv_sans_reserve_incoherent(self):
        run(self.d, "--campagne", "2026-11-24-v1.4.0", "--pv")
        self.edit(f"{CAMP}/pv.md", "- [ ] GO sans réserve", "- [x] GO sans réserve")
        self.assertIn("PV-INCOHERENT", codes(run(self.d)[1]))

    def test_pv_existant_non_ecrase(self):
        run(self.d, "--campagne", "2026-11-24-v1.4.0", "--pv")
        self.edit(f"{CAMP}/pv.md", "| Métier (MOA) | | | | |", "| Métier (MOA) | Mme Dupuis | Responsable | 2026-11-26 | signé |")
        code, res = run(self.d, "--campagne", "2026-11-24-v1.4.0", "--pv")
        self.assertTrue(res["pv"].endswith("pv.proposition.md"))
        self.assertIn("Mme Dupuis", (self.d / CAMP / "pv.md").read_text())


if __name__ == "__main__":
    unittest.main()
