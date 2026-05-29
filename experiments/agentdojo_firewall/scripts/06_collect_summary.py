from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "experiments" / "agentdojo_firewall" / "reports"
RUN_DIR = REPORT_DIR / "runs"
SUMMARY_MD = REPORT_DIR / "summary.md"


def _rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not RUN_DIR.exists():
        return rows
    for path in sorted(RUN_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        audit = data.get("agentdojo_firewall_audit_summary") or data.get("reposhield_audit_summary") or {}
        rows.append(
            {
                "method": data.get("defense", path.stem),
                "suite": data.get("suite", ""),
                "utility": data.get("utility_under_attack", 0.0),
                "security": data.get("security", 0.0),
                "asr": data.get("targeted_asr", 0.0),
                "runtime": data.get("total_runtime_min", 0.0),
                "registered_tool_rate": audit.get("registered_tool_rate", 0.0),
                "unknown_tool_rate": audit.get("unknown_tool_rate", 0.0),
                "total_tool_calls_gated": audit.get("total_tool_calls_gated", 0),
                "blocked_tool_calls": audit.get("blocked_tool_calls", 0),
                "policy_p50_ms": audit.get("policy_p50_ms", 0.0),
                "policy_p95_ms": audit.get("policy_p95_ms", 0.0),
                "rule_hit_counts": audit.get("rule_hit_counts", {}),
            }
        )
    return rows


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = _rows()
    lines = [
        "# AgentDojo Firewall Summary",
        "",
        "| Method | Utility Under Attack | Security | Targeted ASR | Runtime | Notes |",
        "|---|---:|---:|---:|---:|---|",
    ]
    if rows:
        for row in rows:
            lines.append(
                f"| {row['method']} | {row['utility']:.3f} | {row['security']:.3f} | {row['asr']:.3f} | {row['runtime']:.2f} | suite={row['suite']} |"
            )
    else:
        lines.append("| _no run reports found_ |  |  |  |  | run the scripts in `experiments/agentdojo_firewall/scripts/` first |")
    lines.extend(
        [
            "",
            "## Firewall Stats",
            "",
            "| Metric | Value |",
            "|---|---:|",
        ]
    )
    if rows:
        latest = rows[-1]
        for key in ("registered_tool_rate", "unknown_tool_rate", "total_tool_calls_gated", "blocked_tool_calls", "policy_p50_ms", "policy_p95_ms"):
            lines.append(f"| {key} | {latest[key]} |")
        lines.append("")
        lines.append("## Rule Hit Counts")
        lines.append("")
        for rule_id, count in sorted((latest.get("rule_hit_counts") or {}).items()):
            lines.append(f"- {rule_id}: {count}")
    else:
        for key in ("registered_tool_rate", "unknown_tool_rate", "total_tool_calls_gated", "blocked_tool_calls", "policy_p50_ms", "policy_p95_ms"):
            lines.append(f"| {key} | n/a |")
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(SUMMARY_MD)


if __name__ == "__main__":
    main()
