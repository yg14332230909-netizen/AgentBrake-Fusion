from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DANGEROUS_SINK_KEYWORDS = (
    "send",
    "transfer",
    "pay",
    "schedule_transaction",
    "reserve",
    "book",
    "invite",
    "add_user",
    "remove_user",
    "delete",
    "update",
    "create",
    "share",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract AgentDojo-derived replay cases only from full execution traces")
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--manifest-out", type=Path, required=True)
    parser.add_argument("--review-queue-out", type=Path, required=True)
    parser.add_argument("--trace-collection-manifest-out", type=Path, required=True)
    parser.add_argument("--source-method", default="no_defense")
    parser.add_argument("--model", default=None)
    parser.add_argument("--attack", default=None)
    args = parser.parse_args()

    result = extract_replay_cases(
        reports_dir=args.reports_dir,
        out_dir=args.out_dir,
        source_method=args.source_method,
        model=args.model,
        attack=args.attack,
    )
    write_json(args.manifest_out, result["manifest"])
    write_jsonl(args.review_queue_out, result["review_queue"])
    write_json(args.trace_collection_manifest_out, result["trace_collection_manifest"])
    report_path = args.out_dir.parent / "extraction_report.md"
    report_path.write_text(render_report(result), encoding="utf-8")
    gap_report_path = args.out_dir.parent / "sample_gap_report.md"
    gap_report_path.write_text(render_sample_gap_report(result), encoding="utf-8")
    print(args.manifest_out)
    return 0


def extract_replay_cases(
    *,
    reports_dir: Path,
    out_dir: Path,
    source_method: str,
    model: str | None = None,
    attack: str | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "safe").mkdir(parents=True, exist_ok=True)
    (out_dir / "unsafe").mkdir(parents=True, exist_ok=True)

    cases: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    trace_missing: list[dict[str, Any]] = []
    considered = 0
    generated = 0

    for summary_path, summary in iter_summaries(reports_dir):
        if model and str(summary.get("model")) != model:
            continue
        if attack and str(summary.get("attack")) != attack:
            continue
        if not method_matches(summary.get("defense"), source_method):
            continue
        for row in summary.get("per_run") or summary.get("normalized_cases") or []:
            if not isinstance(row, dict):
                continue
            considered += 1
            trace_path = resolve_trace_path(row.get("trace_file"), summary_path)
            trace = load_trace(trace_path)
            if not is_full_agentdojo_trace(trace):
                missing = missing_trace_record(summary_path, row, source_method, model, attack, trace_path)
                trace_missing.append(missing)
                continue
            replay_case = build_replay_case(trace, row, summary_path)
            if replay_case is None:
                review_queue.append(review_record(summary_path, row, trace_path, "no_replayable_sink_found"))
                continue
            bucket = "unsafe" if replay_case["expected_decision"] == "block" else "safe"
            case_path = out_dir / bucket / f"{replay_case['case_id']}.json"
            write_json(case_path, replay_case)
            replay_case["path"] = str(case_path)
            cases.append(replay_case)
            review_queue.append(review_record(summary_path, row, trace_path, "generated", case_id=replay_case["case_id"]))
            generated += 1

    manifest = {
        "manifest_schema_version": "agentdojo_replay_manifest_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "agentdojo_full_trace",
        "source_method": source_method,
        "model": model,
        "attack": attack,
        "case_count": len(cases),
        "safe_case_count": sum(1 for case in cases if case["expected_decision"] == "allow"),
        "unsafe_case_count": sum(1 for case in cases if case["expected_decision"] == "block"),
        "trace_missing_count": len(trace_missing),
        "cases": [{"case_id": case["case_id"], "path": case["path"], "expected_decision": case["expected_decision"]} for case in cases],
    }
    return {
        "manifest": manifest,
        "review_queue": review_queue,
        "trace_collection_manifest": {
            "manifest_schema_version": "agentdojo_trace_collection_v1",
            "generated_at": manifest["generated_at"],
            "reports_dir": str(reports_dir),
            "candidate_case_count": considered,
            "trace_missing_count": len(trace_missing),
            "missing_traces": trace_missing,
        },
        "generated_case_count": generated,
        "considered_case_count": considered,
    }


def iter_summaries(reports_dir: Path) -> Any:
    for path in sorted(reports_dir.rglob("*.json")):
        if "normalized" in path.parts:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and (data.get("per_run") or data.get("normalized_cases")):
            yield path, data


def method_matches(defense: Any, source_method: str) -> bool:
    aliases = {
        "no_defense": {"none", "no_defense", "", None},
        "none": {"none", "no_defense", "", None},
        "reposhield_tool_firewall": {"agentdojo_firewall", "reposhield_tool_firewall"},
        "agentdojo_firewall": {"agentdojo_firewall", "reposhield_tool_firewall"},
    }
    return defense in aliases.get(source_method, {source_method})


def resolve_trace_path(raw: Any, summary_path: Path) -> Path | None:
    if not raw:
        return None
    path = Path(str(raw))
    if path.is_absolute():
        return path
    candidate = summary_path.parent / path
    return candidate if candidate.exists() else path


def load_trace(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def is_full_agentdojo_trace(trace: dict[str, Any] | None) -> bool:
    return bool(
        isinstance(trace, dict)
        and isinstance(trace.get("messages"), list)
        and isinstance(trace.get("tool_calls"), list)
        and isinstance(trace.get("tool_results"), list)
    )


def build_replay_case(trace: dict[str, Any], row: dict[str, Any], summary_path: Path) -> dict[str, Any] | None:
    tool_call = first_replayable_tool_call(trace.get("tool_calls") or [])
    if tool_call is None:
        return None
    injection_success = bool(row.get("raw_agentdojo_injection_task_success", row.get("security", trace.get("raw_agentdojo_injection_task_success", False))))
    user_success = bool(row.get("raw_agentdojo_user_task_success", row.get("utility", trace.get("raw_agentdojo_user_task_success", False))))
    expected = "block" if injection_success else "allow"
    case_id = "_".join(
        clean_part(part)
        for part in [
            trace.get("suite") or row.get("suite") or "suite",
            row.get("user_task_id") or trace.get("user_task_id") or "user",
            row.get("injection_task_id") or trace.get("injection_task_id") or "none",
            tool_call.get("tool") or "tool",
            expected,
        ]
    )
    return {
        "case_schema_version": "agentdojo_replay_case_v1",
        "case_id": case_id,
        "source_raw_file": str(summary_path),
        "source_trace_file": str(resolve_trace_path(row.get("trace_file"), summary_path) or ""),
        "suite": trace.get("suite") or row.get("suite"),
        "method": trace.get("method") or row.get("method"),
        "model": trace.get("model"),
        "attack": trace.get("attack"),
        "user_task_id": row.get("user_task_id") or trace.get("user_task_id"),
        "injection_task_id": row.get("injection_task_id") or trace.get("injection_task_id"),
        "expected_decision": expected,
        "expected_agentdojo_user_success": user_success,
        "expected_agentdojo_injection_success": injection_success,
        "tool_call": tool_call,
        "prior_messages": messages_before(trace.get("messages") or [], int(tool_call.get("step") or 0)),
        "prior_tool_results": results_before(trace.get("tool_results") or [], int(tool_call.get("step") or 0)),
    }


def first_replayable_tool_call(tool_calls: list[Any]) -> dict[str, Any] | None:
    normalized = [call for call in tool_calls if isinstance(call, dict)]
    for call in normalized:
        if is_dangerous_sink(str(call.get("tool") or "")):
            return call
    return normalized[0] if normalized else None


def is_dangerous_sink(tool_name: str) -> bool:
    lowered = tool_name.lower()
    return any(keyword in lowered for keyword in DANGEROUS_SINK_KEYWORDS)


def messages_before(messages: list[Any], step: int) -> list[Any]:
    return [message for index, message in enumerate(messages) if index < step]


def results_before(results: list[Any], step: int) -> list[Any]:
    return [result for result in results if isinstance(result, dict) and int(result.get("step") or 0) < step]


def missing_trace_record(
    summary_path: Path,
    row: dict[str, Any],
    source_method: str,
    model: str | None,
    attack: str | None,
    trace_path: Path | None,
) -> dict[str, Any]:
    return {
        "source_raw_file": str(summary_path),
        "source_method": source_method,
        "model": model,
        "attack": attack,
        "suite": row.get("suite"),
        "user_task_id": row.get("user_task_id"),
        "injection_task_id": row.get("injection_task_id"),
        "trace_file": str(trace_path) if trace_path else None,
        "reason": "missing_full_agentdojo_trace",
        "required_fields": ["messages", "tool_calls", "tool_results"],
    }


def review_record(
    summary_path: Path,
    row: dict[str, Any],
    trace_path: Path | None,
    status: str,
    *,
    case_id: str | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "source_raw_file": str(summary_path),
        "trace_file": str(trace_path) if trace_path else None,
        "suite": row.get("suite"),
        "user_task_id": row.get("user_task_id"),
        "injection_task_id": row.get("injection_task_id"),
        "review_status": status,
    }


def render_report(result: dict[str, Any]) -> str:
    manifest = result["manifest"]
    trace_manifest = result["trace_collection_manifest"]
    lines = [
        "# AgentDojo Replay Case Extraction",
        "",
        f"- Candidate cases considered: {trace_manifest['candidate_case_count']}",
        f"- Replay cases generated from full traces: {manifest['case_count']}",
        f"- Missing full traces: {manifest['trace_missing_count']}",
        "",
        "Replay cases are generated only from traces containing `messages`, `tool_calls`, and `tool_results`.",
    ]
    if manifest["trace_missing_count"]:
        lines.extend(["", "No synthetic cases were created for missing traces. See `trace_collection_manifest.json`."])
    return "\n".join(lines) + "\n"


def render_sample_gap_report(result: dict[str, Any]) -> str:
    manifest = result["manifest"]
    trace_manifest = result["trace_collection_manifest"]
    if manifest["trace_missing_count"] == 0:
        status = "No sample gap detected."
    else:
        status = "Formal replay expansion is blocked until full AgentDojo traces are collected."
    return "\n".join(
        [
            "# AgentDojo Replay Sample Gap Report",
            "",
            status,
            "",
            f"- Candidate cases considered: {trace_manifest['candidate_case_count']}",
            f"- Cases generated from real traces: {manifest['case_count']}",
            f"- Cases missing full traces: {manifest['trace_missing_count']}",
            "",
            "Summary-only or normalized rows are intentionally not converted into replay cases.",
        ]
    ) + "\n"


def clean_part(value: Any) -> str:
    text = str(value).strip().replace(" ", "_")
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in text) or "unknown"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
