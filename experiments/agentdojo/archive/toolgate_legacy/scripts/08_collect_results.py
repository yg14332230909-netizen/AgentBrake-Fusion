from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
RUNS = REPORTS / "runs"


METHOD_ORDER = [
    ("no_defense_attack", "No Defense"),
    ("tool_filter_attack", "Tool Filter"),
    ("reposhield_gateway_only_attack", "RepoShield Gateway-only Fast"),
    ("reposhield_toolgate_attack", "RepoShield ToolGate"),
    ("reposhield_toolgate_invariants_attack", "RepoShield ToolGate + Invariants"),
    ("full_reposhield_fast_attack", "Full RepoShield Fast"),
]

ABLATION_ORDER = [
    ("reposhield_toolgate_no_taxonomy_attack", "w/o AgentDojo taxonomy"),
    ("reposhield_toolgate_no_state_tracker_attack", "w/o AgentDojo StateTracker"),
    ("reposhield_toolgate_no_invariants_attack", "w/o AgentDojo invariants"),
]


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    runs = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(RUNS.glob("*.json"))]
    by_name = {run.get("run_name"): run for run in runs}
    rows = []
    for key, label in METHOD_ORDER:
        run = by_name.get(key)
        aggregate = None if run is not None else _aggregate_runs([r for r in runs if str(r.get("run_name", "")).endswith("_" + key)], key)
        if aggregate is not None:
            run = aggregate
        if run is None:
            rows.append({"method": label, "status": "Not implemented"})
            continue
        rows.append(
            {
                "method": label,
                "utility_under_attack": run.get("utility_under_attack"),
                "security": run.get("security"),
                "targeted_asr": run.get("targeted_asr"),
                "total_runtime_min": run.get("total_runtime_min"),
                "run_name": run.get("run_name"),
                "attack": run.get("attack"),
                "defense": run.get("defense"),
            }
        )

    ablation_rows = []
    for key, label in ABLATION_ORDER:
        run = by_name.get(key)
        aggregate = None if run is not None else _aggregate_runs([r for r in runs if str(r.get("run_name", "")).endswith("_" + key)], key)
        if aggregate is not None:
            run = aggregate
        if run is None:
            ablation_rows.append({"method": label, "status": "Not implemented"})
            continue
        ablation_rows.append(
            {
                "method": label,
                "utility_under_attack": run.get("utility_under_attack"),
                "security": run.get("security"),
                "targeted_asr": run.get("targeted_asr"),
                "total_runtime_min": run.get("total_runtime_min"),
                "run_name": run.get("run_name"),
            }
        )

    audit_rows = []
    invariants = _collect_invariant_hits()
    for run in runs:
        audit = run.get("reposhield_audit_summary") or {}
        audit_latency = run.get("reposhield_audit_latency") or {}
        audit_rows.append(
            {
                "run_name": run.get("run_name"),
                "suite": run.get("suite"),
                "tool_gate_calls": (audit.get("reposhield_checked_calls") or 0),
                "unknown_tool_rate": audit.get("reposhield_unknown_tool_rate"),
                "registered_tool_rate": audit.get("reposhield_registered_tool_rate"),
                "policy_p95_ms": audit.get("reposhield_p95_policy_latency_ms"),
                "audit_p95_ms": audit.get("reposhield_p95_audit_latency_ms") or audit_latency.get("audit_append_p95_ms"),
                "decision_counts": audit.get("reposhield_policy_decisions", {}),
            }
        )

    summary = {
        "main_results": rows,
        "ablation_results": ablation_rows,
        "audit_rows": audit_rows,
        "invariant_hits": invariants,
        "runs": runs,
    }
    (REPORTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS / "summary.md").write_text(render_summary(rows, ablation_rows, audit_rows, invariants), encoding="utf-8")
    (REPORTS / "reposhield_audit_check.md").write_text(render_audit_check(runs), encoding="utf-8")
    return 0


def _aggregate_runs(runs: list[dict[str, Any]], run_name: str) -> dict[str, Any] | None:
    if not runs:
        return None
    utility_pairs = []
    security_pairs = []
    for run in runs:
        utility_pairs.extend(bool(v) for v in (run.get("utility_results") or {}).values())
        security_pairs.extend(bool(v) for v in (run.get("security_results") or {}).values())
    audit_summaries = [r.get("reposhield_audit_summary") or {} for r in runs]
    decision_counts: Counter[str] = Counter()
    checked_calls = 0
    unknown_tools = 0
    registered_tools = 0
    policy_p95s = []
    audit_p95s = []
    for audit in audit_summaries:
        checked_calls += int(audit.get("reposhield_checked_calls") or 0)
        unknown_tools += int(audit.get("reposhield_unknown_tools") or 0)
        registered_tools += int(audit.get("reposhield_registered_tools") or 0)
        decision_counts.update(audit.get("reposhield_policy_decisions") or {})
        if audit.get("reposhield_p95_policy_latency_ms") is not None:
            policy_p95s.append(float(audit.get("reposhield_p95_policy_latency_ms") or 0))
        if audit.get("reposhield_p95_audit_latency_ms") is not None:
            audit_p95s.append(float(audit.get("reposhield_p95_audit_latency_ms") or 0))
    targeted_asr = _avg_bool(security_pairs) if security_pairs else 0.0
    security_rate = 1.0 - targeted_asr
    secure_utility = _avg_bool([u and not s for u, s in zip(utility_pairs, security_pairs)])
    return {
        "run_name": run_name,
        "suite": "all",
        "defense": runs[0].get("defense"),
        "attack": runs[0].get("attack"),
        "metric_schema_version": "agentdojo_metrics_v2",
        "utility_under_attack": _avg_bool(utility_pairs),
        "user_utility": _avg_bool(utility_pairs),
        "security": security_rate,
        "security_rate": security_rate,
        "targeted_asr": targeted_asr,
        "secure_utility": secure_utility,
        "total_runtime_min": sum(float(r.get("total_runtime_min") or 0) for r in runs),
        "reposhield_audit_summary": {
            "reposhield_checked_calls": checked_calls,
            "reposhield_unknown_tools": unknown_tools,
            "reposhield_registered_tools": registered_tools,
            "reposhield_unknown_tool_rate": unknown_tools / max(checked_calls, 1),
            "reposhield_registered_tool_rate": registered_tools / max(checked_calls, 1),
            "reposhield_policy_decisions": dict(decision_counts),
            "reposhield_p95_policy_latency_ms": max(policy_p95s) if policy_p95s else 0.0,
            "reposhield_p95_audit_latency_ms": max(audit_p95s) if audit_p95s else 0.0,
        },
    }


