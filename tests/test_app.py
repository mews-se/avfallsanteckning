import io
import json
import tempfile
import unittest
from pathlib import Path

from avfallsanteckning import create_app

KONFIG = """
[verksamhet]
namn = "Testbolaget AB"
orgnr = "556000-0000"
adress = "Testvägen 1"
postnummer = "117 55"
ort = "Stockholm"
kommun = "Stockholm"
cfar = "12345678"
kontakt = "miljo@testbolaget.se"

[favoriter]
koder = ["13 02 08*", "16 01 07*"]

[[arbetsstallen]]
namn = "Verkstaden"
adress = "Testvägen 1, 117 55 Stockholm"
kommun = "Stockholm"
cfar = "12345678"

[[arbetsstallen]]
namn = "Depån"
adress = "Depåvägen 2, 131 54 Nacka"
kommun = "Nacka"
cfar = ""
"""

PRODUCENT = {
    "avfallskod": "13 02 08*",
    "vikt_kg": "120,5",
    "vikt_uppskattad": "1",
    "transportdatum": "2026-10-01",
    "transportsatt": "Vägtransport",
    "arbetsstalle": "0",
    "fran_adress": "Testvägen 1, 117 55 Stockholm",
    "fran_kommun": "Stockholm",
    "transportor_namn": "Transport AB",
    "transportor_orgnr": "556111-1111",
    "mottagare_namn": "Mottagning AB",
    "mottagare_orgnr": "556222-2222",
    "till_adress": "Deponivägen 9, 136 50 Jordbro",
    "till_kommun": "Haninge",
    "referens": "Order 4711",
    "av": "Anna",
}

TRANSPORTOR = {
    "avfallskod": "15 02 02*",
    "vikt_kg": "40",
    "transportdatum": "2026-10-02",
    "transportsatt": "Vägtransport",
    "lamnare_namn": "",
    "fran_adress": "E4 norrgående vid Hallunda",
    "fran_koordinat": "59.2432, 17.8266",
    "fran_kommun": "Botkyrka",
    "klassgrund": ["spill", "osakert"],
    "mottagare_namn": "Mottagning AB",
    "mottagare_orgnr": "556222-2222",
    "till_adress": "Deponivägen 9, 136 50 Jordbro",
    "fordon": "ABC 123",
    "forare": "Bo",
}


class AppCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        katalog = Path(self.tmp.name)
        (katalog / "config.toml").write_text(KONFIG, encoding="utf-8")
        app = create_app(config_path=katalog / "config.toml", data_dir=katalog / "data")
        app.config["TESTING"] = True
        self.klient = app.test_client()

    def skapa(self, roll, data):
        svar = self.klient.post(f"/ny/{roll}", data=data)
        self.assertEqual(svar.status_code, 302, svar.data.decode())
        return int(svar.headers["Location"].rstrip("/").split("/")[-1])


class FormularTest(AppCase):
    def test_startsida(self):
        svar = self.klient.get("/")
        self.assertEqual(svar.status_code, 200)
        self.assertIn("Inga anteckningar", svar.data.decode())

    def test_producent_skapas_och_visas(self):
        aid = self.skapa("producent", PRODUCENT)
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("2026-0001", text)
        self.assertIn("13 02 08*", text)
        self.assertIn("120,5 kg", text)
        self.assertIn("uppskattad", text)
        self.assertIn("Rapportera senast <b>mån 5 okt 2026</b>", text)
        self.assertIn("CFAR 12345678", text)
        self.assertIn("Stockholm (0180)", text)
        self.assertIn("Haninge (0136)", text)
        lista = self.klient.get("/").data.decode()
        self.assertIn("Mottagning AB", lista)

    def test_validering(self):
        svar = self.klient.post("/ny/producent", data={**PRODUCENT, "avfallskod": "99 99 99", "vikt_kg": "0"})
        text = svar.data.decode()
        self.assertEqual(svar.status_code, 200)
        self.assertIn("Välj en avfallskod", text)
        self.assertIn("Ange vikt", text)

    def test_kommun(self):
        svar = self.klient.post("/ny/producent", data={**PRODUCENT, "till_kommun": "Atlantis"})
        self.assertIn("Okänd kommun: Atlantis", svar.data.decode())
        annan = {**PRODUCENT, "arbetsstalle": "", "fran_kommun": "", "till_kommun": "haninge kommun"}
        aid = self.skapa("producent", annan)
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertNotIn("Stockholm (0180)", text)
        self.assertIn("Haninge (0136)", text)
        svar = self.klient.post("/ny/transportor", data={**TRANSPORTOR, "fran_kommun": ""})
        self.assertIn("Ange kommunen", svar.data.decode())
        csv = self.klient.get("/export.csv?ar=2026").data.decode("utf-8-sig")
        self.assertIn(";0136;", csv)
        self.assertIn(";Haninge;", csv)

    def test_transportor_kraver_grund(self):
        svar = self.klient.post("/ny/transportor", data={**TRANSPORTOR, "klassgrund": []})
        self.assertIn("minst en grund", svar.data.decode())
        aid = self.skapa("transportor", TRANSPORTOR)
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("Okänd", text)
        self.assertIn("Testbolaget AB", text)
        self.assertIn("Osäker bedömning", text)

    def test_icke_farligt_har_ingen_frist(self):
        aid = self.skapa("producent", {**PRODUCENT, "avfallskod": "20 03 01"})
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("rapporteras inte", text)

    def test_kopiera_behaller_transporten_men_inte_avfallet(self):
        aid = self.skapa("producent", PRODUCENT)
        text = self.klient.get(f"/ny/producent?kopiera={aid}").data.decode()
        self.assertIn("Order 4711", text)
        self.assertIn("Ingen kod vald", text)


