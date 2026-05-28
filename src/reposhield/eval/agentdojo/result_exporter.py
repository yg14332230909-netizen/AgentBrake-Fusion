"""Summarize RepoShield audit events for AgentDojo experiment reports."""

from __future__ import annotations

from collections import Counter
from typing import Any


def summarize_agentdojo_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [
        event.get("payload", {})
        for event in events
        if event.get("event_type") in {"policy_decision", "agentdojo_tool_gate_decision"}
    ]
    tool_events = [event.get("payload", {}) for event in events if event.get("event_type") == "agentdojo_tool_gate_decision"]
    fact_events = [event.get("payload", {}) for event in events if event.get("event_type") == "policy_fact_set"]
    unknown = [
        payload
        for payload in fact_events
        if "agentdojo" in (payload.get("namespace_counts") or {}) and "unknown" in str(payload.get("summary", "")).lower()
    ]
    reason_counts = Counter(reason for decision in decisions for reason in decision.get("reason_codes", []) or [])
    latencies = [
        value
        for event in events
        if event.get("event_type") == "performance_trace"
        for value in [((event.get("payload") or {}).get("timings_ms") or {}).get("policy.total_ms")]
        if isinstance(value, (int, float))
    ]
    return {
        "reposhield_checked_calls": len(tool_events) or len(decisions),
        "reposhield_policy_decisions": dict(Counter(str(item.get("decision")) for item in decisions)),
        "reposhield_blocks": sum(1 for item in decisions if item.get("decision") in {"block", "quarantine"}),
        "reposhield_unknown_tools": len(unknown),
        "reposhield_unregistered_tool_rate": (len(unknown) / max(len(tool_events), 1)) if tool_events else 0.0,
        "reposhield_top_reason_codes": reason_counts.most_common(10),
        "reposhield_avg_policy_latency_ms": (sum(latencies) / len(latencies)) if latencies else 0.0,
        "reposhield_p95_policy_latency_ms": _p95(latencies),
    }


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))])
