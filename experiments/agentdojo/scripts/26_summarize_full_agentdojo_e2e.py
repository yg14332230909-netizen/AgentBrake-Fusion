from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPORTS = ROOT / "experiments" / "agentdojo" / "reports" / "deepseekv4_flash" / "e2e_full_agentdojo"
PHASE2_SCRIPT = Path(__file__).with_name("22_summarize_e2e_phase2.py")
METHODS = ("no_defense", "tool_filter", "reposhield_strict", "reposhield_gateway_eval", "reposhield_oracle_user_eval")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize full-distribution AgentDojo Phase 2.2 E2E runs")
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS)
    args = parser.parse_args()

    summarizer = load_phase2_summarizer()
    rows = summarizer.load_per_case_rows(args.reports_dir)
    summarizer.write_jsonl(args.reports_dir / "per_case_results.jsonl", rows)
    summary = summarizer.build_summary(rows)
    summary["phase"] = "phase2.2"
    summary["experiment_type"] = "agentdojo_e2e_full_distribution"
    write_json(args.reports_dir / "e2e_full_summary.json", summary)
    (args.reports_dir / "e2e_full_summary.md").write_text(render_full_summary_md(summary), encoding="utf-8")
    summarizer.write_aggregate_csv(args.reports_dir / "aggregate.csv", summary)

    recovery = summarizer.build_recovery_summary(rows)
    write_json(args.reports_dir / "blocked_recovery_summary.json", recovery)
    (args.reports_dir / "blocked_recovery_summary.md").write_text(summarizer.render_recovery_md(recovery), encoding="utf-8")
    confirmation = summarizer.build_confirmation_summary(rows)
    write_json(args.reports_dir / "confirmation_summary.json", confirmation)
    (args.reports_dir / "confirmation_summary.md").write_text(summarizer.render_confirmation_md(confirmation), encoding="utf-8")
    failures = summarizer.build_failure_clusters(rows)
    write_json(args.reports_dir / "failure_clusters.json", failures)
    (args.reports_dir / "failure_clusters.md").write_text(summarizer.render_failure_clusters_md(failures), encoding="utf-8")
    summarizer.write_grouped_raw(args.reports_dir, args.reports_dir, rows)

    attack_active = build_attack_active_subset_summary(rows)
    write_json(args.reports_dir / "attack_active_subset_summary.json", attack_active)
    (args.reports_dir / "attack_active_subset_summary.md").write_text(render_attack_active_md(attack_active), encoding="utf-8")
    excluded = build_excluded_manifest(args.reports_dir, rows)
    if excluded["excluded_raw_runs"] or excluded["excluded_full_traces"]:
        write_json(args.reports_dir / "excluded_runs_manifest.json", excluded)
    comparison = build_replay_vs_e2e_comparison(args.reports_dir, summary, attack_active)
    write_json(args.reports_dir / "replay_vs_e2e_comparison.json", comparison)
    (args.reports_dir / "replay_vs_e2e_comparison.md").write_text(render_comparison_md(comparison), encoding="utf-8")
    artifact_manifest = build_artifact_manifest(args.reports_dir)
    write_json(args.reports_dir / "artifact_manifest.json", artifact_manifest)
    (args.reports_dir / "validation_commands.txt").write_text(render_validation_commands(args.reports_dir), encoding="utf-8")
    (args.reports_dir / "validation_outputs.txt").write_text(render_validation_outputs(summary, attack_active, excluded), encoding="utf-8")
    print(args.reports_dir / "e2e_full_summary.json")
    return 0


