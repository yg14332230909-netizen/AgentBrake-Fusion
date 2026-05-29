"""RepoShield-AgentDojo Tool Firewall.

A benchmark-specific adapter that keeps RepoShield's core idea:
ActionGraph -> multi-source evidence fusion -> deterministic ToolGate decision.
"""
from .tool_firewall import AgentDojoToolFirewall, ToolExecutionDecision
from .taxonomy import AgentDojoToolTaxonomy, ToolSpec
from .state import AgentDojoStateTracker
from .action_graph import AgentDojoActionGraphBuilder
from .fusion import AgentDojoEvidenceFusion
from .runtime_wrapper import (
    AgentDojoFirewallPipeline,
    AgentDojoGuardedFunctionsRuntime,
    AgentDojoRuntimeInjector,
    build_agentdojo_firewall_pipeline,
    wrap_functions_runtime,
)

__all__ = [
    "AgentDojoToolFirewall",
    "ToolExecutionDecision",
    "AgentDojoToolTaxonomy",
    "ToolSpec",
    "AgentDojoStateTracker",
    "AgentDojoActionGraphBuilder",
    "AgentDojoEvidenceFusion",
    "AgentDojoGuardedFunctionsRuntime",
    "AgentDojoRuntimeInjector",
    "AgentDojoFirewallPipeline",
    "wrap_functions_runtime",
    "build_agentdojo_firewall_pipeline",
]
