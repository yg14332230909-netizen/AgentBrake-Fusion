import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "experiments" / "agentdojo" / "scripts" / "18_debug_blocked_recovery.py"
spec = importlib.util.spec_from_file_location("debug_blocked_recovery", SCRIPT)
assert spec and spec.loader
debugger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(debugger)


def test_blocked_debugger_classifies_missing_trace(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "summary.json").write_text(
        json.dumps(
            {
                "suite": "banking",
                "defense": "agentdojo_firewall",
                "per_run": [
                    {
                        "suite": "banking",
                        "method": "agentdojo_firewall",
                        "user_task_id": "user_task_2",
                        "injection_task_id": "injection_task_0",
                        "blocked_case": True,
                        "raw_agentdojo_user_task_success": False,
                        "raw_agentdojo_injection_task_success": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rows = debugger.analyze_blocked_cases(reports, selectors=["banking:user_task_2:injection_task_0"])

    assert rows[0]["failure_category"] == "missing_trace"
    assert rows[0]["required_action"].startswith("rerun with --save-full-trace")
