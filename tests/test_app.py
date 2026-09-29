import base64
import io
import json
import re
import tempfile
import unittest
import zlib
from pathlib import Path

from avfallsanteckning import create_app

INSTALLNINGAR = {
    "namn": "Testbolaget AB",
    "orgnr": "556000-0001",
    "adress": "Testvägen 1",
    "postnummer": "117 55",
    "ort": "Stockholm",
    "cfar": "12345678",
    "kontakt": "miljo@testbolaget.se",
    "koder": "13 02 08*, 16 01 07*",
    "aktiv": "1",
    "blankett_beskrivning": "Avfall som hittats vid vägen",
    "blankett_producent": "Okänd, avfallet är upphittat",
    "bedomningsgrunder": "Spill av olja eller kemikalier\nOsäker bedömning, hanteras som farligt",
    "stalle_namn": ["Verkstaden", "Depån"],
    "stalle_adress": ["Testvägen 1, 117 55 Stockholm", "Depåvägen 2, 131 54 Nacka"],
    "stalle_kommun": ["Stockholm", "Nacka"],
    "stalle_cfar": ["12345678", ""],
}

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
    "transportor_orgnr": "556111-1112",
    "mottagare_namn": "Mottagning AB",
    "mottagare_orgnr": "556222-2223",
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
    "klassgrund": ["Spill av olja eller kemikalier", "Osäker bedömning, hanteras som farligt"],
    "mottagare_namn": "Mottagning AB",
    "mottagare_orgnr": "556222-2223",
    "till_adress": "Deponivägen 9, 136 50 Jordbro",
    "fordon": "ABC 123",
    "forare": "Bo",
}


def pdf_text(data):
    # reportlab skriver sidorna som ascii85 + flate
    delar = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        del_ = m.group(1).strip()
        if del_.endswith(b"~>"):
            del_ = base64.a85decode(del_[:-2])
        try:
            del_ = zlib.decompress(del_)
        except zlib.error:
            pass
        delar.append(del_)
    return b"".join(delar)


class AppCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        app = create_app(data_dir=Path(self.tmp.name) / "data")
        app.config["TESTING"] = True
        self.klient = app.test_client()
        self.installningar(INSTALLNINGAR)

    def installningar(self, data):
        svar = self.klient.post("/installningar", data=data)
        self.assertEqual(svar.status_code, 302, svar.data.decode())

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

    def test_orgnr_kontrolleras(self):
        svar = self.klient.post("/ny/producent", data={**PRODUCENT, "transportor_orgnr": "556111-1111"})
        self.assertIn("Ogiltigt org.nr: 556111-1111", svar.data.decode())
        aid = self.skapa("producent", {**PRODUCENT, "transportor_orgnr": "5561111112", "mottagare_orgnr": ""})
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("556111-1112", text)
        svar = self.klient.post("/ny/transportor", data={**TRANSPORTOR, "lamnare_orgnr": "202100-5488"})
        self.assertIn("Ogiltigt org.nr: 202100-5488", svar.data.decode())

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
        self.installningar({k: v for k, v in INSTALLNINGAR.items() if not k.startswith("stalle_")})
        text = self.klient.get("/ny/producent").data.decode()
        self.assertIn('<option value="0" selected>Testbolaget AB, Testvägen 1, 117 55 Stockholm (CFAR 12345678)', text)
        self.assertNotIn('<option value="1"', text)
        aid = self.skapa("producent", PRODUCENT)
        self.assertIn("Stockholm (0180)", self.klient.get(f"/anteckning/{aid}").data.decode())
        self.installningar({**INSTALLNINGAR, "ort": "Skogås", "stalle_namn": []})
        aid = self.skapa("producent", PRODUCENT)
        text = self.klient.get(f"/anteckning/{aid}").data.decode()
        self.assertIn("Skogås", text)
        self.assertNotIn("(0", text.split("Var avfallet producerats")[1].split("</tr>")[0])

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
        with self.klient.get(f"/bilaga/{bid}") as svar:
            self.assertEqual(svar.data, b"%PDF-1.4 test")
        data = {"filer": (io.BytesIO(b"x"), "fel.exe")}
        svar = self.klient.post(
            f"/anteckning/{aid}/bilaga", data=data, content_type="multipart/form-data", follow_redirects=True
        )
        self.assertIn("filtypen stöds inte", svar.data.decode())


class TransportorTest(AppCase):
    def test_rollen_kan_stangas_av(self):
        text = self.klient.get("/").data.decode()
        self.assertIn("Ny: transportör", text)
        self.assertIn("Blankett", text)
        self.installningar({k: v for k, v in INSTALLNINGAR.items() if k != "aktiv"})
        text = self.klient.get("/").data.decode()
        self.assertNotIn("Ny: transportör", text)
        self.assertNotIn("Blankett", text)
        self.assertNotIn('name="roll"', text)
        self.assertEqual(self.klient.get("/ny/transportor").status_code, 404)
        self.assertEqual(self.klient.get("/transportdokument.pdf").status_code, 404)
        self.assertEqual(self.klient.get("/ny/producent").status_code, 200)

    def test_grunder_och_blankett_fran_installningarna(self):
        text = self.klient.get("/ny/transportor").data.decode()
        self.assertIn('value="Spill av olja eller kemikalier"', text)
        pdf = pdf_text(self.klient.get("/transportdokument.pdf").data)
        self.assertIn(b"upphittat", pdf)
        self.assertIn(b"hittats vid v", pdf)
        self.assertIn(b"Spill av olja", pdf)
        self.assertEqual(pdf.count(b"Namnf"), 1)
        enkel = {k: v for k, v in INSTALLNINGAR.items() if not k.startswith(("blankett_", "bedomningsgrunder"))}
        self.installningar(enkel)
        self.assertNotIn("Grund för bedömningen", self.klient.get("/ny/transportor").data.decode())
        svar = self.klient.post("/ny/transportor", data={**TRANSPORTOR, "klassgrund": []})
        self.assertEqual(svar.status_code, 302, svar.data.decode())
        pdf = pdf_text(self.klient.get("/transportdokument.pdf").data)
        self.assertNotIn(b"upphittat", pdf)
        self.assertNotIn(b"Kryssa", pdf)
        self.assertEqual(pdf.count(b"Namnf"), 2)


