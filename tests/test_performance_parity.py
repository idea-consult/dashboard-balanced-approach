"""Golden fixtures: simulation outputs must stay identical across perf refactors."""

from __future__ import annotations

import os
import unittest

from tests.perf_parity_helpers import (
    FIXTURE_DIR,
    assert_snapshots_equal,
    fixture_paths,
    load_fixture,
    run_scenario,
    write_fixture,
)


def _fixtures_exist(scenario: str) -> bool:
    paths = fixture_paths(scenario)
    return all(path.is_file() for path in paths.values())


class TestPerformanceParity(unittest.TestCase):
    """Compare live pipeline output to frozen fixtures from pre-optimisation code."""

    @classmethod
    def setUpClass(cls) -> None:
        update = os.getenv("UPDATE_PERF_FIXTURES", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        for scenario in ("baseline", "active"):
            if update or not _fixtures_exist(scenario):
                write_fixture(run_scenario(scenario))
        if not FIXTURE_DIR.is_dir():
            raise unittest.SkipTest("perf parity fixture dir missing")

    def test_baseline_matches_fixture(self) -> None:
        actual = run_scenario("baseline")
        expected = load_fixture("baseline")
        assert_snapshots_equal(actual, expected)

    def test_active_matches_fixture(self) -> None:
        actual = run_scenario("active")
        expected = load_fixture("active")
        assert_snapshots_equal(actual, expected)


if __name__ == "__main__":
    unittest.main()
