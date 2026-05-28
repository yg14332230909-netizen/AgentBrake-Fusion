"""Convert AgentDojo metadata into PolicyGraph facts."""

from __future__ import annotations

from typing import Any

from ...models import ActionIR
from ...policy_engine.facts import PolicyFact


def agentdojo_facts_from_action(action: ActionIR) -> list[PolicyFact]:
    metadata = action.metadata.get("agentdojo")
    if not isinstance(metadata, dict):
        return []
    refs = [action.action_id]
    category = str(metadata.get("tool_category") or "")
    semantic = str(metadata.get("semantic_action") or action.semantic_action)
    facts = [
        PolicyFact.of("agentdojo", "suite", metadata.get("suite"), evidence_refs=refs),
        PolicyFact.of("agentdojo", "tool_name", metadata.get("tool_name"), evidence_refs=refs),
        PolicyFact.of("agentdojo", "tool_category", category, evidence_refs=refs),
        PolicyFact.of("agentdojo", "semantic_action", semantic, evidence_refs=refs),
        PolicyFact.of("agentdojo", "user_task_id", metadata.get("user_task_id"), evidence_refs=refs),
        PolicyFact.of("agentdojo", "injection_task_id", metadata.get("injection_task_id"), evidence_refs=refs),
        PolicyFact.of("agentdojo", "attack_surface", metadata.get("attack_surface"), evidence_refs=refs),
        PolicyFact.of("agentdojo", "allowed_tool_categories", metadata.get("allowed_tool_categories", []), evidence_refs=refs),
        PolicyFact.of("agentdojo", "forbidden_attack_goals", metadata.get("forbidden_attack_goals", []), evidence_refs=refs),
        PolicyFact.of("agentdojo", "tool_call_boundary", True, evidence_refs=refs),
        PolicyFact.of("agentdojo", "tool_registered", bool(metadata.get("registered", True)), evidence_refs=refs),
        PolicyFact.of("agentdojo", "external_commit", category in {"booking_commit", "unknown_external_commit"} or semantic in {"external_commit", "unknown_external_commit"}, evidence_refs=refs),
        PolicyFact.of("agentdojo", "financial_commit", category == "financial_commit" or semantic == "financial_transaction", evidence_refs=refs),
        PolicyFact.of("agentdojo", "message_send", category == "message_send" or semantic == "send_external_message", evidence_refs=refs),
        PolicyFact.of("agentdojo", "private_data_read", category == "private_data_read" or semantic == "read_sensitive_context", evidence_refs=refs),
        PolicyFact.of("agentdojo", "state_mutation", bool(metadata.get("side_effect")), evidence_refs=refs),
        PolicyFact.of("agentdojo", "untrusted_observation_seen", bool(metadata.get("untrusted_observation_seen")), evidence_refs=refs),
        PolicyFact.of("agentdojo", "task_authorized_tool", bool(metadata.get("task_authorized_tool")), evidence_refs=refs),
        PolicyFact.of("agentdojo", "tool_args_sensitive", _tool_args_sensitive(metadata.get("tool_args")), evidence_refs=refs),
    ]
    return facts


def _tool_args_sensitive(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    sensitive_keys = {"password", "token", "secret", "ssn", "account", "routing", "card", "email", "recipient", "message", "body"}
    text = " ".join(f"{k}={v}" for k, v in value.items()).lower()
    return any(key in text for key in sensitive_keys)
