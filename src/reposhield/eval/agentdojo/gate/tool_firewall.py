from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .blocked_result import BlockedActionTracker, build_blocked_tool_result
from ..evidence.action_graph import AgentDojoActionGraphBuilder
from ..evidence.evidence import AgentDojoEvidenceBuilder
from ..evidence.fusion import AgentDojoEvidenceFusion, FusionResult
from ..evidence.state import AgentDojoStateTracker
from ..evidence.taxonomy import AgentDojoToolTaxonomy, infer_unknown_tool
from ..compat.types import SanitizeMode, ToolCallContext


@dataclass(slots=True)
class ToolExecutionDecision:
    execute: bool
    decision: str
    reason_codes: list[str]
    safe_result: Any | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    action_graph_id: str | None = None
    action_graph_facts: dict[str, Any] = field(default_factory=dict)
    fusion_result: FusionResult | None = None
    repeated_unsafe_action: bool = False

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "event_type": "agentdojo_tool_gate_decision",
            "execute": self.execute,
            "decision": self.decision,
            "reason_codes": self.reason_codes,
            "action_graph_id": self.action_graph_id,
            "action_graph_facts": self.action_graph_facts,
            "evidence": self.evidence,
            "rule_hits": [asdict(hit) for hit in self.fusion_result.rule_hits] if self.fusion_result else [],
            "repeated_unsafe_action": self.repeated_unsafe_action,
            "modules_executed": self.evidence.get("modules_executed", []),
            "modules_skipped": self.evidence.get("modules_skipped", []),
            "ablation_config": self.evidence.get("ablation_config", {}),
            "matched_rules": list(self.reason_codes),
            "matched_invariants": self.evidence.get("matched_invariants", []),
        }


