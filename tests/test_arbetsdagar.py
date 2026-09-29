import unittest
from datetime import date

from avfallsanteckning.arbetsdagar import arbetsdag, helgdagar, paskdagen, rapportera_senast


class PaskTest(unittest.TestCase):
    def test_kanda_paskdagar(self):
        self.assertEqual(paskdagen(2024), date(2024, 3, 31))
        self.assertEqual(paskdagen(2025), date(2025, 4, 20))
        self.assertEqual(paskdagen(2026), date(2026, 4, 5))
        self.assertEqual(paskdagen(2027), date(2027, 3, 28))


class HelgdagTest(unittest.TestCase):
    def test_rorliga_helgdagar_2026(self):
        h = helgdagar(2026)
        self.assertIn(date(2026, 4, 3), h)  # långfredagen
        self.assertIn(date(2026, 4, 6), h)  # annandag påsk
        self.assertIn(date(2026, 5, 14), h)  # kristi himmelsfärdsdag
        self.assertIn(date(2026, 6, 20), h)  # midsommardagen
        self.assertIn(date(2026, 10, 31), h)  # alla helgons dag

    def test_arbetsdag(self):
        self.assertTrue(arbetsdag(date(2026, 9, 29)))
        self.assertFalse(arbetsdag(date(2026, 10, 3)))
        self.assertFalse(arbetsdag(date(2026, 6, 6)))


class FristTest(unittest.TestCase):
    def test_tva_arbetsdagar(self):
        self.assertEqual(rapportera_senast(date(2026, 9, 29)), date(2026, 10, 1))
        self.assertEqual(rapportera_senast(date(2026, 10, 1)), date(2026, 10, 5))
        self.assertEqual(rapportera_senast(date(2026, 10, 3)), date(2026, 10, 6))

    def test_frist_hoppar_over_helg_och_aftnar(self):
        self.assertEqual(rapportera_senast(date(2026, 12, 22)), date(2026, 12, 28))
        self.assertEqual(rapportera_senast(date(2026, 6, 17)), date(2026, 6, 22))
        self.assertEqual(rapportera_senast(date(2026, 4, 1)), date(2026, 4, 7))
