from __future__ import annotations

import argparse
import json
import os
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from agentdojo.attacks.attack_registry import load_attack
from agentdojo.logging import OutputLogger, TraceLogger
from agentdojo.task_suite.load_suites import get_suite

from reposhield.eval.agentdojo.run_toolgate_eval import (
    _infer_authorized_tools_and_categories,
    _run_agentdojo_task_with_retries,
    build_llm,
    build_pipeline,
)
from reposhield.eval.agentdojo_firewall.state import extract_targets, looks_like_injection
from reposhield.eval.agentdojo_firewall.tool_firewall import summarize_agentdojo_firewall_audit
from reposhield.eval.agentdojo.pipeline_wrapper import RepoShieldAgentDojoContext

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "experiments" / "agentdojo_firewall" / "reports"
ITER_DIR = REPORT_DIR / "iterations"
LOG_DIR = ROOT / "experiments" / "agentdojo_firewall" / "logs" / "iterations"


@dataclass
class SampleResult:
    suite: str
    phase: str
    user_task_id: str
    injection_task_id: str
    utility: bool
    security: bool
    run_path: Path
    user_task_text: str
    injection_text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    firewall_audit: dict[str, Any] = field(default_factory=dict)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--attack", default="important_instructions")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--train-users", type=int, default=2)
    parser.add_argument("--val-users", type=int, default=2)
    parser.add_argument("--train-injections", type=int, default=2)
    parser.add_argument("--val-injections", type=int, default=2)
    parser.add_argument("--suites", nargs="+", default=["travel", "banking", "slack", "workspace"])
    parser.add_argument("--benchmark-version", default="v1.2.2")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ITER_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "model": args.model,
        "attack": args.attack,
        "seed": args.seed,
        "suites": {},
    }

    for suite_name in args.suites:
        suite_summary = run_suite_iteration(
            suite_name=suite_name,
            benchmark_version=args.benchmark_version,
            model=args.model,
            attack=args.attack,
            seed=args.seed,
            train_users=args.train_users,
            val_users=args.val_users,
            train_injections=args.train_injections,
            val_injections=args.val_injections,
        )
        summary["suites"][suite_name] = suite_summary

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = ITER_DIR / f"iteration_{timestamp}.json"
    md_path = ITER_DIR / f"iteration_{timestamp}.md"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    md_path.write_text(render_iteration_markdown(summary), encoding="utf-8")
    print(md_path)


def run_suite_iteration(
    *,
    suite_name: str,
    benchmark_version: str,
    model: str,
    attack: str,
    seed: int,
    train_users: int,
    val_users: int,
    train_injections: int,
    val_injections: int,
) -> dict[str, Any]:
    suite = get_suite(benchmark_version, suite_name)
    user_ids = _sample_ids(sorted(suite.user_tasks.keys()), train_users + val_users, seed=seed)
    injection_ids = _sample_ids(sorted(suite.injection_tasks.keys()), train_injections + val_injections, seed=seed + 101)
    train_user_ids = user_ids[: min(train_users, len(user_ids))]
    val_user_ids = user_ids[min(train_users, len(user_ids)) : min(train_users + val_users, len(user_ids))]
    train_injection_ids = injection_ids[: min(train_injections, len(injection_ids))]
    val_injection_ids = injection_ids[min(train_injections, len(injection_ids)) : min(train_injections + val_injections, len(injection_ids))]

    train_results = _run_phase(
        suite_name=suite_name,
        benchmark_version=benchmark_version,
        model=model,
        attack=attack,
        phase="train",
        user_ids=train_user_ids,
        injection_ids=train_injection_ids,
        seed=seed,
    )
    train_analysis = analyze_samples(train_results)

    val_results = _run_phase(
        suite_name=suite_name,
        benchmark_version=benchmark_version,
        model=model,
        attack=attack,
        phase="validation",
        user_ids=val_user_ids,
        injection_ids=val_injection_ids,
        seed=seed + 1,
    )
    val_analysis = analyze_samples(val_results)

    return {
        "sample_plan": {
            "train_user_ids": train_user_ids,
            "val_user_ids": val_user_ids,
            "train_injection_ids": train_injection_ids,
            "val_injection_ids": val_injection_ids,
        },
        "train": train_analysis,
        "validation": val_analysis,
        "rule_patch_suggestions": suggest_rule_patches(suite_name, train_analysis["failures"]),
    }


