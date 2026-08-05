"""Unit tests for PDF report help parsing and measure grouping."""

from __future__ import annotations

import unittest

from reports.context import (
    _group_applied_measures,
    _parse_measure_help,
    _title_case_type,
)


class TestParseMeasureHelp(unittest.TestCase):
    def test_extracts_uitleg_effect_and_type(self) -> None:
        help_text = """# Verkavelingsverbod

#### Uitleg
Verbod op opsplitsen.

#### Beoogd effect
Minder woningen.

#### Type maatregel
bijkomende gehinderde personen vermijden

---

#### Instrument en kosten
- **Instrument:** test
"""
        short, measure_type = _parse_measure_help(help_text)
        self.assertIn("Verbod op opsplitsen", short)
        self.assertIn("Minder woningen", short)
        self.assertNotIn("Instrument", short)
        self.assertNotIn("bijkomende gehinderde", short)
        self.assertEqual(measure_type, "bijkomende gehinderde personen vermijden")

    def test_title_case_type(self) -> None:
        self.assertEqual(
            _title_case_type("bijkomende gehinderde personen vermijden"),
            "Bijkomende gehinderde personen vermijden",
        )
        self.assertEqual(_title_case_type(""), "Overige maatregelen")

    def test_group_preserves_type_order(self) -> None:
        rows = [
            {
                "naam": "A",
                "measure_type": "bijkomende gehinderde personen vermijden",
                "measure_type_title": "Bijkomende gehinderde personen vermijden",
            },
            {
                "naam": "B",
                "measure_type": "akoestisch binnencomfort verbeteren",
                "measure_type_title": "Akoestisch binnencomfort verbeteren",
            },
            {
                "naam": "C",
                "measure_type": "bijkomende gehinderde personen vermijden",
                "measure_type_title": "Bijkomende gehinderde personen vermijden",
            },
        ]
        groups = _group_applied_measures(rows)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["title"], "Bijkomende gehinderde personen vermijden")
        self.assertEqual([m["naam"] for m in groups[0]["measures"]], ["A", "C"])
        self.assertEqual(groups[1]["title"], "Akoestisch binnencomfort verbeteren")


if __name__ == "__main__":
    unittest.main()
