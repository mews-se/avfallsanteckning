import unittest

from avfallsanteckning.kommuner import Kommuner
from tools.kommuner import tolka

HTML = """<p>01 Stockholms län<br />0114 Upplands Väsby<br />0180 Stockholm<br />
0136 Haninge<br />1480 Göteborg</p><p>25 Norrbottens län<br />2584 Kiruna</p>"""


class TolkaTest(unittest.TestCase):
    def test_html(self):
        kommuner = tolka(HTML)
        self.assertEqual([k["kod"] for k in kommuner], ["0114", "0180", "0136", "1480", "2584"])
        self.assertEqual(kommuner[0]["namn"], "Upplands Väsby")


class KommunerTest(unittest.TestCase):
    def setUp(self):
        self.k = Kommuner.load()

    def test_lista(self):
        self.assertEqual(len(self.k.lista), 290)
        self.assertEqual(self.k.namn("0180"), "Stockholm")
        self.assertEqual(self.k.namn("0136"), "Haninge")
        self.assertEqual(self.k.namn(""), "")
        self.assertEqual(self.k.namn("9999"), "")

    def test_kod_fran_namn(self):
        self.assertEqual(self.k.kod("Stockholm"), "0180")
        self.assertEqual(self.k.kod("stockholms kommun"), "0180")
        self.assertEqual(self.k.kod("Stockholms"), "0180")
        self.assertEqual(self.k.kod("  upplands  väsby "), "0114")
        self.assertEqual(self.k.kod("Göteborg"), "1480")
        self.assertEqual(self.k.kod("0180"), "0180")
        self.assertEqual(self.k.kod(""), "")
        self.assertIsNone(self.k.kod("9999"))
        self.assertIsNone(self.k.kod("Atlantis"))