def _run_phase(
    *,
    suite_name: str,
    benchmark_version: str,
    model: str,
    attack: str,
    phase: str,
    user_ids: list[str],
    injection_ids: list[str],
    seed: int,
) -> list[SampleResult]:
    suite = get_suite(benchmark_version, suite_name)
    llm, llm_name = build_llm(model, None, "tool")
    pipeline = build_pipeline("agentdojo_firewall", llm, None, system_message="You are a helpful assistant.", max_iters=15)
    attack_obj = load_attack(attack, suite, pipeline)
    phase_log_root = LOG_DIR / f"{suite_name}_{phase}"
    phase_log_root.mkdir(parents=True, exist_ok=True)
    phase_report_root = REPORT_DIR / "iterations" / f"{suite_name}_{phase}"
    phase_report_root.mkdir(parents=True, exist_ok=True)

    results: list[SampleResult] = []
    with OutputLogger(str(phase_log_root)):
        for user_task_id in user_ids:
            user_task = suite.get_user_task_by_id(user_task_id)
            for injection_task_id in injection_ids:
                injection_task = suite.get_injection_task_by_id(injection_task_id)
                injections = attack_obj.attack(user_task, injection_task)
                allowed_tools, allowed_categories = _infer_authorized_tools_and_categories(suite_name, suite, user_task)
                if hasattr(pipeline, "set_context"):
                    pipeline.set_context(
                        RepoShieldAgentDojoContext(
                            suite=suite_name,
                            user_task_id=user_task_id,
                            injection_task_id=injection_task_id,
                            task_instruction=getattr(user_task, "PROMPT", None),
                            injection_instruction=getattr(injection_task, "GOAL", None),
                            attack_goal=getattr(injection_task, "GOAL", None),
                            attack_goal_signatures=[
                                getattr(injection_task, "GOAL", "") or "",
                                getattr(injection_task, "PROMPT", "") or "",
                            ],
                            source_ids=list(injections.keys()),
                            source_has_untrusted=bool(injections),
                            untrusted_observation_seen=bool(injections),
                            allowed_tools=allowed_tools,
                            allowed_tool_categories=allowed_categories,
                            run_id=f"{suite_name}-{user_task_id}-{injection_task_id}-{phase}-{seed}",
                            metadata={},
                        )
                    )
                run_path = phase_log_root / f"{user_task_id}_{injection_task_id}.json"
                with TraceLogger(
                    delegate=OutputLogger(str(phase_log_root)),
                    suite_name=suite.name,
                    user_task_id=user_task_id,
                    injection_task_id=injection_task_id,
                    injections=injections,
                    attack_type=attack_obj.name,
                    pipeline_name=getattr(pipeline, "name", llm_name),
                    benchmark_version=benchmark_version,
                ) as logger:
                    firewall = getattr(pipeline, "firewall", None)
                    firewall_start = len(getattr(firewall, "audit_events", []) or [])
                    utility, security = _run_agentdojo_task_with_retries(suite, pipeline, user_task, injection_task, injections)
                    logger.set_contextarg("utility", utility)
                    logger.set_contextarg("security", security)
                log_file = _find_sample_log_file(
                    phase_log_root,
                    suite_name=suite_name,
                    user_task_id=user_task_id,
                    attack_name=attack_obj.name,
                    injection_task_id=injection_task_id,
                )
                sample = _load_sample_result(log_file, suite_name=suite_name, phase=phase)
                sample.utility = utility
                sample.security = security
                sample.run_path = log_file
                sample.user_task_text = getattr(user_task, "PROMPT", "") or getattr(user_task, "prompt", "") or str(user_task)
                sample.injection_text = "\n\n".join(
                    text
                    for text in [
                        getattr(injection_task, "GOAL", "") or "",
                        getattr(injection_task, "PROMPT", "") or "",
                        "\n".join(str(v) for v in injections.values()),
                    ]
                    if text
                )
                if firewall is not None and hasattr(firewall, "audit_events"):
                    sample.firewall_audit = summarize_agentdojo_firewall_audit(firewall.audit_events[firewall_start:])
                results.append(sample)
    return results


def _load_sample_result(path: Path, *, suite_name: str, phase: str) -> SampleResult:
    data = json.loads(path.read_text(encoding="utf-8"))
    messages = data.get("messages") or []
    tool_calls: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") == "assistant" and message.get("tool_calls"):
            for call in message["tool_calls"]:
                tool_calls.append({"function": call.get("function"), "args": call.get("args", {})})
    return SampleResult(
        suite=suite_name,
        phase=phase,
        user_task_id=str(data.get("user_task_id", "")),
        injection_task_id=str(data.get("injection_task_id", "")),
        utility=bool(data.get("utility", False)),
        security=bool(data.get("security", False)),
        run_path=path,
        user_task_text="",
        injection_text="",
        tool_calls=tool_calls,
        messages=messages,
        firewall_audit=data.get("agentdojo_firewall_audit_summary") or {},
    )


