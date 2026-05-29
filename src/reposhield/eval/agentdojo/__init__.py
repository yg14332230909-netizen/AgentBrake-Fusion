"""AgentDojo evaluation integration."""

from .fact_adapter import agentdojo_facts_from_action
from .pipeline_wrapper import RepoShieldAgentDojoPipeline, build_reposhield_agentdojo_pipeline
from .result_exporter import summarize_agentdojo_audit
from .state_tracker import AgentDojoStateTracker
from .tool_gate import RepoShieldToolGate, ToolGateResult, taxonomy_coverage_summary
from .tool_taxonomy import AGENTDOJO_TOOL_TAXONOMY, classify_agentdojo_tool, coverage_report, load_agentdojo_taxonomy

__all__ = [
    "AGENTDOJO_TOOL_TAXONOMY",
    "RepoShieldAgentDojoPipeline",
    "RepoShieldToolGate",
    "ToolGateResult",
    "AgentDojoStateTracker",
    "agentdojo_facts_from_action",
    "build_reposhield_agentdojo_pipeline",
    "classify_agentdojo_tool",
    "coverage_report",
    "load_agentdojo_taxonomy",
    "summarize_agentdojo_audit",
    "taxonomy_coverage_summary",
]


def __getattr__(name: str):
    if name in {"RepoShieldToolGate", "ToolGateResult"}:
        from .tool_gate import RepoShieldToolGate, ToolGateResult

        return {"RepoShieldToolGate": RepoShieldToolGate, "ToolGateResult": ToolGateResult}[name]
    if name in {"reposhield_agentdojo", "register_native_defense"}:
        if name == "reposhield_agentdojo":
            from .inspect_adapter import reposhield_agentdojo

            return reposhield_agentdojo
        from .agentdojo_defense import register_native_defense

        return register_native_defense
    if name in {"RepoShieldAgentDojoPipeline", "build_reposhield_agentdojo_pipeline"}:
        from .pipeline_wrapper import RepoShieldAgentDojoPipeline, build_reposhield_agentdojo_pipeline

        return {"RepoShieldAgentDojoPipeline": RepoShieldAgentDojoPipeline, "build_reposhield_agentdojo_pipeline": build_reposhield_agentdojo_pipeline}[name]
    raise AttributeError(name)