class ArbetsstalleTest(AppCase):
    def test_arbetsstallet_ger_adress_kommun_och_cfar(self):
        text = self.klient.get("/ny/producent").data.decode()
        self.assertIn('<option value="0" selected>Verkstaden, Testvägen 1, 117 55 Stockholm (CFAR 12345678)', text)
        self.assertIn('<option value="1">Depån, Depåvägen 2, 131 54 Nacka</option>', text)
        depan = {**PRODUCENT, "arbetsstalle": "1", "fran_adress": "ignoreras", "fran_kommun": "Atlantis"}
        aid = self.skapa("producent", depan)
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("Depåvägen 2, 131 54 Nacka", text)
        self.assertIn("Nacka (0182)", text)
        self.assertNotIn("CFAR", text)
        self.assertNotIn("ignoreras", text)
        self.assertIn('<option value="1" selected>', self.klient.get(f"/anteckning/{aid}/redigera").data.decode())
        self.skapa("producent", PRODUCENT)
        csv = self.klient.get("/export.csv?ar=2026").data.decode("utf-8-sig")
        self.assertIn("fran_cfar", csv.splitlines()[0])
        self.assertIn(";12345678;", csv)
        self.assertTrue(self.klient.get(f"/anteckning/{aid}/anteckning.pdf").data.startswith(b"%PDF"))

    def test_annan_plats_skrivs_in(self):
        svar = self.klient.post("/ny/producent", data={**PRODUCENT, "arbetsstalle": "", "fran_adress": ""})
        self.assertIn("Ange var avfallet producerats", svar.data.decode())
        data = {**PRODUCENT, "arbetsstalle": "", "fran_adress": "Tillfällig plats 3", "fran_kommun": "Solna"}
        aid = self.skapa("producent", data)
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("Tillfällig plats 3", text)
        self.assertIn("Solna (0184)", text)
        self.assertNotIn("CFAR", text)
        text = self.klient.get(f"/anteckning/{aid}/redigera").data.decode()
        self.assertIn('<option value="">annan plats, skriv in nedan</option>', text)

    def test_utan_lista_anvands_verksamheten(self):
        katalog = Path(self.tmp.name)
        (katalog / "ensam.toml").write_text(KONFIG.split("[[arbetsstallen]]")[0], encoding="utf-8")
        app = create_app(config_path=katalog / "ensam.toml", data_dir=katalog / "ensam")
        text = app.test_client().get("/ny/producent").data.decode()
        self.assertIn('<option value="0" selected>Testbolaget AB, Testvägen 1, 117 55 Stockholm (CFAR 12345678)', text)
        self.assertNotIn('<option value="1"', text)

    def test_gammal_databas_far_kolumnen(self):
        from avfallsanteckning import db

        vag = Path(self.tmp.name) / "gammal.db"
        conn = db.anslut(vag)
        conn.executescript(db.SCHEMA.replace("    fran_cfar TEXT NOT NULL DEFAULT '',\n", ""))
        self.assertNotIn("fran_cfar", [r[1] for r in conn.execute("PRAGMA table_info(anteckning)")])
        conn.close()
        db.init(vag)
        conn = db.anslut(vag)
        self.assertIn("fran_cfar", [r[1] for r in conn.execute("PRAGMA table_info(anteckning)")])
        conn.close()


