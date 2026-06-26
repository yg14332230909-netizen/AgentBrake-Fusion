from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from prototype.mock_agent_app import MockAgentApp, load_cases  # noqa: E402
from prototype.mock_business_tools import MockBusinessTools  # noqa: E402
from prototype.supervisor_plugin import MonitoringPlugin  # noqa: E402


DEFAULT_CASES = PACKAGE_ROOT / "cases" / "adversarial_cases.jsonl"
DEFAULT_POLICY = PACKAGE_ROOT / "policies" / "supervisor_policy.json"
DEFAULT_RUNTIME = PACKAGE_ROOT / "runtime"


def run_all(*, runtime: Path = DEFAULT_RUNTIME, cases_path: Path = DEFAULT_CASES, policy_path: Path = DEFAULT_POLICY, include_benign: bool = True, clean: bool = True) -> dict:
    if clean and runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir(parents=True, exist_ok=True)
    supervisor = MonitoringPlugin(policy_path, runtime)
    tools = MockBusinessTools(runtime)
    app = MockAgentApp(supervisor, tools)
    results = []
    for case in load_cases(cases_path):
        if not include_benign and case["id"].startswith("BENIGN"):
            continue
        results.append(app.run_case(case))
    totals = {"allow": 0, "ask": 0, "block": 0}
    for result in results:
        for key, value in result["counts"].items():
            totals[key] += value
    summary = {
        "results": results,
        "totals": totals,
        "audit_log": str(runtime / "audit_log.jsonl"),
        "alerts": str(runtime / "alerts.jsonl"),
        "dashboard_command": f"python {PACKAGE_ROOT / 'prototype' / 'realtime_dashboard.py'} --runtime {runtime} --port 8899",
    }
    (runtime / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay all local LLM-agent attack cases.")
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--attacks-only", action="store_true")
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()
    summary = run_all(
        runtime=args.runtime,
        cases_path=args.cases,
        policy_path=args.policy,
        include_benign=not args.attacks_only,
        clean=not args.no_clean,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
