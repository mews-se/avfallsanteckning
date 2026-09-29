import unittest

from avfallsanteckning.kommungranser import Kommungranser, tolka_koordinat


class KoordinatTest(unittest.TestCase):
    def test_tolkning(self):
        self.assertEqual(tolka_koordinat("59.2432, 17.8266"), (59.2432, 17.8266))
        self.assertEqual(tolka_koordinat("59,2432 17,8266"), (59.2432, 17.8266))
        self.assertEqual(tolka_koordinat("N 59.2432 E 17.8266"), (59.2432, 17.8266))
        self.assertEqual(tolka_koordinat("17.8266, 59.2432"), (59.2432, 17.8266))
        for text in ("", "E4 vid Hallunda", "59.2432", "1.0, 2.0", "6567000, 660000"):
            self.assertIsNone(tolka_koordinat(text), text)


class GranserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.granser = Kommungranser.load()

    def test_alla_kommuner(self):
        self.assertEqual(len(self.granser.kommuner), 290)

    def test_kanda_punkter(self):
        for text, kod in (
            ("59.3293, 18.0686", "0180"),
            ("59.2432, 17.8266", "0127"),
            ("57.7089, 11.9746", "1480"),
            ("67.8558, 20.2253", "2584"),
            ("55.6050, 13.0038", "1280"),
        ):
            self.assertEqual(self.granser.kod(text), kod, text)

    def test_utanfor(self):
        self.assertIsNone(self.granser.kod("58.0, 19.5"))
        self.assertIsNone(self.granser.kod("hittepå"))


if __name__ == "__main__":
    unittest.main()
