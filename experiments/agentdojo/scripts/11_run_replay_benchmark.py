from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from reposhield.eval.agentdojo.compat.types import ToolCallContext
from reposhield.eval.agentdojo.gate.tool_firewall import AgentDojoToolFirewall

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASES = ROOT / "experiments" / "agentdojo" / "replay_cases"
DEFAULT_OUT = ROOT / "experiments" / "agentdojo" / "reports" / "replay"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AgentDojo-derived dangerous-action replay benchmark")
    parser.add_argument("--cases-dir", "--manifest", dest="cases_dir", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.cases_dir.name == "manifest.json":
        args.cases_dir = args.cases_dir.parent
    if args.out is not None:
        args.out_dir = args.out.parent
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cases = load_cases(args.cases_dir)
    if args.dry_run:
        print(json.dumps({"case_count": len(cases), "cases_dir": str(args.cases_dir)}, indent=2))
        return 0
    results = [run_case(case) for case in cases]
    report = {
        "benchmark_type": "agentdojo_derived_tool_boundary_replay",
        "standard_agentdojo_e2e_score": False,
        "warning": "This is an AgentDojo-derived tool-boundary replay benchmark, not a standard AgentDojo end-to-end score.",
        "results": results,
    }
    out = args.out or (args.out_dir / "replay_results.json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)
    return 0


def load_cases(cases_dir: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for label in ("unsafe", "safe"):
        for path in sorted((cases_dir / label).glob("*.json")):
            case = json.loads(path.read_text(encoding="utf-8"))
            case.setdefault("label", label)
            case.setdefault("source_raw_file", str(path))
            cases.append(case)
    return cases


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    fw = AgentDojoToolFirewall()
    for prior in iter_prior_tool_events(case):
        if prior.get("role") == "tool":
            ctx = ToolCallContext(
                suite=str(case.get("suite", "workspace")),
                tool_name=str(prior.get("name", "unknown_tool")),
                tool_args={},
                user_task=case_user_task(case),
            )
            fw.observe_after_tool(ctx, prior.get("content", ""))
    call = case.get("current_tool_call") or case["tool_call"]
    ctx = ToolCallContext(
        suite=str(case.get("suite", "workspace")),
        tool_name=str(call.get("tool")),
        tool_args=dict(call.get("args", {}) or {}),
        user_task=case_user_task(case),
    )
    decision = fw.guard_before_tool(ctx)
    observed = "allow" if decision.execute else decision.decision
    return {
        "case_id": case.get("case_id"),
        "suite": case.get("suite"),
        "label": case.get("label"),
        "expected_decision": case.get("expected_decision"),
        "observed_decision": observed,
        "passed": observed == case.get("expected_decision"),
        "reason_codes": decision.reason_codes,
        "ground_truth_violation": case.get("ground_truth_violation", {}),
        "expected_reason_codes": case.get("expected_reason_codes", []),
        "blocked_result": decision.safe_result,
        "audit": fw.audit_events,
    }


def iter_prior_tool_events(case: dict[str, Any]) -> list[dict[str, Any]]:
    if case.get("prior"):
        return list(case.get("prior") or [])
    out = []
    for result in case.get("prior_tool_results") or []:
        if not isinstance(result, dict):
            continue
        out.append(
            {
                "role": "tool",
                "name": result.get("tool", "unknown_tool"),
                "content": result.get("content", ""),
            }
        )
    return out


def case_user_task(case: dict[str, Any]) -> str:
    if case.get("user_task"):
        return str(case["user_task"])
    for message in case.get("prior_messages") or []:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(str(item.get("content") or item.get("text") or ""))
                else:
                    parts.append(str(item))
            return " ".join(part for part in parts if part).strip()
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
