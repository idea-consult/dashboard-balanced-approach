import unittest

from ui.formatting import format_euro, format_integer, format_number, format_percent


class TestFormatting(unittest.TestCase):
    def test_format_integer(self):
        self.assertEqual(format_integer(1_000_000), "1.000.000")

    def test_format_number_positive(self):
        self.assertEqual(format_number(1_000_000), "1.000.000,00")

    def test_format_number_negative(self):
        self.assertEqual(format_number(-1234.5), "-1.234,50")

    def test_format_euro(self):
        self.assertEqual(format_euro(2500), "€ 2.500,00")

    def test_format_percent(self):
        self.assertEqual(format_percent(12.5, decimals=1), "12,5 %")


if __name__ == "__main__":
    unittest.main()
