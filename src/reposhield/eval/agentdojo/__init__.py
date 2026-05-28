"""AgentDojo evaluation integration."""

from .fact_adapter import agentdojo_facts_from_action
from .tool_taxonomy import AGENTDOJO_TOOL_TAXONOMY, classify_agentdojo_tool

__all__ = [
    "AGENTDOJO_TOOL_TAXONOMY",
    "RepoShieldToolGate",
    "ToolGateResult",
    "agentdojo_facts_from_action",
    "classify_agentdojo_tool",
]


def __getattr__(name: str):
    if name in {"RepoShieldToolGate", "ToolGateResult"}:
        from .tool_gate import RepoShieldToolGate, ToolGateResult

        return {"RepoShieldToolGate": RepoShieldToolGate, "ToolGateResult": ToolGateResult}[name]
    raise AttributeError(name)