class StatusTest(AppCase):
    def test_rapportering_och_aterta(self):
        aid = self.skapa("producent", PRODUCENT)
        data = {"handling": "rapporterad", "nv_kvittens": "NV-123", "av": "Anna"}
        self.klient.post(f"/anteckning/{aid}/status", data=data)
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("NV-123", text)
        self.assertIn("Rapporterad", text)
        self.klient.post(f"/anteckning/{aid}/status", data={"handling": "aterta"})
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("Markera som rapporterad", text)

    def test_makulering_kraver_skal_och_laser(self):
        aid = self.skapa("producent", PRODUCENT)
        self.klient.post(f"/anteckning/{aid}/status", data={"handling": "makulera", "skal": ""})
        self.assertIn("Markera som rapporterad", self.klient.get(f"/anteckning/{aid}").data.decode())
        self.klient.post(f"/anteckning/{aid}/status", data={"handling": "makulera", "skal": "dubbelregistrering"})
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("Makulerad", text)
        self.assertIn("dubbelregistrering", text)
        svar = self.klient.get(f"/anteckning/{aid}/redigera")
        self.assertEqual(svar.status_code, 302)

    def test_rattning_efter_rapportering_loggas(self):
        aid = self.skapa("producent", PRODUCENT)
        self.klient.post(f"/anteckning/{aid}/status", data={"handling": "rapporterad"})
        self.klient.post(f"/anteckning/{aid}/redigera", data={**PRODUCENT, "vikt_kg": "130"})
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("130 kg", text)
        self.assertIn("rättad", text)

    def test_forfallna(self):
        aid = self.skapa("producent", {**PRODUCENT, "transportdatum": "2026-01-07"})
        svar = json.loads(self.klient.get("/api/forfallna").data)
        self.assertEqual(svar["att_rapportera"], 1)
        self.assertEqual(svar["forfallna"][0]["senast"], "2026-01-09")
        self.klient.post(f"/anteckning/{aid}/status", data={"handling": "rapporterad"})
        self.assertEqual(json.loads(self.klient.get("/api/forfallna").data)["forfallna"], [])


class DokumentTest(AppCase):
    def test_pdf_och_export(self):
        aid = self.skapa("producent", PRODUCENT)
        urler = (
            f"/anteckning/{aid}/anteckning.pdf",
            f"/anteckning/{aid}/transportdokument.pdf",
            "/transportdokument.pdf",
        )
        for url in urler:
            svar = self.klient.get(url)
            self.assertEqual(svar.status_code, 200, url)
            self.assertTrue(svar.data.startswith(b"%PDF"), url)
        tid = self.skapa("transportor", TRANSPORTOR)
        self.assertTrue(self.klient.get(f"/anteckning/{tid}/anteckning.pdf").data.startswith(b"%PDF"))
        csv = self.klient.get("/export.csv?ar=2026").data.decode("utf-8-sig")
        self.assertIn("2026-0001;antecknad", csv)
        self.assertIn("15 02 02*", csv)

    def test_bilaga(self):
        aid = self.skapa("producent", PRODUCENT)
        data = {"filer": (io.BytesIO(b"%PDF-1.4 test"), "transportdokument åäö.pdf"), "av": "Anna"}
        self.klient.post(f"/anteckning/{aid}/bilaga", data=data, content_type="multipart/form-data")
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("transportdokument åäö.pdf", text)
        bid = int(text.split("/bilaga/")[1].split('"')[0])
        self.assertEqual(self.klient.get(f"/bilaga/{bid}").data, b"%PDF-1.4 test")
        data = {"filer": (io.BytesIO(b"x"), "fel.exe")}
        svar = self.klient.post(
            f"/anteckning/{aid}/bilaga", data=data, content_type="multipart/form-data", follow_redirects=True
        )
        self.assertIn("filtypen stöds inte", svar.data.decode())


class ParterTest(AppCase):
    def test_part_fylls_i_anteckningen(self):
        part = {
            "namn": "Ragnvald AB",
            "orgnr": "556333-3333",
            "adress": "Skrotgatan 1",
            "kommun": "Göteborg",
            "roll": "mottagare",
            "aktiv": "1",
        }
        self.klient.post("/parter", data=part)
        text = self.klient.get("/parter").data.decode()
        self.assertIn("Ragnvald AB", text)
        self.assertIn('value="Göteborg"', text)
        pid = text.split('name="id" value="')[1].split('"')[0]
        data = {**PRODUCENT, "mottagare_id": pid, "mottagare_namn": "", "till_adress": "", "till_kommun": ""}
        aid = self.skapa("producent", data)
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("Ragnvald AB", text)
        self.assertIn("Skrotgatan 1", text)
        self.assertIn("Göteborg (1480)", text)

    def test_healthz(self):
        self.assertEqual(json.loads(self.klient.get("/healthz").data)["ok"], True)
