from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def main() -> int:
    summary_path = REPORTS / "summary.json"
    if not summary_path.exists():
        raise SystemExit("Run 08_collect_results.py first.")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    lines = [
        "# Latency Profile",
        "",
        "| Run | policy_p50_ms | policy_p95_ms | audit_p95_ms | total_runtime_min |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary.get("audit_rows", []):
        run = next((r for r in summary.get("runs", []) if r.get("run_name") == row.get("run_name")), {})
        audit = run.get("reposhield_audit_summary") or {}
        lines.append(
            f"| {row.get('run_name')} | {fmt(audit.get('reposhield_p50_policy_latency_ms'))} | {fmt(audit.get('reposhield_p95_policy_latency_ms'))} | {fmt(row.get('audit_p95_ms'))} | {fmt(run.get('total_runtime_min'))} |"
        )
    (REPORTS / "latency_profile.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


def fmt(value):
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