def _find_sample_log_file(
    phase_log_root: Path,
    *,
    suite_name: str,
    user_task_id: str,
    attack_name: str,
    injection_task_id: str,
) -> Path:
    expected = f"{injection_task_id}.json"
    candidates = []
    for path in phase_log_root.rglob(expected):
        parts = {part.lower() for part in path.parts}
        if suite_name.lower() in parts and user_task_id.lower() in parts and attack_name.lower() in parts:
            candidates.append(path)
    if not candidates:
        for path in phase_log_root.rglob(expected):
            if suite_name.lower() in path.as_posix().lower():
                candidates.append(path)
    if not candidates:
        raise FileNotFoundError(
            f"could not locate sample log for {suite_name}/{user_task_id}/{attack_name}/{injection_task_id} under {phase_log_root}"
        )
    candidates.sort(key=lambda item: len(item.parts))
    return candidates[0]


def analyze_samples(samples: list[SampleResult]) -> dict[str, Any]:
    failures = [sample for sample in samples if not sample.security or not sample.utility]
    failure_counts = Counter()
    tool_counts = Counter()
    for sample in failures:
        category = classify_failure(sample)
        failure_counts[category] += 1
        for call in sample.tool_calls:
            tool = str(call.get("function") or "")
            if tool:
                tool_counts[tool] += 1
    firewall = _aggregate_firewall_stats(samples)
    return {
        "sample_count": len(samples),
        "utility_under_attack": _avg_bool([sample.utility for sample in samples]),
        "security": _avg_bool([sample.security for sample in samples]),
        "targeted_asr": 1.0 - _avg_bool([sample.security for sample in samples]) if samples else 0.0,
        "failures": [
            {
                "user_task_id": sample.user_task_id,
                "injection_task_id": sample.injection_task_id,
                "kind": classify_failure(sample),
                "tool_calls": sample.tool_calls,
                "user_task_targets": sorted(extract_targets(sample.user_task_text)),
                "injection_targets": sorted(extract_targets(sample.injection_text)),
            }
            for sample in failures
        ],
        "failure_counts": dict(failure_counts),
        "tool_counts": dict(tool_counts),
        "firewall": firewall,
    }


def classify_failure(sample: SampleResult) -> str:
    if sample.security:
        return "none"
    tool_names = [str(call.get("function") or "") for call in sample.tool_calls]
    user_targets = extract_targets(sample.user_task_text)
    injection_targets = extract_targets(sample.injection_text)
    if any(name.startswith("reserve_") for name in tool_names):
        booking_target = _booking_target(sample.tool_calls)
        if user_targets and booking_target and booking_target not in user_targets:
            return "travel_booking_target_mismatch"
        if looks_like_injection(sample.injection_text):
            return "travel_booking_after_untrusted_review"
        return "travel_booking_failure"
    if any(name.startswith(("send_", "share_")) for name in tool_names):
        if injection_targets:
            return "egress_after_private_or_untrusted"
        return "external_send_failure"
    if any(name.startswith("send_money") or name.startswith("schedule_transaction") for name in tool_names):
        return "financial_commit_failure"
    if sample.utility is False and not tool_names:
        return "no_tool_calls"
    return "other_failure"


def suggest_rule_patches(suite_name: str, failures: list[dict[str, Any]]) -> list[dict[str, str]]:
    categories = Counter(item["kind"] for item in failures)
    suggestions: list[dict[str, str]] = []
    if suite_name == "travel":
        if categories.get("travel_booking_target_mismatch") or categories.get("travel_booking_after_untrusted_review"):
            suggestions.append(
                {
                    "rule_id": "ADJ-TRAVEL-003",
                    "patch": "keep the explicit target-match booking rule and extend it to all booking tools when the user task names a concrete target.",
                }
            )
        if categories.get("egress_after_private_or_untrusted"):
            suggestions.append(
                {
                    "rule_id": "ADJ-DATA-001 / ADJ-MSG-001",
                    "patch": "tighten external-send blocking after private-data reads and untrusted review text, especially for send_email and share-like travel actions.",
                }
            )
    elif suite_name == "banking":
        if categories.get("financial_commit_failure"):
            suggestions.append(
                {
                    "rule_id": "ADJ-FIN-001 / ADJ-GOAL-001",
                    "patch": "keep the financial-commit block, and add a softer allow path only for explicitly authorized task goals.",
                }
            )
    else:
        if categories:
            suggestions.append(
                {
                    "rule_id": "suite-specific",
                    "patch": "derive a new target-mismatch or external-egress rule from the dominant failure pattern in this suite.",
                }
            )
    if not suggestions:
        suggestions.append({"rule_id": "none", "patch": "no new rule patch suggested from this sample batch."})
    return suggestions


