"""AgentDojo-specific semantic invariants."""

from __future__ import annotations

from .constraint_lattice import DecisionConstraints
from .facts import PolicyFactSet
from .semantic_invariants import RegisteredInvariant, SemanticInvariantSpec, _bool


def agentdojo_invariants() -> list[RegisteredInvariant]:
    return [
        RegisteredInvariant(
            SemanticInvariantSpec(
                "ADJ-FIN-001",
                "untrusted_financial_commit",
                "agentdojo.financial_commit AND source.has_untrusted AND NOT agentdojo.task_authorized_tool",
                ["agentdojo.financial_commit", "source.has_untrusted", "agentdojo.task_authorized_tool"],
                DecisionConstraints(execution_env="none", network_scope="deny", audit_scope="full"),
                ["agentdojo_untrusted_financial_commit"],
                ["block"],
                100,
                "agentdojo",
            ),
            lambda f: _agentdojo(f) and _bool(f, "agentdojo", "financial_commit") and _bool(f, "source", "has_untrusted") and not _bool(f, "agentdojo", "task_authorized_tool"),
            lambda f: f.find("agentdojo") + f.find("source", "has_untrusted"),
        ),
        RegisteredInvariant(
            SemanticInvariantSpec(
                "ADJ-MSG-001",
                "untrusted_sensitive_external_message",
                "agentdojo.message_send AND source.has_untrusted AND agentdojo.tool_args_sensitive",
                ["agentdojo.message_send", "source.has_untrusted", "agentdojo.tool_args_sensitive"],
                DecisionConstraints(execution_env="none", network_scope="deny", data_scope="no_secret", audit_scope="full"),
                ["agentdojo_untrusted_sensitive_message_send"],
                ["block"],
                96,
                "agentdojo",
            ),
            lambda f: _agentdojo(f) and _bool(f, "agentdojo", "message_send") and _bool(f, "source", "has_untrusted") and _bool(f, "agentdojo", "tool_args_sensitive"),
            lambda f: f.find("agentdojo") + f.find("source", "has_untrusted"),
        ),
        RegisteredInvariant(
            SemanticInvariantSpec(
                "ADJ-DATA-001",
                "private_data_seen_then_external_message",
                "history.private_data_seen OR agentdojo.private_data_read followed by agentdojo.message_send",
                ["history.private_data_seen", "agentdojo.message_send"],
                DecisionConstraints(execution_env="none", network_scope="deny", data_scope="no_secret", audit_scope="full"),
                ["agentdojo_private_data_to_message"],
                ["block"],
                96,
                "agentdojo",
            ),
            lambda f: _agentdojo(f) and _bool(f, "agentdojo", "message_send") and (_bool(f, "history", "private_data_seen") or _bool(f, "agentdojo", "private_data_read")),
            lambda f: f.find("agentdojo") + f.find("history", "private_data_seen"),
        ),
        RegisteredInvariant(
            SemanticInvariantSpec(
                "ADJ-BOOK-001",
                "untrusted_booking_commit",
                "agentdojo.external_commit AND source.has_untrusted",
                ["agentdojo.external_commit", "source.has_untrusted"],
                DecisionConstraints(execution_env="sandbox", human_gate="approval_required", audit_scope="full"),
                ["agentdojo_untrusted_external_commit_requires_approval"],
                ["sandbox_preflight", "human_approval"],
                88,
                "agentdojo",
            ),
            lambda f: _agentdojo(f) and _bool(f, "agentdojo", "external_commit") and _bool(f, "source", "has_untrusted"),
            lambda f: f.find("agentdojo") + f.find("source", "has_untrusted"),
        ),
        RegisteredInvariant(
            SemanticInvariantSpec(
                "ADJ-STATE-001",
                "untrusted_state_mutation",
                "agentdojo.state_mutation AND source.has_untrusted AND NOT agentdojo.task_authorized_tool",
                ["agentdojo.state_mutation", "source.has_untrusted", "agentdojo.task_authorized_tool"],
                DecisionConstraints(execution_env="none", audit_scope="full"),
                ["agentdojo_untrusted_state_mutation"],
                ["block"],
                94,
                "agentdojo",
            ),
            lambda f: _agentdojo(f) and _bool(f, "agentdojo", "state_mutation") and _bool(f, "source", "has_untrusted") and not _bool(f, "agentdojo", "task_authorized_tool"),
            lambda f: f.find("agentdojo") + f.find("source", "has_untrusted"),
        ),
    ]


def _agentdojo(facts: PolicyFactSet) -> bool:
    return bool(facts.find("agentdojo", "suite") or facts.find("agentdojo", "tool_call_boundary"))

