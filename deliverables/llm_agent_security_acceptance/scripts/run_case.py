from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from prototype.mock_agent_app import MockAgentApp, load_cases  # noqa: E402
from prototype.mock_business_tools import MockBusinessTools  # noqa: E402
from prototype.supervisor_plugin import MonitoringPlugin  # noqa: E402


DEFAULT_CASES = PACKAGE_ROOT / "cases" / "adversarial_cases.jsonl"
DEFAULT_POLICY = PACKAGE_ROOT / "policies" / "supervisor_policy.json"
DEFAULT_RUNTIME = PACKAGE_ROOT / "runtime"


def run_case(case_id: str, *, runtime: str | Path = DEFAULT_RUNTIME, cases_path: str | Path = DEFAULT_CASES, policy_path: str | Path = DEFAULT_POLICY) -> dict[str, Any]:
    cases = {case["id"]: case for case in load_cases(cases_path)}
    if case_id not in cases:
        raise SystemExit(f"unknown case_id {case_id}; available: {', '.join(sorted(cases))}")
    runtime_path = Path(runtime)
    supervisor = MonitoringPlugin(policy_path, runtime_path)
    tools = MockBusinessTools(runtime_path)
    app = MockAgentApp(supervisor, tools)
    return app.run_case(cases[case_id])


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a single local red-team case.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    args = parser.parse_args()
    result = run_case(args.case_id, runtime=args.runtime, cases_path=args.cases, policy_path=args.policy)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
