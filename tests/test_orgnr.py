import unittest

from avfallsanteckning.orgnr import formatera, giltigt


class OrgnrTest(unittest.TestCase):
    def test_kontrollsiffra(self):
        for text in ("202100-5489", "2021005489", "556000-0001", "16556000-0001", "202100 5489"):
            self.assertTrue(giltigt(text), text)
        for text in ("202100-5488", "556000-0000", "55600-0001", "", "abc", "5560000001x1"):
            self.assertFalse(giltigt(text), text)

    def test_formatering(self):
        self.assertEqual(formatera("2021005489"), "202100-5489")
        self.assertEqual(formatera("16556000-0001"), "556000-0001")
        self.assertEqual(formatera(" 556000-0001 "), "556000-0001")
        self.assertEqual(formatera("kort"), "kort")


if __name__ == "__main__":
    unittest.main()
