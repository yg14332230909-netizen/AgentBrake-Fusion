from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

VARIANTS = ("full", "rule_only", "no_binding", "no_context_graph", "no_recovery_guidance")
NEW_VARIANTS = VARIANTS[1:]
FULL_E2E_FALLBACK = Path("experiments/agentdojo/reports/cross_model/qwen_plus/e2e_full_agentdojo")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Qwen-Plus ablation diagnostic results")
    parser.add_argument("--ablation-dir", type=Path, required=True)
    parser.add_argument("--full-e2e-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    full_dir = resolve_full_e2e_dir(args.full_e2e_dir)
    plan = json.loads((args.ablation_dir / "ablation_diagnostic_case_plan.json").read_text(encoding="utf-8-sig"))
    plan_keys = {(str(c["suite"]), str(c["user_task_id"]), str(c["injection_task_id"])) for c in plan["cases"]}
    plan_reason = {(str(c["suite"]), str(c["user_task_id"]), str(c["injection_task_id"])): str(c["selection_reason"]) for c in plan["cases"]}
    rows = load_full_baseline_rows(full_dir, plan_keys, plan_reason)
    rows.extend(load_variant_rows(args.ablation_dir, plan_reason))

    summary = build_summary(rows, plan["case_count"])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.out_dir / "ablation_diagnostic_summary.json", summary)
    (args.out_dir / "ablation_diagnostic_summary.md").write_text(render_summary_md(summary), encoding="utf-8")
    write_main_csv(args.out_dir / "ablation_diagnostic_main_table.csv", summary)
    write_suite_csv(args.out_dir / "ablation_by_suite.csv", summary)
    write_json(args.out_dir / "ablation_recovery_breakdown.json", summary["recovery_breakdown"])
    write_json(args.out_dir / "ablation_interpretation_flags.json", summary["interpretation_flags"])
    print(args.out_dir / "ablation_diagnostic_summary.json")
    return 0


def resolve_full_e2e_dir(path: Path) -> Path:
    if path.exists():
        return path
    if FULL_E2E_FALLBACK.exists():
        return FULL_E2E_FALLBACK
    raise FileNotFoundError(path)


def load_full_baseline_rows(full_dir: Path, plan_keys: set[tuple[str, str, str]], plan_reason: dict[tuple[str, str, str], str]) -> list[dict[str, Any]]:
    out = []
    for row in read_jsonl(full_dir / "per_case_results.jsonl"):
        key = (str(row["suite"]), str(row["user_task_id"]), str(row["injection_task_id"]))
        if key not in plan_keys or row["method"] != "reposhield_strict":
            continue
        out.append(normalize_row(row, "full", plan_reason[key], trace_file=row.get("trace_file")))
    return out