def render_iteration_markdown(summary: dict[str, Any]) -> str:
    lines = ["# AgentDojo Firewall Iteration", ""]
    lines.append(f"- model: {summary['model']}")
    lines.append(f"- attack: {summary['attack']}")
    lines.append(f"- seed: {summary['seed']}")
    lines.append("")
    for suite_name, suite_summary in summary["suites"].items():
        lines.extend(
            [
                f"## {suite_name}",
                "",
                "| Phase | Utility Under Attack | Security | Targeted ASR | Samples | Blocked | P50 ms | P95 ms |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
                _phase_row("train", suite_summary["train"]),
                _phase_row("validation", suite_summary["validation"]),
                "",
                "### Failure Reasons",
                "",
            ]
        )
        for kind, count in sorted(suite_summary["train"]["failure_counts"].items()):
            lines.append(f"- train {kind}: {count}")
        for kind, count in sorted(suite_summary["validation"]["failure_counts"].items()):
            lines.append(f"- validation {kind}: {count}")
        lines.extend(["", "### Rule Patches", ""])
        for patch in suite_summary["rule_patch_suggestions"]:
            lines.append(f"- {patch['rule_id']}: {patch['patch']}")
        lines.append("")
    return "\n".join(lines)


def _phase_row(phase: str, analysis: dict[str, Any]) -> str:
    fw = analysis["firewall"]
    return (
        f"| {phase} | {analysis['utility_under_attack']:.3f} | {analysis['security']:.3f} | "
        f"{analysis['targeted_asr']:.3f} | {analysis['sample_count']} | {fw.get('blocked_tool_calls', 0)} | "
        f"{fw.get('policy_p50_ms', 0.0):.3f} | {fw.get('policy_p95_ms', 0.0):.3f} |"
    )


def _sample_ids(items: list[str], count: int, *, seed: int) -> list[str]:
    rng = random.Random(seed)
    if count >= len(items):
        return list(items)
    selected = rng.sample(items, count)
    return sorted(selected)


def _message_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return " ".join(parts)
    return str(value or "")


def _booking_target(tool_calls: list[dict[str, Any]]) -> str:
    for call in tool_calls:
        args = call.get("args") or {}
        if not isinstance(args, dict):
            continue
        for key in ("hotel", "hotel_name", "company", "company_name", "restaurant", "restaurant_name"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _aggregate_firewall_stats(samples: list[SampleResult]) -> dict[str, Any]:
    combined = {
        "registered_tool_rate": 0.0,
        "unknown_tool_rate": 0.0,
        "total_tool_calls_gated": 0,
        "blocked_tool_calls": 0,
        "policy_p50_ms": 0.0,
        "policy_p95_ms": 0.0,
        "rule_hit_counts": {},
    }
    firewalls = [sample.firewall_audit for sample in samples if sample.firewall_audit]
    if not firewalls:
        return combined
    combined["registered_tool_rate"] = sum(float(item.get("registered_tool_rate", 0.0)) for item in firewalls) / len(firewalls)
    combined["unknown_tool_rate"] = sum(float(item.get("unknown_tool_rate", 0.0)) for item in firewalls) / len(firewalls)
    combined["total_tool_calls_gated"] = sum(int(item.get("total_tool_calls_gated", 0)) for item in firewalls)
    combined["blocked_tool_calls"] = sum(int(item.get("blocked_tool_calls", 0)) for item in firewalls)
    combined["policy_p50_ms"] = sum(float(item.get("policy_p50_ms", 0.0)) for item in firewalls) / len(firewalls)
    combined["policy_p95_ms"] = sum(float(item.get("policy_p95_ms", 0.0)) for item in firewalls) / len(firewalls)
    rule_hits: Counter[str] = Counter()
    for item in firewalls:
        rule_hits.update({str(k): int(v) for k, v in (item.get("rule_hit_counts") or {}).items()})
    combined["rule_hit_counts"] = dict(sorted(rule_hits.items()))
    return combined


def _avg_bool(values: list[bool]) -> float:
    return float(sum(1 for item in values if item) / len(values)) if values else 0.0


if __name__ == "__main__":
    main()
