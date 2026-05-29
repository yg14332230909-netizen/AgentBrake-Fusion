from __future__ import annotations

from typing import Any

from .models_compat import sha256_text
from .state import AgentDojoStateTracker
from .task_authorizer import sensitive_args_not_in_user_task, task_authorizes_tool
from .types import EvidenceBundle, ToolCallContext, ToolSpec

SENSITIVE_ARG_KEYS = {"password", "token", "secret", "iban", "account", "recipient", "to", "email", "message", "body", "file_id", "amount"}

class AgentDojoEvidenceBuilder:
    def build(self, *, context: ToolCallContext, spec: ToolSpec, state: AgentDojoStateTracker, graph_facts: dict[str, Any] | None = None) -> EvidenceBundle:
        task_authorized = task_authorizes_tool(context, spec)
        sensitive_args_present = self._sensitive_args_present(context.tool_args, spec)
        sensitive_mismatch = sensitive_args_not_in_user_task(context.tool_args, spec, context.user_task)
        attack_goal_overlap = state.attack_goal_overlap(context.tool_args)
        unknown = spec.group == "unknown"
        facts = {
            "agentdojo.suite": context.suite,
            "agentdojo.tool_name": context.tool_name,
            "agentdojo.semantic_action": spec.semantic_action,
            "agentdojo.tool_group": spec.group,
            "agentdojo.risk": spec.risk,
            "agentdojo.side_effect": spec.side_effect,
            "agentdojo.read_private": spec.read_private,
            "agentdojo.read_untrusted": spec.read_untrusted,
            "agentdojo.external_sink": spec.external_sink,
            "agentdojo.state_mutation": spec.state_mutation,
            "agentdojo.task_authorized": task_authorized,
            "agentdojo.untrusted_seen": state.untrusted_seen,
            "agentdojo.injection_seen": state.injection_seen,
            "agentdojo.private_data_seen": state.private_data_seen,
            "agentdojo.financial_data_seen": state.financial_data_seen,
            "agentdojo.attack_goal_overlap": attack_goal_overlap,
            "agentdojo.unknown_tool": unknown,
            "agentdojo.sensitive_args_present": sensitive_args_present,
            "agentdojo.sensitive_args_not_in_user_task": sensitive_mismatch,
            "source.has_untrusted": state.untrusted_seen,
            "source.has_injection_like": state.injection_seen,
            "source.trust_floor": "untrusted" if state.untrusted_seen else "trusted",
            "contract.match": "match" if task_authorized else ("violation" if spec.side_effect else "unknown"),
            "history.private_data_seen": state.private_data_seen,
            "history.financial_data_seen": state.financial_data_seen,
            "history.untrusted_seen": state.untrusted_seen,
            "history.injection_seen": state.injection_seen,
        }
        if graph_facts:
            facts.update(graph_facts)
        return EvidenceBundle(
            suite=context.suite,
            tool_name=context.tool_name,
            semantic_action=spec.semantic_action,
            group=spec.group,
            risk=spec.risk,
            side_effect=spec.side_effect,
            read_private=spec.read_private,
            read_untrusted=spec.read_untrusted,
            external_sink=spec.external_sink,
            state_mutation=spec.state_mutation,
            task_authorized=task_authorized,
            untrusted_seen=state.untrusted_seen,
            injection_seen=state.injection_seen,
            private_data_seen=state.private_data_seen,
            financial_data_seen=state.financial_data_seen,
            attack_goal_overlap=attack_goal_overlap,
            unknown_tool=unknown,
            sensitive_args_present=sensitive_args_present,
            sensitive_args_not_in_user_task=sensitive_mismatch,
            tool_args_digest=sha256_text(repr(context.tool_args)),
            state_digest=state.digest(),
            facts=facts,
        )

    def _sensitive_args_present(self, args: dict[str, Any], spec: ToolSpec) -> bool:
        text = " ".join(f"{k}={v}" for k, v in args.items()).lower()
        return any(key.lower() in text for key in set(spec.sensitive_args) | SENSITIVE_ARG_KEYS)