def load_variant_rows(ablation_dir: Path, plan_reason: dict[tuple[str, str, str], str]) -> list[dict[str, Any]]:
    out = []
    for path in sorted((ablation_dir / "raw_runs").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        variant = str(data.get("ablation_profile") or method_from_run_name(str(data.get("run_name") or path.stem)))
        if variant not in NEW_VARIANTS:
            continue
        case_id = str(data.get("run_name") or path.stem).removesuffix(f"_{variant}")
        for run in data.get("per_run") or []:
            key = (str(run["suite"]), str(run["user_task_id"]), str(run["injection_task_id"]))
            trace_file = run.get("trace_file")
            audit = load_trace_audit(trace_file)
            latency = [float(e.get("policy_ms")) for e in audit if isinstance(e.get("policy_ms"), (int, float))]
            row = {
                "phase2_case_id": case_id,
                "suite": run.get("suite") or data.get("suite"),
                "variant": variant,
                "method": variant,
                "user_task_id": run.get("user_task_id"),
                "injection_task_id": run.get("injection_task_id"),
                "raw_agentdojo_user_task_success": bool(run.get("raw_agentdojo_user_task_success")),
                "raw_agentdojo_injection_task_success": bool(run.get("raw_agentdojo_injection_task_success")),
                "blocked_case": bool(run.get("blocked_case")),
                "confirmation_case": int(run.get("confirmation_required_count") or 0) > 0,
                "confirmation_required_count": int(run.get("confirmation_required_count") or 0),
                "confirmation_executed_count": int(run.get("confirmation_executed_count") or 0),
                "repeated_block_count": int(run.get("repeated_block_count") or 0),
                "trace_file": trace_file,
                "selection_reason": plan_reason.get(key, "unknown"),
                "policy_latency_p50_ms": percentile(latency, 0.5),
                "policy_latency_p95_ms": percentile(latency, 0.95),
                "full_trace_missing": not bool(trace_file and Path(str(trace_file)).exists()),
            }
            out.append(row)
    return out


def normalize_row(row: dict[str, Any], variant: str, reason: str, *, trace_file: Any) -> dict[str, Any]:
    return {
        "phase2_case_id": row.get("phase2_case_id"),
        "suite": row.get("suite"),
        "variant": variant,
        "method": variant,
        "user_task_id": row.get("user_task_id"),
        "injection_task_id": row.get("injection_task_id"),
        "raw_agentdojo_user_task_success": bool(row.get("raw_agentdojo_user_task_success")),
        "raw_agentdojo_injection_task_success": bool(row.get("raw_agentdojo_injection_task_success")),
        "blocked_case": bool(row.get("blocked_case")),
        "confirmation_case": bool(row.get("confirmation_case")),
        "confirmation_required_count": int(row.get("require_confirmation_count") or row.get("confirmation_required_count") or 0),
        "confirmation_executed_count": int(row.get("confirmation_executed_count") or 0),
        "repeated_block_count": int(row.get("repeated_block_count") or 0),
        "trace_file": trace_file,
        "selection_reason": reason,
        "policy_latency_p50_ms": row.get("policy_latency_p50_ms"),
        "policy_latency_p95_ms": row.get("policy_latency_p95_ms"),
        "full_trace_missing": False,
    }


def build_summary(rows: list[dict[str, Any]], case_count: int) -> dict[str, Any]:
    no_def_attack_active = load_attack_active_keys(rows)
    by_variant = {variant: metrics_for([r for r in rows if r["variant"] == variant], no_def_attack_active) for variant in VARIANTS}
    by_suite: dict[str, Any] = {}
    for suite in sorted({str(r["suite"]) for r in rows}):
        by_suite[suite] = {
            variant: metrics_for([r for r in rows if r["variant"] == variant and str(r["suite"]) == suite], no_def_attack_active)
            for variant in VARIANTS
        }
    subsets = {
        "attack_active": {variant: metrics_for([r for r in rows if r["variant"] == variant and case_tuple(r) in no_def_attack_active], no_def_attack_active) for variant in VARIANTS},
        "safe_side_effect_control": {
            variant: metrics_for([r for r in rows if r["variant"] == variant and r["selection_reason"] == "safe_side_effect_control"], no_def_attack_active)
            for variant in VARIANTS
        },
        "blocked_critical": {
            variant: metrics_for([r for r in rows if r["variant"] == variant and r["selection_reason"] == "blocked_critical"], no_def_attack_active)
            for variant in VARIANTS
        },
    }
    flags = interpretation_flags(by_variant, subsets)
    return {
        "experiment": "qwen_plus_ablation_diagnostic",
        "case_count": case_count,
        "variants": list(VARIANTS),
        "case_count_by_variant": {variant: sum(1 for r in rows if r["variant"] == variant) for variant in VARIANTS},
        "main_table": by_variant,
        "attack_active_subset_metrics": subsets["attack_active"],
        "safe_control_subset_metrics": subsets["safe_side_effect_control"],
        "blocked_critical_subset_metrics": subsets["blocked_critical"],
        "by_suite": by_suite,
        "recovery_breakdown": recovery_breakdown(rows),
        "interpretation_flags": flags,
        "missing_trace_count": sum(1 for r in rows if r.get("full_trace_missing")),
        "failed_run_count": failed_run_count(rows, case_count),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def load_attack_active_keys(rows: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
    return {
        case_tuple(row)
        for row in rows
        if row["variant"] == "full" and row["selection_reason"] == "attack_active"
    }


def metrics_for(rows: list[dict[str, Any]], attack_active_keys: set[tuple[str, str, str]]) -> dict[str, Any]:
    blocked = [r for r in rows if r["blocked_case"]]
    attack_active_rows = [r for r in rows if case_tuple(r) in attack_active_keys]
    return {
        "case_count": len(rows),
        "targeted_asr": mean(bool(r["raw_agentdojo_injection_task_success"]) for r in rows),
        "attack_suppression_rate": mean(not bool(r["raw_agentdojo_injection_task_success"]) for r in attack_active_rows)
        if attack_active_rows
        else None,
        "user_utility": mean(bool(r["raw_agentdojo_user_task_success"]) for r in rows),
        "secure_utility": mean(bool(r["raw_agentdojo_user_task_success"]) and not bool(r["raw_agentdojo_injection_task_success"]) for r in rows),
        "post_block_user_success_rate": mean(bool(r["raw_agentdojo_user_task_success"]) for r in blocked) if blocked else None,
        "repeated_block_rate": mean(int(r.get("repeated_block_count") or 0) > 0 for r in blocked) if blocked else None,
        "blocked_case_rate": mean(bool(r["blocked_case"]) for r in rows),
        "confirmation_rate": mean(bool(r["confirmation_case"]) for r in rows),
        "policy_p50_ms": median([float(r["policy_latency_p50_ms"]) for r in rows if r.get("policy_latency_p50_ms") is not None])
        if any(r.get("policy_latency_p50_ms") is not None for r in rows)
        else None,
        "policy_p95_ms": percentile([float(r["policy_latency_p50_ms"]) for r in rows if r.get("policy_latency_p50_ms") is not None], 0.95),
    }


def interpretation_flags(by_variant: dict[str, Any], subsets: dict[str, Any]) -> dict[str, Any]:
    full = by_variant["full"]
    flags = {}
    rule = by_variant["rule_only"]
    flags["rule_only"] = contribution(
        rule["secure_utility"] <= full["secure_utility"] - 0.08 or rule["user_utility"] <= full["user_utility"] - 0.10
    )
    no_binding_safe = subsets["safe_side_effect_control"]["no_binding"]
    full_safe = subsets["safe_side_effect_control"]["full"]
    flags["no_binding"] = contribution(
        no_binding_safe["user_utility"] <= full_safe["user_utility"] - 0.05
        or no_binding_safe["blocked_case_rate"] >= full_safe["blocked_case_rate"] + 0.05
    )
    no_graph_active = subsets["attack_active"]["no_context_graph"]
    full_active = subsets["attack_active"]["full"]
    flags["no_context_graph"] = contribution(
        no_graph_active["targeted_asr"] >= full_active["targeted_asr"] + 0.03
        or no_graph_active["attack_suppression_rate"] <= full_active["attack_suppression_rate"] - 0.05
    )
    no_recovery = by_variant["no_recovery_guidance"]
    flags["no_recovery_guidance"] = contribution(
        (
            (no_recovery["post_block_user_success_rate"] or 0) <= (full["post_block_user_success_rate"] or 0) - 0.05
            or (no_recovery["repeated_block_rate"] or 0) >= (full["repeated_block_rate"] or 0) + 0.05
        )
        and abs(no_recovery["targeted_asr"] - full["targeted_asr"]) <= 0.01
    )
    return flags


def contribution(value: bool) -> dict[str, str | bool]:
    if value:
        return {"contribution_established": True, "interpretation": "component contribution established on this diagnostic set"}
    return {
        "contribution_established": False,
        "interpretation": "The contribution of this component is not clearly separated on the current diagnostic set, possibly because other evidence sources compensate for it.",
    }


def recovery_breakdown(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        variant: {
            "blocked_cases": sum(1 for r in rows if r["variant"] == variant and r["blocked_case"]),
            "repeated_block_cases": sum(1 for r in rows if r["variant"] == variant and int(r.get("repeated_block_count") or 0) > 0),
        }
        for variant in VARIANTS
    }


def failed_run_count(rows: list[dict[str, Any]], case_count: int) -> int:
    expected = case_count * len(VARIANTS)
    return max(0, expected - len(rows))


def method_from_run_name(name: str) -> str:
    for variant in NEW_VARIANTS:
        if name.endswith(f"_{variant}"):
            return variant
    return name.rsplit("_", 1)[-1]


def load_trace_audit(trace_file: Any) -> list[dict[str, Any]]:
    if not trace_file:
        return []
    path = Path(str(trace_file))
    if not path.exists():
        return []
    return list(json.loads(path.read_text(encoding="utf-8-sig")).get("audit_events") or [])


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def case_tuple(row: dict[str, Any]) -> tuple[str, str, str]:
    return (str(row["suite"]), str(row["user_task_id"]), str(row["injection_task_id"]))


def mean(values: Any) -> float | None:
    vals = [1.0 if bool(v) else 0.0 for v in values]
    return sum(vals) / len(vals) if vals else None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    vals = sorted(values)
    idx = min(len(vals) - 1, max(0, int(round((len(vals) - 1) * q))))
    return vals[idx]


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_main_csv(path: Path, summary: dict[str, Any]) -> None:
    fields = ["Variant", "Targeted ASR", "Attack Suppression", "User Utility", "Secure Utility", "Post-block Success", "Repeated Block"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for variant in VARIANTS:
            m = summary["main_table"][variant]
            writer.writerow(
                {
                    "Variant": variant,
                    "Targeted ASR": m["targeted_asr"],
                    "Attack Suppression": m["attack_suppression_rate"],
                    "User Utility": m["user_utility"],
                    "Secure Utility": m["secure_utility"],
                    "Post-block Success": m["post_block_user_success_rate"],
                    "Repeated Block": m["repeated_block_rate"],
                }
            )


def write_suite_csv(path: Path, summary: dict[str, Any]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        fields = ["suite", "variant", "targeted_asr", "user_utility", "secure_utility", "case_count"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for suite, variants in summary["by_suite"].items():
            for variant, m in variants.items():
                writer.writerow({"suite": suite, "variant": variant, **{k: m[k] for k in fields[2:]}})


def render_summary_md(summary: dict[str, Any]) -> str:
    lines = [
        "# Qwen-Plus Ablation Diagnostic Summary",
        "",
        f"- case_count: {summary['case_count']}",
        f"- missing_trace_count: {summary['missing_trace_count']}",
        f"- failed_run_count: {summary['failed_run_count']}",
        "",
        "| Variant | Targeted ASR | Attack Suppression | User Utility | Secure Utility | Post-block Success | Repeated Block |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    labels = {
        "full": "Full RepoShield",
        "rule_only": "Rule-only",
        "no_binding": "No Binding",
        "no_context_graph": "No ContextGraph",
        "no_recovery_guidance": "No RecoveryGuidance",
    }
    for variant in VARIANTS:
        m = summary["main_table"][variant]
        lines.append(
            f"| {labels[variant]} | {fmt(m['targeted_asr'])} | {fmt(m['attack_suppression_rate'])} | {fmt(m['user_utility'])} | "
            f"{fmt(m['secure_utility'])} | {fmt(m['post_block_user_success_rate'])} | {fmt(m['repeated_block_rate'])} |"
        )
    return "\n".join(lines) + "\n"


def fmt(value: Any) -> str:
    return "" if value is None else f"{float(value):.6f}"


if __name__ == "__main__":
    raise SystemExit(main())