def _avg_bool(values: list[bool]) -> float:
    return float(sum(1.0 if bool(v) else 0.0 for v in values) / len(values)) if values else 0.0


def render_summary(
    rows: list[dict[str, Any]],
    ablation_rows: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    invariants: dict[str, dict[str, Any]],
) -> str:
    out = ["# AgentDojo ToolGate Summary", ""]
    out += [
        "## Main Results",
        "",
        "| Method | Utility Under Attack | Security | Targeted ASR | 总耗时(min) | 说明 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        if row.get("status") == "Not implemented":
            out.append(f"| {row['method']} | - | - | - | - | Not implemented |")
        else:
            out.append(
                f"| {row['method']} | {fmt(row.get('utility_under_attack'))} | {fmt(row.get('security'))} | {fmt(row.get('targeted_asr'))} | {fmt(row.get('total_runtime_min'))} | {row.get('defense')} / {row.get('attack')} |"
            )
    out += ["", "## Ablations", "", "| Version | Security | Targeted ASR | Utility Under Attack | 说明 |", "|---|---:|---:|---:|---|"]
    for row in ablation_rows:
        if row.get("status") == "Not implemented":
            out.append(f"| {row['method']} | - | - | - | Not implemented |")
        else:
            out.append(
                f"| {row['method']} | {fmt(row.get('security'))} | {fmt(row.get('targeted_asr'))} | {fmt(row.get('utility_under_attack'))} | {row.get('run_name')} |"
            )
    out += [
        "",
        "## Tool Coverage",
        "",
        "| Run | ToolGate Calls | Unknown Rate | Registered Rate | Policy p95(ms) | Audit p95(ms) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in audit_rows:
        out.append(
            f"| {row['run_name']} | {fmt(row.get('tool_gate_calls'))} | {fmt(row.get('unknown_tool_rate'))} | {fmt(row.get('registered_tool_rate'))} | {fmt(row.get('policy_p95_ms'))} | {fmt(row.get('audit_p95_ms'))} |"
        )
    out += ["", "## Invariant Hits", "", "| Invariant | Hits | Decision | Typical suite | Typical tool |", "|---|---:|---|---|---|"]
    for rule_id, info in sorted(invariants.items()):
        out.append(
            f"| {rule_id} | {info.get('hits', 0)} | {info.get('decision', '-')} | {info.get('suite', '-')} | {info.get('tool', '-')} |"
        )
    return "\n".join(out) + "\n"


def render_audit_check(runs: list[dict[str, Any]]) -> str:
    lines = ["# RepoShield Audit Check", ""]
    for run in runs:
        audit = run.get("reposhield_audit_summary")
        if not audit:
            continue
        lines.append(
            f"- {run.get('run_name')}: checked={audit.get('reposhield_checked_calls')} blocks={audit.get('reposhield_blocks')} unknown_rate={fmt(audit.get('reposhield_unknown_tool_rate'))}"
        )
    if len(lines) == 2:
        lines.append("- No RepoShield audit logs were found.")
    return "\n".join(lines) + "\n"


def _collect_invariant_hits() -> dict[str, dict[str, Any]]:
    counts: Counter[str] = Counter()
    witness: dict[str, dict[str, Any]] = {}
    for audit_path in ROOT.joinpath("logs").glob("*/agentdojo_audit.jsonl"):
        events = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        action_tool: dict[str, tuple[str, str]] = {}
        for event in events:
            if event.get("event_type") == "agentdojo_tool_gate_decision":
                payload = event.get("payload") or {}
                action_tool[str(event.get("action_id"))] = (str(payload.get("suite") or "-"), str(payload.get("tool_name") or "-"))
        for event in events:
            if event.get("event_type") != "policy_decision":
                continue
            payload = event.get("payload") or {}
            suite = None
            tool = None
            if payload.get("action_id") and payload["action_id"] in action_tool:
                suite, tool = action_tool[payload["action_id"]]
            for rule in payload.get("matched_rules", []) or []:
                rule_id = str(rule.get("rule_id") or rule.get("invariant_id") or "unknown")
                counts[rule_id] += 1
                witness.setdefault(rule_id, {"hits": 0, "decision": payload.get("decision"), "suite": suite or "-", "tool": tool or "-"})
                witness[rule_id]["hits"] = counts[rule_id]
    return witness


def fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
