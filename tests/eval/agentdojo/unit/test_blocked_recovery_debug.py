import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "experiments" / "agentdojo" / "scripts" / "18_debug_blocked_recovery.py"
spec = importlib.util.spec_from_file_location("debug_blocked_recovery_required_name", SCRIPT)
assert spec and spec.loader
debugger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(debugger)


def test_debugger_case_selector_supports_wildcard():
    assert debugger.matches_any([("banking", "user_task_2", "*")], "banking", "user_task_2", "injection_task_0")
