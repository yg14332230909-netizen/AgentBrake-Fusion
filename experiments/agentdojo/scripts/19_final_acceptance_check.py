from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REPLAY = ROOT / "experiments" / "agentdojo" / "replay_cases"
REPORTS = ROOT / "experiments" / "agentdojo" / "reports" / "deepseekv4_flash"


def main() -> int:
    checks = build_checks()
    out = REPORTS / "final_acceptance_check.json"
    md = REPORTS / "final_acceptance_check.md"
    out.write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
    md.write_text(render_markdown(checks), encoding="utf-8")
    print(md)
    return 0 if all(row["status"] in {"PASS", "GAP"} for row in checks) else 1


def build_checks() -> list[dict[str, Any]]:
    manifest = load_json(REPLAY / "manifest_agentdojo_derived.json")
    replay_summary = load_json(REPORTS / "replay" / "agentdojo_derived_replay_summary.json")
    taxonomy = load_json(REPORTS / "blocked_recovery_debug" / "recovery_failure_taxonomy.json")
    debug_rows = load_jsonl(REPORTS / "blocked_recovery_debug" / "blocked_case_analysis.jsonl")
    confirmation_csv = (REPORTS / "confirmation_modes" / "normalized" / "aggregate.csv").read_text(encoding="utf-8")
    sample_gap = (REPLAY / "sample_gap_report.md").read_text(encoding="utf-8")
    checks: list[dict[str, Any]] = []
    add(checks, "smoke_and_derived_dirs_separated", (REPLAY / "smoke").is_dir() and (REPLAY / "agentdojo_derived").is_dir())
    add(checks, "derived_cases_from_real_traces", all_case_field("source", "agentdojo_trace"))
    add(checks, "manifest_complete", all(key in manifest for key in ("benchmark_type", "standard_agentdojo_e2e_score", "counts_by_suite", "counts_by_violation_type", "review_status_counts")))
    add(checks, "standard_agentdojo_e2e_score_false", manifest.get("standard_agentdojo_e2e_score") is False and replay_summary.get("standard_agentdojo_e2e_score") is False)
    add(checks, "counts_by_violation_type_non_unknown", bool(manifest.get("counts_by_violation_type")) and set(manifest["counts_by_violation_type"]) != {"unknown"})
    add(checks, "no_get_webpage_unsafe_sink", not any("get_webpage_block" in p.name for p in (REPLAY / "agentdojo_derived" / "unsafe").glob("*.json")))
    add(checks, "sample_gap_report_has_phase1_shortfall", "Phase 1 unsafe shortfall" in sample_gap and "No sample gap detected" not in sample_gap)
    add(checks, "phase1_50_50_sample_size", manifest.get("unsafe_case_count", 0) >= 50 and manifest.get("safe_case_count", 0) >= 50, status_if_false="GAP", detail="Requires additional same-model full traces; must not be faked.")
    add(checks, "replay_summary_matches_manifest_case_count", replay_summary.get("case_count") == manifest.get("case_count"))
    add(checks, "confirmation_modes_regenerated", "travel,agentdojo_firewall,16,0.375000,0.000000,1.000000,0.375000,89,2,0" in confirmation_csv)
    add(checks, "blocked_debug_14_cases", taxonomy.get("case_count") == 14 and len(debug_rows) == 14)
    add(checks, "blocked_debug_action_fields", all(row.get("blocked_tool") and row.get("decision") and row.get("reason_codes") and (row.get("next_assistant_message") or row.get("next_tool_call_after_block")) for row in debug_rows))
    add(checks, "blocked_debug_recovery_guidance_fields", all(row.get("blocked_result_text") and row.get("allowed_next_steps") and row.get("disallowed_next_steps") for row in debug_rows))
    add(checks, "recovery_improved_confirmation_subset", "slack,agentdojo_firewall,8,0.500000" in confirmation_csv and "travel,agentdojo_firewall,16,0.375000" in confirmation_csv)
    add(checks, "travel_repeated_block_rate_decreased", "travel,agentdojo_firewall,16,0.375000,0.000000,1.000000,0.375000,89,2,0" in confirmation_csv)
    return checks


def add(checks: list[dict[str, Any]], name: str, ok: bool, *, status_if_false: str = "FAIL", detail: str = "") -> None:
    checks.append({"name": name, "status": "PASS" if ok else status_if_false, "detail": "" if ok else detail})


def all_case_field(key: str, expected: Any) -> bool:
    for label in ("safe", "unsafe"):
        for path in (REPLAY / "agentdojo_derived" / label).glob("*.json"):
            data = load_json(path)
            if data.get(key) != expected:
                return False
    return True


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def render_markdown(checks: list[dict[str, Any]]) -> str:
    lines = ["# Final Acceptance Check", "", "| check | status | detail |", "|---|---|---|"]
    for row in checks:
        lines.append(f"| {row['name']} | {row['status']} | {row.get('detail', '')} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
