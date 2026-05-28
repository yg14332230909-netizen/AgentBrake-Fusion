"""AgentDojo tool taxonomy mapped to RepoShield semantic actions."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency fallback
    yaml = None


@dataclass(frozen=True)
class AgentDojoToolInfo:
    tool_name: str
    semantic_action: str
    category: str
    risk: str
    side_effect: bool
    constraints: dict[str, Any]
    registered: bool = True


def _taxonomy_path() -> Path:
    return Path(__file__).with_name("tool_taxonomy.yaml")


@lru_cache(maxsize=1)
def load_agentdojo_taxonomy() -> dict[str, dict[str, Any]]:
    if yaml is None:
        return _fallback_taxonomy()
    data = yaml.safe_load(_taxonomy_path().read_text(encoding="utf-8")) or {}
    tools = data.get("tools", {}) if isinstance(data, dict) else {}
    return {str(name).lower(): dict(value) for name, value in tools.items() if isinstance(value, dict)}


AGENTDOJO_TOOL_TAXONOMY = load_agentdojo_taxonomy()


def coverage_report(known_tools: list[str]) -> dict[str, Any]:
    taxonomy = load_agentdojo_taxonomy()
    normalized = {tool.strip().lower() for tool in known_tools if tool}
    covered = sorted(tool for tool in normalized if tool in taxonomy)
    unknown = sorted(tool for tool in normalized if tool not in taxonomy)
    total = len(normalized)
    return {
        "registered_tool_rate": (len(covered) / total) if total else 1.0,
        "known_tool_count": total,
        "registered_tool_count": len(covered),
        "unknown_tools": unknown,
    }


def classify_agentdojo_tool(tool_name: str, tool_args: dict[str, Any] | None = None) -> AgentDojoToolInfo:
    taxonomy = load_agentdojo_taxonomy()
    name = tool_name.strip()
    normalized = name.lower()
    if normalized in taxonomy:
        item = dict(taxonomy[normalized])
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


def _fallback_taxonomy() -> dict[str, dict[str, Any]]:
    return {
        "send_email": {"semantic_action": "send_external_message", "category": "message_send", "risk": "high"},
        "transfer_money": {"semantic_action": "financial_transaction", "category": "financial_commit", "risk": "critical"},
    }


READ_ONLY_HINTS = ("get_", "read_", "search_", "lookup", "list_", "open_")
EXTERNAL_COMMIT_HINTS = ("send_", "transfer", "pay_", "book_", "delete_", "update_", "create_", "submit_")
