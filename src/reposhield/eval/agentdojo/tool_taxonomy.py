"""AgentDojo tool taxonomy mapped to RepoShield semantic actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentDojoToolInfo:
    tool_name: str
    semantic_action: str
    category: str
    risk: str
    side_effect: bool
    constraints: dict[str, Any]
    registered: bool = True


AGENTDOJO_TOOL_TAXONOMY: dict[str, dict[str, Any]] = {
    "get_user_info": {"semantic_action": "read_sensitive_context", "category": "private_data_read", "risk": "medium"},
    "read_email": {"semantic_action": "read_sensitive_context", "category": "private_data_read", "risk": "medium"},
    "read_bank_account": {"semantic_action": "read_sensitive_context", "category": "private_data_read", "risk": "medium"},
    "search_email": {"semantic_action": "read_context", "category": "search_or_read", "risk": "low"},
    "search_workspace": {"semantic_action": "read_context", "category": "search_or_read", "risk": "low"},
    "lookup": {"semantic_action": "browse_context", "category": "navigation", "risk": "low"},
    "open_page": {"semantic_action": "browse_context", "category": "navigation", "risk": "low"},
    "send_email": {
        "semantic_action": "send_external_message",
        "category": "message_send",
        "risk": "high",
        "side_effect": True,
        "constraints": {"audit_scope": "full_audit"},
    },
    "send_slack_message": {
        "semantic_action": "send_external_message",
        "category": "message_send",
        "risk": "high",
        "side_effect": True,
        "constraints": {"audit_scope": "full_audit"},
    },
    "transfer_money": {
        "semantic_action": "financial_transaction",
        "category": "financial_commit",
        "risk": "critical",
        "side_effect": True,
        "constraints": {"human_gate": "approval_required"},
    },
    "pay_bill": {
        "semantic_action": "financial_transaction",
        "category": "financial_commit",
        "risk": "critical",
        "side_effect": True,
        "constraints": {"human_gate": "approval_required"},
    },
    "book_hotel": {"semantic_action": "external_commit", "category": "booking_commit", "risk": "high", "side_effect": True},
    "book_flight": {"semantic_action": "external_commit", "category": "booking_commit", "risk": "high", "side_effect": True},
    "delete_email": {"semantic_action": "destructive_update", "category": "delete_or_modify", "risk": "high", "side_effect": True},
    "update_record": {"semantic_action": "destructive_update", "category": "delete_or_modify", "risk": "high", "side_effect": True},
    "run_command": {"semantic_action": "shell_command", "category": "terminal_or_code", "risk": "critical", "side_effect": True},
    "terminal": {"semantic_action": "shell_command", "category": "terminal_or_code", "risk": "critical", "side_effect": True},
}


READ_ONLY_HINTS = ("get_", "read_", "search_", "lookup", "list_", "open_")
EXTERNAL_COMMIT_HINTS = ("send_", "transfer", "pay_", "book_", "delete_", "update_", "create_", "submit_")


def classify_agentdojo_tool(tool_name: str, tool_args: dict[str, Any] | None = None) -> AgentDojoToolInfo:
    name = tool_name.strip()
    normalized = name.lower()
    if normalized in AGENTDOJO_TOOL_TAXONOMY:
        item = dict(AGENTDOJO_TOOL_TAXONOMY[normalized])
        return AgentDojoToolInfo(
            tool_name=name,
            semantic_action=str(item["semantic_action"]),
            category=str(item["category"]),
            risk=str(item["risk"]),
            side_effect=bool(item.get("side_effect", item["risk"] in {"high", "critical"})),
            constraints=dict(item.get("constraints") or {}),
            registered=True,
        )

    args = tool_args or {}
    mutation_arg = any(key.lower() in {"amount", "recipient", "to", "email", "message", "body", "delete", "confirm"} for key in args)
    if normalized.startswith(READ_ONLY_HINTS) and not mutation_arg:
        return AgentDojoToolInfo(name, "read_context", "unknown_read_only", "low", False, {"unknown_tool": True}, registered=False)
    if normalized.startswith(EXTERNAL_COMMIT_HINTS) or mutation_arg:
        return AgentDojoToolInfo(
            name,
            "unknown_external_commit",
            "unknown_external_commit",
            "critical",
            True,
            {"unknown_tool": True, "human_gate": "approval_required"},
            registered=False,
        )
    return AgentDojoToolInfo(
        name,
        "unknown_side_effect",
        "unknown_side_effect",
        "high",
        True,
        {"unknown_tool": True, "human_gate": "approval_required"},
        registered=False,
    )

