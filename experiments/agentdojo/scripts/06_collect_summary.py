from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "experiments" / "agentdojo_firewall" / "reports"
LOG_DIR = ROOT / "experiments" / "agentdojo_firewall" / "logs"


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    runs = load_run_reports()
    coverage = load_json(REPORT_DIR / "tool_coverage.json") or {}
    summary = {
        "runs": runs,
        "tool_coverage": coverage,
        "fairness": {
            "fair_mode": "Fair mode does not use injection ground truth.",
            "oracle_mode": "Oracle mode is an upper bound only.",
            "iterator": "The failure-sample iterator only generates candidate rules and does not merge them automatically.",
        },
    }
    (REPORT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (REPORT_DIR / "summary.md").write_text(render_summary(runs, coverage), encoding="utf-8")
    print(REPORT_DIR / "summary.md")


def load_run_reports() -> list[dict[str, Any]]:
    paths = list((REPORT_DIR / "runs").glob("*.json")) if (REPORT_DIR / "runs").exists() else []
    paths += list(LOG_DIR.glob("**/reports/*.json")) if LOG_DIR.exists() else []
    out: list[dict[str, Any]] = []
    for path in sorted(set(paths)):
        data = load_json(path)
        if isinstance(data, dict) and {"utility_under_attack", "security"} & set(data):
            data["_path"] = str(path)
            out.append(data)
    return out


def render_summary(runs: list[dict[str, Any]], coverage: dict[str, Any]) -> str:
    lines = ["# AgentDojo Firewall Summary", ""]
    lines.extend(render_main_results(runs))
    lines.extend(render_tool_coverage(coverage))
    lines.extend(render_decision_distribution(runs))
    lines.extend(render_rule_hits(runs))
    lines.extend(render_performance(runs))
    lines.extend(
        [
            "## Fairness Statement",
            "",
            "Fair mode does not use injection ground truth, InjectionTask.GOAL, InjectionTask.PROMPT, or final scoring state.",
            "",
            "Oracle mode is only an upper bound and must not be reported as the primary defense result.",
            "",
            "The failure-sample iterator only generates candidate rules. It does not automatically modify or merge core firewall rules.",
            "",
        ]
    )
    return "\n".join(lines)


def render_main_results(runs: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Table 1: AgentDojo Main Results",
        "",
        "| Method | Utility Under Attack ↑ | Security ↑ | Targeted ASR ↓ | Total Time | Notes |",
        "|---|---:|---:|---:|---:|---|",
    ]
    labels = {
        "none": "No Defense",
        "tool_filter": "Tool Filter",
        "gateway_only": "Gateway-only Fast",
        "reposhield_toolgate": "Gateway-only Fast",
        "agentdojo_firewall": "AgentDojo Firewall Fair",
    }
    rows = runs or []
    if not rows:
        rows = [
            {"defense": key, "utility_under_attack": 0, "security": 0, "targeted_asr": 0, "total_runtime_min": 0, "mode": ""}
            for key in ["none", "tool_filter", "gateway_only", "agentdojo_firewall"]
        ]
        rows.append(
            {
                "defense": "agentdojo_firewall",
                "utility_under_attack": 0,
                "security": 0,
                "targeted_asr": 0,
                "total_runtime_min": 0,
                "mode": "oracle_full",
            }
        )
    for run in rows:
        defense = str(run.get("defense", "unknown"))
        mode = str(run.get("mode", ""))
        label = "AgentDojo Firewall Oracle Upper Bound" if mode == "oracle_full" else labels.get(defense, defense)
        lines.append(
            f"| {label} | {float(run.get('utility_under_attack', 0.0)):.3f} | {float(run.get('security', 0.0)):.3f} | {float(run.get('targeted_asr', 0.0)):.3f} | {float(run.get('total_runtime_min', 0.0)):.2f} | suite={run.get('suite', '')} mode={mode or 'n/a'} |"
        )
    lines.append("")
    return lines


def render_tool_coverage(coverage: dict[str, Any]) -> list[str]:
    lines = [
        "## Table 2: Tool Coverage",
        "",
        "| Suite | Total tools | Registered tools | Unknown tools | Unknown rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for suite, item in sorted((coverage.get("suites") or {}).items()):
        lines.append(
            f"| {suite} | {item.get('official_tool_count', 0)} | {len(item.get('registered_tools', []))} | {len(item.get('unknown_tools', []))} | {float(item.get('unknown_tool_rate', 0.0)):.3f} |"
        )
    lines.append("")
    return lines


def render_decision_distribution(runs: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Table 3: ToolGate Decision Distribution",
        "",
        "| 方法 | allow | block | safe_blocked_result | unknown_tool | tool_gate_decisions |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for run in runs:
        audit = run.get("agentdojo_firewall_audit_summary") or {}
        decisions = int(audit.get("tool_gate_decision_count", audit.get("total_tool_calls_gated", 0)) or 0)
        block = int(audit.get("blocked_tool_calls", 0) or 0)
        unknown = round(float(audit.get("unknown_tool_rate", 0.0) or 0.0) * decisions)
        lines.append(f"| {run.get('defense', '')} | {decisions - block} | {block} | {block} | {unknown} | {decisions} |")
    lines.append("")
    return lines


def render_rule_hits(runs: list[dict[str, Any]]) -> list[str]:
    hits: Counter[str] = Counter()
    for run in runs:
        hits.update((run.get("agentdojo_firewall_audit_summary") or {}).get("rule_hit_counts") or {})
    lines = [
        "## Table 4: Rule Hits",
        "",
        "| Rule | Hits | Typical suite | Typical tool | Decision |",
        "|---|---:|---|---|---|",
    ]
    for rule, count in sorted(hits.items()):
        lines.append(f"| {rule} | {count} | mixed | mixed | block |")
    lines.append("")
    return lines


def render_performance(runs: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Table 5: Performance",
        "",
        "| 方法 | runtime_min | avg_sample_sec | policy_p50_ms | policy_p95_ms |",
        "|---|---:|---:|---:|---:|",
    ]
    for run in runs:
        audit = run.get("agentdojo_firewall_audit_summary") or {}
        sample_count = max(1, len(run.get("per_run") or []))
        runtime_sec = float(run.get("total_runtime_sec", 0.0) or 0.0)
        lines.append(
            f"| {run.get('defense', '')} | {float(run.get('total_runtime_min', 0.0)):.2f} | {runtime_sec / sample_count:.2f} | {float(audit.get('policy_p50_ms', 0.0)):.3f} | {float(audit.get('policy_p95_ms', 0.0)):.3f} |"
        )
    lines.append("")
    return lines


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


if __name__ == "__main__":
    main()
