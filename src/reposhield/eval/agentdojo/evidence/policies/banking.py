from __future__ import annotations

from typing import Any

from .base import PolicyFinding


class BankingPolicyEngine:
    name = "banking"
    suites = {"banking"}

    def evaluate(self, *, facts: dict[str, Any], graph: dict[str, Any], context: Any) -> list[PolicyFinding]:
        group = facts.get("agentdojo.tool_group")
        findings: list[PolicyFinding] = []
        if group == "credential_change":
            if facts.get("agentdojo.untrusted_seen"):
                findings.append(
                    PolicyFinding(
                        engine=self.name,
                        decision="block",
                        confidence=0.9,
                        reason_codes=["ADJ-CRED-001"],
                        metadata={"reason": "credential change after untrusted observation"},
                    )
                )
            return findings
        if group != "financial_commit":
            return findings
        if facts.get("agentdojo.untrusted_seen") and not facts.get("agentdojo.task_authorized"):
            findings.append(
                PolicyFinding(
                    engine=self.name,
                    decision="block",
                    confidence=0.85,
                    reason_codes=["ADJ-FIN-001"],
                    unsafe_parameters=list((facts.get("agentdojo.arg_source_map") or {}).keys()),
                    metadata={"reason": "untrusted context attempted unauthorized financial commit"},
                )
            )
        if facts.get("agentdojo.target_entity_source") == "unknown" and facts.get("agentdojo.sensitive_args_present"):
            findings.append(
                PolicyFinding(
                    engine=self.name,
                    decision="require_confirmation",
                    confidence=0.7,
                    reason_codes=["ADJ-BANKING-CONFIRM-UNKNOWN-RECIPIENT"],
                    metadata={"reason": "unknown payment recipient requires user confirmation"},
                )
            )
        if (
            facts.get("agentdojo.args_match_untrusted_entity")
            or (facts.get("agentdojo.sensitive_args_not_in_user_task") and facts.get("agentdojo.untrusted_seen"))
        ) and not facts.get("agentdojo.task_authorized"):
            findings.append(
                PolicyFinding(
                    engine=self.name,
                    decision="block",
                    confidence=0.9,
                    reason_codes=["ADJ-BANKING-UNTRUSTED-FINANCIAL-COMMIT"],
                    unsafe_parameters=list((facts.get("agentdojo.arg_source_map") or {}).keys()),
                    metadata={"reason": "financial commit arguments were not authorized by user task entities"},
                )
            )
        if graph.get("graph.has_attack_goal_to_action_edge"):
            findings.append(
                PolicyFinding(
                    engine=self.name,
                    decision="block",
                    confidence=0.9,
                    reason_codes=["ADJ-BANKING-UNTRUSTED-FINANCIAL-COMMIT"],
                    unsafe_parameters=list((facts.get("agentdojo.arg_source_map") or {}).keys()),
                    metadata={"reason": "financial commit target overlaps an observed attack goal"},
                )
            )
        return findings

