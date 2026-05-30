"""AgentDojo evaluation integration.

The recommended path is AgentDojo Tool Firewall under
``reposhield.eval.agentdojo.gate``. Optional AgentDojo/OpenAI dependencies are
loaded only by runner and adapter entrypoints.
"""

from .evidence.state import AgentDojoStateTracker
from .evidence.taxonomy import AgentDojoToolTaxonomy
from .fact_adapter import agentdojo_facts_from_action
from .gate.tool_firewall import AgentDojoToolFirewall, ToolExecutionDecision, summarize_agentdojo_firewall_audit
from .tool_gate import RepoShieldToolGate, ToolGateResult, taxonomy_coverage_summary
from .tool_taxonomy import AGENTDOJO_TOOL_TAXONOMY, classify_agentdojo_tool, coverage_report, load_agentdojo_taxonomy

__all__ = [
    "AGENTDOJO_TOOL_TAXONOMY",
    "AgentDojoToolFirewall",
    "AgentDojoToolTaxonomy",
    "RepoShieldAgentDojoPipeline",
    "RepoShieldToolGate",
    "ToolGateResult",
    "ToolExecutionDecision",
    "AgentDojoStateTracker",
    "agentdojo_facts_from_action",
    "build_reposhield_agentdojo_pipeline",
    "classify_agentdojo_tool",
    "coverage_report",
    "load_agentdojo_taxonomy",
    "require_agentdojo",
    "summarize_agentdojo_firewall_audit",
    "summarize_agentdojo_audit",
    "taxonomy_coverage_summary",
]


def require_agentdojo() -> None:
    try:
        import agentdojo  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("AgentDojo evaluation requires: pip install -e '.[agentdojo]'") from exc


def __getattr__(name: str):
    if name == "summarize_agentdojo_audit":
        from .runner.result_exporter import summarize_agentdojo_audit

        return summarize_agentdojo_audit
    if name in {"RepoShieldToolGate", "ToolGateResult"}:
        from .tool_gate import RepoShieldToolGate, ToolGateResult

        return {"RepoShieldToolGate": RepoShieldToolGate, "ToolGateResult": ToolGateResult}[name]
    if name in {"reposhield_agentdojo", "register_native_defense"}:
        if name == "reposhield_agentdojo":
            from .adapters.inspect_adapter import reposhield_agentdojo

            return reposhield_agentdojo
        from .adapters.native_defense import register_native_defense

        return register_native_defense
    if name in {"RepoShieldAgentDojoPipeline", "build_reposhield_agentdojo_pipeline"}:
        from .adapters.pipeline_wrapper import RepoShieldAgentDojoPipeline, build_reposhield_agentdojo_pipeline

        return {
            "RepoShieldAgentDojoPipeline": RepoShieldAgentDojoPipeline,
            "build_reposhield_agentdojo_pipeline": build_reposhield_agentdojo_pipeline,
        }[name]
    raise AttributeError(name)


def __dir__() -> list[str]:
    return sorted(
        set(globals())
        | {"RepoShieldAgentDojoPipeline", "build_reposhield_agentdojo_pipeline", "reposhield_agentdojo", "register_native_defense"}
    )

