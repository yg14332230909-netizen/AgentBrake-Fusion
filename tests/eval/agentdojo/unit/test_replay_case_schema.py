import json
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
CASES = ROOT / "experiments" / "agentdojo" / "replay_cases"


def load_script(name: str):
    path = ROOT / "experiments" / "agentdojo" / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_replay_manifest_declares_not_e2e_score():
    manifest = json.loads((CASES / "manifest.json").read_text(encoding="utf-8"))
    assert "not a standard AgentDojo end-to-end score" in manifest["description"]


def test_replay_case_has_required_fields():
    validator = load_script("16_validate_replay_cases.py")
    errors = validator.validate_replay_cases(CASES)
    assert errors == []


def test_replay_summary_separates_unsafe_and_safe_denominators():
    summarizer = load_script("11_summarize_replay_benchmark.py")
    unsafe = [{"label": "unsafe", "observed_decision": "block"}]
    safe = [{"label": "safe", "observed_decision": "allow"}, {"label": "safe", "observed_decision": "block"}]
    assert summarizer._rate(row["observed_decision"] == "block" for row in unsafe) == 1
    assert summarizer._rate(row["observed_decision"] == "allow" for row in safe) == 0.5