class AgentDojoToolFirewall:
    """Tool firewall for AgentDojo benchmark runs."""

    def __init__(
        self,
        *,
        taxonomy: AgentDojoToolTaxonomy | None = None,
        state: AgentDojoStateTracker | None = None,
        graph_builder: AgentDojoActionGraphBuilder | None = None,
        evidence_builder: AgentDojoEvidenceBuilder | None = None,
        fusion: AgentDojoEvidenceFusion | None = None,
        sanitize_outputs: bool = True,
        sanitize_mode: SanitizeMode = "soft",
        eval_mode: bool = True,
        enable_taxonomy: bool = True,
        enable_state_tracker: bool = True,
        enable_action_graph: bool = True,
        enable_task_contract: bool = True,
        enable_invariants: bool = True,
        enable_recovery_guidance: bool = True,
    ) -> None:
        self.taxonomy = taxonomy or AgentDojoToolTaxonomy()
        self.state = state or AgentDojoStateTracker()
        self.state.sanitize_mode = sanitize_mode
        self.graph_builder = graph_builder or AgentDojoActionGraphBuilder()
        self.evidence_builder = evidence_builder or AgentDojoEvidenceBuilder()
        self.fusion = fusion or AgentDojoEvidenceFusion(eval_mode=eval_mode)
        self.sanitize_outputs = sanitize_outputs
        self.sanitize_mode = sanitize_mode
        self.eval_mode = eval_mode
        self.audit_events: list[dict[str, Any]] = []
        self.ablation_config = {
            "enable_taxonomy": enable_taxonomy,
            "enable_state_tracker": enable_state_tracker,
            "enable_action_graph": enable_action_graph,
            "enable_task_contract": enable_task_contract,
            "enable_invariants": enable_invariants,
            "enable_recovery_guidance": enable_recovery_guidance,
        }
        self._blocked_tracker = BlockedActionTracker()

    def guard_before_tool(self, context: ToolCallContext) -> ToolExecutionDecision:
        started = time.perf_counter()
        modules_executed: list[str] = []
        modules_skipped: list[str] = []
        ablation_config = {**self.ablation_config, **context.ablation_config}

        def module_enabled(name: str) -> bool:
            key = f"enable_{name}"
            return bool(ablation_config.get(key, True))

        if module_enabled("taxonomy"):
            modules_executed.append("taxonomy")
            spec = self.taxonomy.classify(context.tool_name, suite=context.suite)
        else:
            modules_skipped.append("taxonomy")
            spec = infer_unknown_tool(context.tool_name)
        if context.defense_mode == "oracle_full":
            for signature in context.attack_goal_signatures:
                self.state.add_attack_goal_signature(signature)
        if module_enabled("state_tracker"):
            modules_executed.append("state_tracker")
            self.state.observe_tool_call(context.tool_name, spec, context.tool_args)
        else:
            modules_skipped.append("state_tracker")
        initial = self.evidence_builder.build(context=context, spec=spec, state=self.state)
        if module_enabled("action_graph"):
            modules_executed.append("action_graph")
            graph_result = self.graph_builder.build(context=context, spec=spec, state=self.state, evidence=initial)
            graph_facts = graph_result.facts
            action_graph_id = graph_result.graph.graph_id
        else:
            modules_skipped.append("action_graph")
            graph_facts = {}
            action_graph_id = None
        evidence = self.evidence_builder.build(context=context, spec=spec, state=self.state, graph_facts=graph_facts)
        evidence.action_graph_id = action_graph_id
        for name in ("task_contract", "invariants"):
            if module_enabled(name):
                modules_executed.append(name)
            else:
                modules_skipped.append(name)
        evidence.facts["ablation_config"] = ablation_config
        evidence.facts["modules_executed"] = modules_executed
        evidence.facts["modules_skipped"] = modules_skipped
        evidence.facts["matched_invariants"] = [] if not module_enabled("invariants") else evidence.facts.get("matched_invariants", [])
        fusion = self.fusion.decide(evidence)
        execute = fusion.decision in {"allow", "allow_in_sandbox"}
        repeated = False
        safe = None
        if not execute:
            safe = build_blocked_tool_result(
                context,
                fusion,
                recovery_guidance_enabled=bool(ablation_config.get("enable_recovery_guidance", True)),
            )
            retry_count = self._blocked_tracker.record(str(safe["same_action_retry_key"]))
            repeated = retry_count > 1
            if repeated:
                safe = build_blocked_tool_result(
                    context,
                    fusion,
                    repeated_unsafe_action=True,
                    recovery_guidance_enabled=bool(ablation_config.get("enable_recovery_guidance", True)),
                )
        decision = ToolExecutionDecision(
            execute=execute,
            decision=fusion.decision,
            reason_codes=fusion.reason_codes,
            safe_result=safe,
            evidence=evidence.facts,
            action_graph_id=action_graph_id,
            action_graph_facts=graph_facts,
            fusion_result=fusion,
            repeated_unsafe_action=repeated,
        )
        event = decision.to_audit_event()
        event["policy_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        self.audit_events.append(event)
        return decision

    def observe_after_tool(self, context: ToolCallContext, raw_result: Any) -> Any:
        started = time.perf_counter()
        spec = self.taxonomy.classify(context.tool_name, suite=context.suite)
        event = self.state.observe_tool_result(context.tool_name, spec, raw_result)
        sanitized = self.state.sanitize_tool_output(raw_result, mode=self.sanitize_mode) if self.sanitize_outputs else raw_result
        self.audit_events.append(
            {
                "event_type": "agentdojo_tool_result_observed",
                "suite": context.suite,
                "tool_name": context.tool_name,
                "tool_group": spec.group,
                "result_event": asdict(event),
                "state": self.state.as_dict(),
                "sanitized": sanitized != raw_result,
                "observe_ms": round((time.perf_counter() - started) * 1000.0, 3),
            }
        )
        return sanitized

    def run_guarded_tool(self, context: ToolCallContext, original_tool: Callable[..., Any]) -> tuple[Any, ToolExecutionDecision]:
        decision = self.guard_before_tool(context)
        if not decision.execute:
            return decision.safe_result, decision
        raw = original_tool(**context.tool_args)
        return self.observe_after_tool(context, raw), decision


def summarize_agentdojo_firewall_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    decision_events = [event for event in events if event.get("event_type") == "agentdojo_tool_gate_decision"]
    result_events = [event for event in events if event.get("event_type") == "agentdojo_tool_result_observed"]
    policy_latencies = [float(event.get("policy_ms", 0.0)) for event in decision_events if isinstance(event.get("policy_ms"), (int, float))]
    registered = 0
    unknown = 0
    blocked = 0
    repeated_blocked = 0
    rule_hits: dict[str, int] = {}
    for event in decision_events:
        evidence = event.get("evidence") or {}
        if evidence.get("agentdojo.unknown_tool"):
            unknown += 1
        else:
            registered += 1
        if not event.get("execute", True):
            blocked += 1
        if event.get("repeated_unsafe_action"):
            repeated_blocked += 1
        for hit in event.get("rule_hits") or []:
            rule_id = str(hit.get("rule_id", ""))
            if rule_id:
                rule_hits[rule_id] = rule_hits.get(rule_id, 0) + 1
    total = len(decision_events)
    return {
        "registered_tool_rate": 0.0 if total == 0 else registered / total,
        "unknown_tool_rate": 0.0 if total == 0 else unknown / total,
        "total_tool_calls_gated": total,
        "tool_gate_decision_count": total,
        "blocked_tool_calls": blocked,
        "repeated_block_count": repeated_blocked,
        "safe_blocked_result": blocked,
        "allow": total - blocked,
        "block": blocked,
        "policy_p50_ms": _percentile(policy_latencies, 0.5),
        "policy_p95_ms": _percentile(policy_latencies, 0.95),
        "rule_hit_counts": dict(sorted(rule_hits.items())),
        "result_events": len(result_events),
    }


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round((len(ordered) - 1) * pct)))
    return float(ordered[idx])