class InstallningarTest(AppCase):
    def test_forsta_start(self):
        app = create_app(data_dir=Path(self.tmp.name) / "ny")
        text = app.test_client().get("/").data.decode()
        self.assertIn("Verksamhetens uppgifter saknas", text)
        self.assertEqual(app.test_client().get("/installningar").status_code, 200)
        self.assertNotIn("Verksamhetens uppgifter saknas", self.klient.get("/").data.decode())

    def test_sparas_och_visas(self):
        text = self.klient.get("/installningar").data.decode()
        self.assertIn('value="Testbolaget AB"', text)
        self.assertIn('value="13 02 08*, 16 01 07*"', text)
        self.assertIn('value="Depåvägen 2, 131 54 Nacka"', text)
        self.assertIn("Spill av olja eller kemikalier\nOsäker bedömning", text)
        self.assertIn('name="aktiv" value="1" checked', text)
        self.assertIn('href="https://cfarnrsok.scb.se/"', text)
        self.assertIn("Testbolaget AB</span>", self.klient.get("/").data.decode())
        pdf = pdf_text(self.klient.get("/transportdokument.pdf").data)
        self.assertIn(b"Org.nr 556000-0001", pdf)
        self.assertIn(b"miljo@testbolaget.se", pdf)

    def test_validering(self):
        data = {**INSTALLNINGAR, "namn": "", "koder": "13 02 08*, 99 99 99"}
        data["stalle_namn"] = ["", "Depån"]
        data["stalle_kommun"] = ["Atlantis", "Nacka"]
        svar = self.klient.post("/installningar", data=data)
        text = svar.data.decode()
        self.assertEqual(svar.status_code, 200)
        self.assertIn("Ange verksamhetens namn", text)
        self.assertIn("Okänd kommun: Atlantis", text)
        self.assertIn("Okänd avfallskod: 99 99 99", text)
        self.assertIn("Ange namn på arbetsstället", text)
        svar = self.klient.post("/installningar", data={**INSTALLNINGAR, "orgnr": "556000-0000"})
        self.assertIn("Ogiltigt org.nr: 556000-0000", svar.data.decode())
        self.installningar({**INSTALLNINGAR, "orgnr": "5560000001"})
        self.assertIn('value="556000-0001"', self.klient.get("/installningar").data.decode())
        self.assertIn('value="Testbolaget AB"', self.klient.get("/installningar").data.decode())

    def test_logotyp(self):
        self.assertEqual(self.klient.get("/logotyp").status_code, 404)
        text = self.klient.get("/").data.decode()
        self.assertNotIn("/logotyp", text)
        self.assertIn("<small>Testbolaget AB</small>", text)
        self.installningar({**INSTALLNINGAR, "logotyp": (io.BytesIO(b"\x89PNG\r\n\x1a\n"), "firma.png")})
        with self.klient.get("/logotyp") as svar:
            self.assertEqual(svar.status_code, 200)
            self.assertEqual(svar.mimetype, "image/png")
        text = self.klient.get("/").data.decode()
        self.assertIn('src="/logotyp"', text)
        self.assertNotIn("<small>Testbolaget AB</small>", text)
        svar = self.klient.post("/installningar", data={**INSTALLNINGAR, "logotyp": (io.BytesIO(b"x"), "fel.exe")})
        self.assertIn("png, svg, jpg eller webp", svar.data.decode())
        with self.klient.get("/logotyp") as svar:
            self.assertEqual(svar.status_code, 200)
        self.installningar({**INSTALLNINGAR, "ta_bort_logotyp": "1"})
        self.assertEqual(self.klient.get("/logotyp").status_code, 404)


class ParterTest(AppCase):
    def test_part_fylls_i_anteckningen(self):
        part = {
            "namn": "Ragnvald AB",
            "orgnr": "556333-3334",
            "adress": "Skrotgatan 1",
            "kommun": "Göteborg",
            "roll": "mottagare",
            "aktiv": "1",
        }
        svar = self.klient.post("/parter", data={**part, "orgnr": "556333-3333"}, follow_redirects=True)
        self.assertIn("Ogiltigt org.nr: 556333-3333", svar.data.decode())
        self.klient.post("/parter", data={**part, "orgnr": "5563333334"})
        text = self.klient.get("/parter").data.decode()
        self.assertIn("Ragnvald AB", text)
        self.assertIn('value="556333-3334"', text)
        self.assertIn("foretagsinfo.bolagsverket.se", text)
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
