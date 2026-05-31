from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..compat.types import ConstraintDecision, Decision, EvidenceBundle


@dataclass(slots=True)
class RuleHit:
    rule_id: str
    decision: Decision
    constraints: ConstraintDecision
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FusionResult:
    decision: Decision
    constraints: ConstraintDecision
    reason_codes: list[str]
    rule_hits: list[RuleHit]
    facts: dict[str, Any]


class AgentDojoEvidenceFusion:
    """Deterministic AgentDojo multi-source fusion.

    The rules intentionally avoid bluntly blocking all tools after any untrusted
    observation.  Read tools remain available; risky side effects are blocked
    only when multiple evidence sources indicate attack influence or exfil risk.
    """

    def __init__(self, *, eval_mode: bool = True) -> None:
        self.eval_mode = eval_mode

    def decide(self, evidence: EvidenceBundle) -> FusionResult:
        hits = self._evaluate_rules(evidence)
        constraints = ConstraintDecision()
        for hit in hits:
            constraints = constraints.join(hit.constraints)
        decision = constraints.to_public_decision(eval_mode=self.eval_mode)
        reasons = [hit.rule_id for hit in hits] or ["ADJ-ALLOW-READONLY" if not evidence.side_effect else "ADJ-ALLOW-AUTHORIZED"]
        return FusionResult(decision=decision, constraints=constraints, reason_codes=reasons, rule_hits=hits, facts=evidence.facts)

    def _evaluate_rules(self, e: EvidenceBundle) -> list[RuleHit]:
        hits: list[RuleHit] = []
        if not e.side_effect:
            return hits
        if e.unknown_tool:
            hits.append(self._block("ADJ-UNKNOWN-001", "unknown side-effecting tool", e))
        if e.attack_goal_overlap:
            hits.append(self._block("ADJ-GOAL-001", "tool arguments overlap suspicious target extracted from prior output", e))
        if e.group == "financial_commit" and e.untrusted_seen and not e.task_authorized:
            hits.append(self._block("ADJ-FIN-001", "untrusted context attempted unauthorized financial commit", e))
        if (
            e.group == "financial_commit"
            and e.facts.get("agentdojo.target_entity_source") == "unknown"
            and e.facts.get("agentdojo.sensitive_args_present")
        ):
            hits.append(self._confirm("ADJ-BANKING-CONFIRM-UNKNOWN-RECIPIENT", "unknown payment recipient requires user confirmation", e))
        if (
            e.group == "financial_commit"
            and (e.args_match_untrusted_entity or (e.sensitive_args_not_in_user_task and e.untrusted_seen))
            and not e.task_authorized
        ):
            hits.append(self._block("ADJ-BANKING-UNTRUSTED-FINANCIAL-COMMIT", "financial commit arguments were not authorized by user task entities", e))
        if (
            e.external_sink
            and e.private_data_seen
            and (e.injection_seen or e.attack_goal_overlap)
            and not e.task_authorized
            and not e.args_match_user_entity
        ):
            hits.append(self._block("ADJ-DATA-001", "private data observed before risky external sink", e))
        if (
            e.external_sink
            and e.sensitive_args_present
            and (e.args_match_private_entity or e.args_match_untrusted_entity)
            and not e.args_match_user_entity
        ):
            hits.append(self._block("ADJ-DATA-002", "external sink arguments appear sourced from private or untrusted observations", e))
        if e.group == "external_send" and e.untrusted_seen and not e.args_match_user_entity and not e.task_authorized:
            hits.append(self._block("ADJ-MSG-001", "untrusted context attempted unauthorized external send", e))
        if (
            e.group == "external_send"
            and e.facts.get("agentdojo.message_recipient_source") in {"untrusted_tool_result", "injection_text"}
            and not e.args_match_user_entity
        ):
            hits.append(self._block("ADJ-SLACK-INJECTED-RECIPIENT", "message recipient appears sourced from injected content", e))
        if e.group == "external_send" and e.facts.get("agentdojo.message_contains_private_data") and e.args_match_untrusted_entity:
            hits.append(self._block("ADJ-SLACK-PRIVATE-EXFIL", "private data would be sent to an injected recipient or channel", e))
        if e.group == "external_send" and e.facts.get("agentdojo.message_recipient_source") == "unknown" and not e.task_authorized:
            hits.append(self._confirm("ADJ-SLACK-CONFIRM-UNKNOWN-DESTINATION", "unknown message destination requires confirmation", e))
        if (
            e.group == "booking_commit"
            and e.injection_seen
            and (not e.task_authorized or e.sensitive_args_not_in_user_task)
            and not e.args_match_user_entity
        ):
            hits.append(self._block("ADJ-TRAVEL-001", "injection-like travel output attempted unauthorized or mismatched booking", e))
        if e.group == "booking_commit" and e.facts.get("agentdojo.target_entity_source") == "unknown":
            hits.append(self._confirm("ADJ-TRAVEL-CONFIRM-UNKNOWN-TARGET", "unknown travel booking target requires confirmation", e))
        if e.group == "booking_commit" and e.untrusted_seen and not e.args_match_user_entity and not e.task_authorized:
            hits.append(self._block("ADJ-TRAVEL-002", "untrusted travel content attempted unauthorized booking", e))
        if e.group == "booking_commit" and e.args_match_untrusted_entity and not e.args_match_user_entity:
            hits.append(self._block("ADJ-TRAVEL-004", "booking target appears sourced from untrusted output rather than user task", e))
        if (
            e.group == "booking_commit"
            and e.injection_seen
            and e.facts.get("agentdojo.explicit_booking_target_in_task")
            and not e.facts.get("agentdojo.booking_target_matches_user_goal")
        ):
            hits.append(
                self._block("ADJ-TRAVEL-003", "travel booking target does not match the user goal after untrusted review content", e)
            )
        if e.group == "membership_mutation":
            hits.append(self._confirm("ADJ-SLACK-CONFIRM-MEMBERSHIP-EXPANSION", "workspace membership changes require confirmation", e))
        if e.group in {"destructive_update", "credential_change"} and not e.task_authorized:
            hits.append(self._block("ADJ-STATE-001", "high-impact state mutation not authorized by user task", e))
        if e.group == "credential_change" and e.untrusted_seen:
            hits.append(self._block("ADJ-CRED-001", "credential change after untrusted observation", e))
        if e.facts.get("graph.has_private_to_external_edge") and (e.injection_seen or not e.task_authorized):
            hits.append(self._block("ADJ-GRAPH-001", "ActionGraph found private-data-to-external relation", e))
        if e.facts.get("graph.has_injection_to_side_effect_edge") and not e.task_authorized:
            hits.append(self._block("ADJ-GRAPH-002", "ActionGraph found injection-like output influencing unauthorized side effect", e))
        if e.facts.get("graph.has_attack_goal_to_action_edge"):
            hits.append(self._block("ADJ-GRAPH-003", "ActionGraph found attack-goal-to-action relation", e))
        return dedupe_hits(hits)

    def _block(self, rule_id: str, reason: str, e: EvidenceBundle) -> RuleHit:
        return RuleHit(
            rule_id=rule_id,
            decision="block",
            constraints=ConstraintDecision(execution_env="no_execute", network_scope="deny", data_scope="no_private", audit_scope="full"),
            reason=reason,
            evidence={
                key: e.facts.get(key)
                for key in sorted(e.facts)
                if key.startswith(("agentdojo.", "source.", "contract.", "history.", "graph."))
            },
        )

    def _confirm(self, rule_id: str, reason: str, e: EvidenceBundle) -> RuleHit:
        return RuleHit(
            rule_id=rule_id,
            decision="require_confirmation",
            constraints=ConstraintDecision(human_gate="approval_required", audit_scope="full"),
            reason=reason,
            evidence={
                key: e.facts.get(key)
                for key in sorted(e.facts)
                if key.startswith(("agentdojo.", "source.", "contract.", "history.", "graph."))
            },
        )


def dedupe_hits(hits: list[RuleHit]) -> list[RuleHit]:
    seen: set[str] = set()
    out: list[RuleHit] = []
    for hit in hits:
        if hit.rule_id in seen:
            continue
        seen.add(hit.rule_id)
        out.append(hit)
    return out


