"""Integration profiles for quick, standard, and full agent onboarding."""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_AGENTS = (
    "generic",
    "custom-openai",
    "custom-openai-compatible",
    "codex",
    "codex-cli",
    "claude-code",
    "cursor",
    "cline",
    "openclaw",
    "openhands",
    "aider",
)
SUPPORTED_MODES = ("quick", "standard", "full")
SHIM_COMMANDS = ("bash", "sh", "python", "python3", "pip", "pip3", "npm", "npx", "pnpm", "yarn", "git", "curl")


@dataclass(frozen=True, slots=True)
class IntegrationProfile:
    agent: str
    mode: str
    guarded_tools: bool
    shims: bool
    studio: bool
    approval_api: bool
    demo_package: bool

    @property
    def expected_capabilities(self) -> list[str]:
        capabilities = [
            "model_response",
            "openai_tool_calls",
            "gateway",
            "stable_session_identity",
            "audit_log",
            "agent_env",
            "agent_instructions",
        ]
        if self.guarded_tools:
            capabilities.extend(["guarded_tool_shims", "file_guard", "exec_guard", "package_install", "mcp_tool"])
        if self.studio:
            capabilities.append("studio")
        if self.approval_api:
            capabilities.append("approval_api")
        if self.demo_package:
            capabilities.extend(["demo_package", "audit_evidence_graph"])
        return capabilities


def make_profile(agent: str, mode: str) -> IntegrationProfile:
    normalized_agent = _normalize_agent(agent)
    normalized_mode = mode.strip().lower()
    if normalized_agent not in SUPPORTED_AGENTS:
        raise ValueError(f"unsupported agent: {agent}")
    if normalized_mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported integration mode: {mode}")
    return IntegrationProfile(
        agent=normalized_agent,
        mode=normalized_mode,
        guarded_tools=normalized_mode in {"standard", "full"},
        shims=normalized_mode in {"standard", "full"},
        studio=normalized_mode == "full",
        approval_api=normalized_mode == "full",
        demo_package=normalized_mode == "full",
    )


def _normalize_agent(agent: str) -> str:
    normalized = agent.strip().lower()
    aliases = {
        "custom": "custom-openai",
        "custom-openai-compatible": "custom-openai",
        "openai-compatible": "custom-openai",
        "codex-cli": "codex",
    }
    return aliases.get(normalized, normalized)
