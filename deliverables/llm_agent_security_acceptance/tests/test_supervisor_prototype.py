from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_all_attacks import run_all  # noqa: E402
from scripts.run_case import run_case  # noqa: E402


class SupervisorPrototypeTests(unittest.TestCase):
    def test_prompt_injection_blocks_external_secret_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_case("SCN-01", runtime=Path(tmp))
            blocked_tools = [item for item in result["decisions"] if item.get("decision") == "block"]
            self.assertTrue(blocked_tools)

    def test_memory_poisoning_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_case("SCN-05", runtime=Path(tmp))
            self.assertGreaterEqual(result["counts"]["block"], 1)

    def test_all_cases_generate_audit_and_alerts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            summary = run_all(runtime=runtime)
            self.assertTrue(Path(summary["audit_log"]).exists())
            self.assertTrue(Path(summary["alerts"]).exists())
            self.assertGreaterEqual(summary["totals"]["block"], 5)
            self.assertGreaterEqual(summary["totals"]["allow"], 1)


if __name__ == "__main__":
    unittest.main()
