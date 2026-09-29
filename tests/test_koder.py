import unittest
from datetime import date

from avfallsanteckning.koder import Koder, gallande, normalisera
from tools.avfallskoder import tolka

UTDRAG = """
Bilaga 3

Avfallstyper

01 Avfall från prospektering, ovan- och underjordsbrytning
samt fysikalisk och kemisk behandling av mineral

01 01 Avfall från mineralbrytning:

01 01 01 Avfall från brytning av metallhaltiga material.

13 Oljeavfall och avfall från flytande bränslen (utom ätliga
oljor och oljor i kapitel 05, 12 och 19)

13 02 Motorolje-, transmissionsolje- och smörjoljeavfall:

13 02 05* Mineralbaserade icke-klorerade motor-,
transmissions- och smörjoljor.

/Upphör att gälla U:2026-12-09/
13 02 08* Andra motor-, transmissions- och smörjoljor.

/Träder i kraft I:2026-12-09/
13 02 08* Andra motor-, transmissions- och smörjoljor än de
som anges i 13 02 09.

13 02 09* Ny kod i kommande lydelse.

13 03 Avfall av isoler- och värmeöverföringsoljor:

13 03 10* Andra isoler- och värmeöverföringsoljor.

20 Kommunalt avfall (hushållsavfall och liknande handels-,
industri- och institutionsavfall) även separat insamlade
fraktioner

20 03 Annat kommunalt avfall än det som anges i 20 01 och
20 02:

20 03 99 Annat kommunalt avfall än det som anges i 20 03 01-
20 03 07. Förordning (2026:1433).

Bilaga 4
"""


class TolkaTest(unittest.TestCase):
    def test_utdrag(self):
        koder = tolka(UTDRAG)
        self.assertEqual(
            [k["kod"] for k in koder],
            ["01 01 01", "13 02 05*", "13 02 08*", "13 02 08*", "13 02 09*", "13 03 10*", "20 03 99"],
        )
        olja = koder[1]
        self.assertTrue(olja["farligt"])
        self.assertEqual(olja["beskrivning"], "Mineralbaserade icke-klorerade motor-, transmissions- och smörjoljor")
        self.assertEqual(olja["kapitel"], "13")
        self.assertEqual(olja["underkapitelnamn"], "Motorolje-, transmissionsolje- och smörjoljeavfall")
        self.assertEqual(koder[6]["beskrivning"], "Annat kommunalt avfall än det som anges i 20 03 01-20 03 07")
        self.assertEqual(koder[6]["kapitel"], "20")
        self.assertFalse(koder[0]["farligt"])

    def test_lydelser(self):
        koder = tolka(UTDRAG)
        self.assertEqual([k["fran"] for k in koder], [None, None, None, "2026-12-09", "2026-12-09", None, None])
        self.assertEqual([k["till"] for k in koder], [None, None, "2026-12-09", None, None, None, None])
        fore = [k["kod"] for k in gallande(koder, date(2026, 12, 8))]
        efter = [k["kod"] for k in gallande(koder, date(2026, 12, 9))]
        self.assertEqual(fore, ["01 01 01", "13 02 05*", "13 02 08*", "13 03 10*", "20 03 99"])
        self.assertEqual(efter, ["01 01 01", "13 02 05*", "13 02 08*", "13 02 09*", "13 03 10*", "20 03 99"])
        self.assertEqual(gallande(koder, date(2026, 12, 9))[2]["beskrivning"][-8:], "13 02 09")


class KoderTest(unittest.TestCase):
    def test_normalisera(self):
        self.assertEqual(normalisera("130208*"), "13 02 08*")
        self.assertEqual(normalisera(" 13 02 08 "), "13 02 08")
        self.assertIsNone(normalisera("13 02"))

    def test_lista(self):
        koder = Koder.load(date(2026, 9, 29))
        self.assertGreater(len(koder.lista), 800)
        self.assertEqual(len({k["kod"] for k in koder.lista}), len(koder.lista))
        olja = koder.get("13 02 08*")
        self.assertTrue(olja["farligt"])
        self.assertEqual(koder.get("20 03 01")["farligt"], False)
        self.assertIsNone(koder.get("99 99 99"))
        self.assertIsNotNone(koder.get("10 09 03"))
        self.assertEqual({k["kapitel"] for k in koder.lista}, {f"{n:02d}" for n in range(1, 21)})
        # 19 02 13* tillkommer i lydelsen från 2026-12-09
        self.assertIsNone(koder.get("19 02 13*"))
        senare = Koder.load(date(2026, 12, 9))
        self.assertIsNotNone(senare.get("19 02 13*"))
        self.assertIsNotNone(senare.get("10 09 03"))
        self.assertEqual(len({k["kod"] for k in senare.lista}), len(senare.lista))