def load_phase2_summarizer() -> Any:
    spec = importlib.util.spec_from_file_location("phase2_summarizer", PHASE2_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load phase2 summarizer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_attack_active_subset_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active_ids = {row["phase2_case_id"] for row in rows if row["method"] == "no_defense" and row["raw_agentdojo_injection_task_success"]}
    methods: dict[str, Any] = {}
    baseline_count = len(active_ids)
    for method in METHODS:
        method_rows = [row for row in rows if row["method"] == method and row["phase2_case_id"] in active_ids]
        attack_successes = sum(1 for row in method_rows if row["raw_agentdojo_injection_task_success"])
        user_successes = sum(1 for row in method_rows if row["raw_agentdojo_user_task_success"])
        secure_successes = sum(1 for row in method_rows if row["raw_agentdojo_user_task_success"] and not row["raw_agentdojo_injection_task_success"])
        methods[method] = {
            "case_count": len(method_rows),
            "targeted_asr": ratio(attack_successes, len(method_rows)),
            "security_rate": 1.0 - ratio(attack_successes, len(method_rows)) if method_rows else None,
            "user_utility": ratio(user_successes, len(method_rows)),
            "secure_utility": ratio(secure_successes, len(method_rows)),
            "attack_suppression": 1.0 - ratio(attack_successes, baseline_count) if baseline_count else None,
        }
    return {
        "definition": "cases where no_defense raw_agentdojo_injection_task_success is true",
        "case_count": baseline_count,
        "methods": methods,
    }


def build_excluded_manifest(reports_dir: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    included_runs = {f"{row['phase2_case_id']}_{row['method']}.json" for row in rows}
    included_traces = {str(row.get("trace_file") or "").replace("\\", "/") for row in rows if row.get("trace_file")}
    raw_files = sorted(path for path in (reports_dir / "raw_runs").glob("*.json"))
    trace_files = sorted(path for path in (reports_dir / "full_traces").glob("**/*.json"))
    excluded_raw = [relative(path, reports_dir) for path in raw_files if path.name not in included_runs]
    excluded_traces = [relative(path, reports_dir) for path in trace_files if relative(path, reports_dir) not in included_traces]
    return {
        "reason": "raw/full trace files outside the frozen counted plan are excluded from metrics",
        "included_row_count": len(rows),
        "excluded_raw_runs": excluded_raw,
        "excluded_full_traces": excluded_traces,
    }


def build_replay_vs_e2e_comparison(reports_dir: Path, summary: dict[str, Any], attack_active: dict[str, Any]) -> dict[str, Any]:
    phase1_path = ROOT / "experiments" / "agentdojo" / "reports" / "deepseekv4_flash" / "replay" / "agentdojo_derived_replay_summary.json"
    phase1 = json.loads(phase1_path.read_text(encoding="utf-8")) if phase1_path.exists() else {}
    strict = (summary.get("methods") or {}).get("reposhield_strict") or {}
    return {
        "comparison_scope": "full_agentdojo_all_pairs",
        "metrics_source": "e2e_full_summary.json",
        "full_phase2_case_count": summary.get("case_count"),
        "linked_subset_case_count": attack_active.get("case_count"),
        "phase1_2_replay": {
            "case_count": phase1.get("case_count"),
            "unsafe_interception_rate": phase1.get("unsafe_interception_rate"),
            "safe_pass_rate": phase1.get("safe_pass_rate"),
            "false_positive_rate": phase1.get("false_positive_rate"),
        },
        "full_e2e": {
            "reposhield_strict_targeted_asr": strict.get("targeted_asr"),
            "reposhield_strict_user_utility": strict.get("user_utility"),
            "reposhield_strict_secure_utility": strict.get("secure_utility"),
            "attack_active_case_count": attack_active.get("case_count"),
        },
        "artifact_dir": relative(reports_dir, ROOT),
    }


def build_artifact_manifest(reports_dir: Path) -> dict[str, Any]:
    names = [
        "full_agentdojo_case_plan.json",
        "full_agentdojo_case_plan.sha256",
        "full_agentdojo_case_plan_rationale.md",
        "dry_run_summary.json",
        "dry_run_summary.md",
        "e2e_full_summary.json",
        "e2e_full_summary.md",
        "aggregate.csv",
        "per_case_results.jsonl",
        "attack_active_subset_summary.json",
        "attack_active_subset_summary.md",
        "blocked_recovery_summary.json",
        "blocked_recovery_summary.md",
        "confirmation_summary.json",
        "confirmation_summary.md",
        "failure_clusters.json",
        "failure_clusters.md",
        "replay_vs_e2e_comparison.json",
        "replay_vs_e2e_comparison.md",
        "final_acceptance_full_agentdojo.json",
        "final_acceptance_full_agentdojo.md",
        "validation_commands.txt",
        "validation_outputs.txt",
    ]
    return {"artifacts": [{"path": name, "exists": (reports_dir / name).exists()} for name in names]}


def render_full_summary_md(summary: dict[str, Any]) -> str:
    lines = ["# Full AgentDojo E2E Summary", "", "| method | cases | targeted_asr | security | user_utility | secure_utility | confirmation_execute | repeated_block |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for method, metrics in (summary.get("methods") or {}).items():
        lines.append(
            f"| {method} | {metrics.get('case_count')} | {fmt(metrics.get('targeted_asr'))} | {fmt(metrics.get('security_rate'))} | {fmt(metrics.get('user_utility'))} | {fmt(metrics.get('secure_utility'))} | {fmt(metrics.get('confirmation_execute_rate'))} | {fmt(metrics.get('repeated_block_rate'))} |"
        )
    return "\n".join(lines) + "\n"


def render_attack_active_md(summary: dict[str, Any]) -> str:
    lines = ["# Attack-Active Subset Summary", "", f"- case_count: {summary['case_count']}", "", "| method | cases | targeted_asr | suppression | secure_utility |", "|---|---:|---:|---:|---:|"]
    for method, metrics in summary["methods"].items():
        lines.append(f"| {method} | {metrics['case_count']} | {fmt(metrics['targeted_asr'])} | {fmt(metrics['attack_suppression'])} | {fmt(metrics['secure_utility'])} |")
    return "\n".join(lines) + "\n"


def render_comparison_md(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Replay vs Full E2E Comparison",
            "",
            f"- comparison_scope: {report['comparison_scope']}",
            f"- metrics_source: {report['metrics_source']}",
            f"- full_phase2_case_count: {report['full_phase2_case_count']}",
            f"- linked_subset_case_count: {report['linked_subset_case_count']}",
            f"- strict_targeted_asr: {report['full_e2e'].get('reposhield_strict_targeted_asr')}",
            f"- strict_secure_utility: {report['full_e2e'].get('reposhield_strict_secure_utility')}",
        ]
    ) + "\n"


def render_validation_commands(reports_dir: Path) -> str:
    rel = relative(reports_dir, ROOT)
    commands = [
        "python -m ruff check experiments/agentdojo/scripts tests",
        "python -m pytest tests/eval/agentdojo/unit tests/policy_engine",
        "python -m pytest",
        "python experiments/agentdojo/scripts/25_plan_full_agentdojo_e2e.py --out-dir " + rel,
        "python experiments/agentdojo/scripts/21_run_e2e_phase2.py --case-plan " + rel + "/full_agentdojo_case_plan.json --out-dir " + rel + " --methods no_defense tool_filter reposhield_strict reposhield_gateway_eval reposhield_oracle_user_eval --dry-run --save-full-trace",
        "python experiments/agentdojo/scripts/21_run_e2e_phase2.py --case-plan " + rel + "/full_agentdojo_case_plan.json --out-dir " + rel + " --methods no_defense tool_filter reposhield_strict reposhield_gateway_eval reposhield_oracle_user_eval --save-full-trace --skip-existing",
        "python experiments/agentdojo/scripts/26_summarize_full_agentdojo_e2e.py --reports-dir " + rel,
        "python experiments/agentdojo/scripts/27_check_full_agentdojo_acceptance.py --reports-dir " + rel,
    ]
    return "\n".join(commands) + "\n"


def render_validation_outputs(summary: dict[str, Any], attack_active: dict[str, Any], excluded: dict[str, Any]) -> str:
    return "\n".join(
        [
            "e2e_full_summary.json generated",
            f"case_count={summary.get('case_count')}",
            f"row_count={summary.get('row_count')}",
            f"attack_active_case_count={attack_active.get('case_count')}",
            f"excluded_raw_runs={len(excluded.get('excluded_raw_runs') or [])}",
            f"excluded_full_traces={len(excluded.get('excluded_full_traces') or [])}",
        ]
    ) + "\n"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def fmt(value: Any) -> str:
    return "null" if value is None else f"{float(value):.4f}"


def relative(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
