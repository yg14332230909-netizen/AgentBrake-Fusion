"""Track AgentDojo state across tool calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentDojoStateTracker:
    untrusted_observation_seen: bool = False
    private_data_seen: bool = False
    financial_data_seen: bool = False
    last_untrusted_tool: str | None = None
    tool_call_history: list[str] = field(default_factory=list)
    attack_goal_signatures: list[str] = field(default_factory=list)
    tool_result_history: list[dict[str, Any]] = field(default_factory=list)

    def observe_tool_result(self, tool_name: str, result: Any, *, suite: str | None = None) -> dict[str, bool]:
        text = str(result).lower()
        self.tool_call_history.append(tool_name)
        self.tool_result_history.append({"tool_name": tool_name, "result": _truncate(result), "suite": suite})
        if _looks_untrusted(text):
            self.untrusted_observation_seen = True
            self.last_untrusted_tool = tool_name
        if _looks_private(text) or tool_name in {
            "get_iban",
            "get_most_recent_transactions",
            "get_user_information",
            "read_inbox",
            "get_file_by_id",
        }:
            self.private_data_seen = True
        if tool_name in {"get_balance", "get_iban", "get_most_recent_transactions", "get_scheduled_transactions"}:
            self.financial_data_seen = True
        return {
            "untrusted_observation_seen": self.untrusted_observation_seen,
            "private_data_seen": self.private_data_seen,
            "financial_data_seen": self.financial_data_seen,
        }

    def observe_tool_call(self, tool_name: str, tool_args: Any = None) -> dict[str, bool]:
        args_text = str(tool_args).lower()
        if any(signature.lower() in args_text for signature in self.attack_goal_signatures):
            self.attack_goal_signatures = list(dict.fromkeys([*self.attack_goal_signatures, args_text[:200]]))
            return {"attack_goal_overlap": True}
        return {"attack_goal_overlap": False}

    def add_attack_goal(self, signature: str) -> None:
        if signature and signature not in self.attack_goal_signatures:
            self.attack_goal_signatures.append(signature)

    def as_dict(self) -> dict[str, Any]:
        return {
            "untrusted_observation_seen": self.untrusted_observation_seen,
            "private_data_seen": self.private_data_seen,
            "financial_data_seen": self.financial_data_seen,
            "last_untrusted_tool": self.last_untrusted_tool,
            "tool_call_history": list(self.tool_call_history),
            "attack_goal_signatures": list(self.attack_goal_signatures),
        }


def _truncate(value: Any, limit: int = 2000) -> str:
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "..."


def _looks_untrusted(text: str) -> bool:
    return any(
        token in text
        for token in (
            "important instructions",
            "ignore previous",
            "high priority",
            "override original",
            "prompt injection",
            "attack",
            "exfil",
        )
    )


def _looks_private(text: str) -> bool:
    return any(token in text for token in ("iban", "account number", "credit card", "password", "secret", "transaction"))
