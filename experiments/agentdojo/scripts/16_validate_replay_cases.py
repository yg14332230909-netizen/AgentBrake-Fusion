from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASES = ROOT / "experiments" / "agentdojo" / "replay_cases"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AgentDojo-derived replay case schema")
    parser.add_argument("--cases-dir", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args()
    errors = validate_replay_cases(args.cases_dir)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("replay cases valid")
    return 0


def validate_replay_cases(cases_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest = json.loads((cases_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "agentdojo_replay_cases_v2":
        errors.append("manifest schema_version must be agentdojo_replay_cases_v2")
    if "not a standard AgentDojo end-to-end score" not in str(manifest.get("description", "")):
        errors.append("manifest must declare replay is not a standard AgentDojo end-to-end score")
    cases = []
    for label in ("unsafe", "safe"):
        for path in sorted((cases_dir / label).glob("*.json")):
            case = json.loads(path.read_text(encoding="utf-8"))
            cases.append(case)
            errors.extend(validate_case(case, path))
    if int(manifest.get("total_case_count", -1)) != len(cases):
        errors.append("manifest total_case_count does not match case files")
    counts: dict[tuple[str, str], int] = {}
    for case in cases:
        counts[(str(case.get("suite")), str(case.get("label")))] = counts.get((str(case.get("suite")), str(case.get("label"))), 0) + 1
    for suite in ("banking", "travel", "slack", "workspace"):
        for label in ("unsafe", "safe"):
            if counts.get((suite, label), 0) < 3:
                errors.append(f"{suite} requires at least 3 {label} replay cases")
    return errors


def validate_case(case: dict, path: Path) -> list[str]:
    required = {
        "case_id",
        "suite",
        "label",
        "source_trace",
        "prior",
        "current_tool_call",
        "ground_truth_violation",
        "expected_decision",
        "case_origin",
        "standard_agentdojo_e2e_score",
    }
    missing = sorted(required - set(case))
    errors = [f"{path}: missing {missing}"] if missing else []
    if case.get("standard_agentdojo_e2e_score") is not False:
        errors.append(f"{path}: standard_agentdojo_e2e_score must be false")
    if case.get("expected_decision") not in {"allow", "require_confirmation", "block"}:
        errors.append(f"{path}: invalid expected_decision")
    if case.get("label") not in {"unsafe", "safe", "require_confirmation"}:
        errors.append(f"{path}: invalid label")
    call = case.get("current_tool_call") or {}
    if not isinstance(call, dict) or "tool" not in call or "args" not in call:
        errors.append(f"{path}: current_tool_call requires tool and args")
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
