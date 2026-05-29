from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Risk = Literal["low", "medium", "high", "critical"]
Decision = Literal["allow", "allow_in_sandbox", "sandbox_then_approval", "quarantine", "block"]
ToolGroup = Literal[
    "read_only",
    "private_read",
    "untrusted_read",
    "external_send",
    "financial_commit",
    "booking_commit",
    "calendar_mutation",
    "workspace_mutation",
    "destructive_update",
    "membership_mutation",
    "credential_change",
    "terminal_or_code",
    "unknown",
]

@dataclass(slots=True)
class ToolSpec:
    name: str
    semantic_action: str
    group: ToolGroup
    risk: Risk = "low"
    side_effect: bool = False
    read_private: bool = False
    read_untrusted: bool = False
    external_sink: bool = False
    state_mutation: bool = False
    sensitive_args: list[str] = field(default_factory=list)
    decision_hints: list[str] = field(default_factory=list)
    description: str = ""

@dataclass(slots=True)
class ToolCallContext:
    suite: str
    tool_name: str
    tool_args: dict[str, Any] = field(default_factory=dict)
    user_task: str = ""
    user_task_id: str | int | None = None
    injection_task_id: str | int | None = None
    allowed_tools: set[str] = field(default_factory=set)
    allowed_groups: set[str] = field(default_factory=set)
    attack_goal_signatures: list[str] = field(default_factory=list)
    run_id: str = "agentdojo_run"
    sample_id: str | None = None
    raw_tool_call: Any = None

@dataclass(slots=True)
class EvidenceBundle:
    suite: str
    tool_name: str
    semantic_action: str
    group: ToolGroup
    risk: Risk
    side_effect: bool
    read_private: bool
    read_untrusted: bool
    external_sink: bool
    state_mutation: bool
    task_authorized: bool
    untrusted_seen: bool
    injection_seen: bool
    private_data_seen: bool
    financial_data_seen: bool
    attack_goal_overlap: bool
    unknown_tool: bool
    sensitive_args_present: bool
    sensitive_args_not_in_user_task: bool
    tool_args_digest: str
    state_digest: str
    action_graph_id: str | None = None
    facts: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class ConstraintDecision:
    execution_env: Literal["host", "sandbox", "no_execute"] = "host"
    network_scope: Literal["allow", "allowlist", "deny"] = "allow"
    data_scope: Literal["raw", "redacted", "no_private"] = "raw"
    human_gate: Literal["none", "approval_required"] = "none"
    audit_scope: Literal["basic", "full"] = "basic"

    def join(self, other: "ConstraintDecision") -> "ConstraintDecision":
        return ConstraintDecision(
            execution_env=_max_order(self.execution_env, other.execution_env, ["host", "sandbox", "no_execute"]),
            network_scope=_max_order(self.network_scope, other.network_scope, ["allow", "allowlist", "deny"]),
            data_scope=_max_order(self.data_scope, other.data_scope, ["raw", "redacted", "no_private"]),
            human_gate=_max_order(self.human_gate, other.human_gate, ["none", "approval_required"]),
            audit_scope=_max_order(self.audit_scope, other.audit_scope, ["basic", "full"]),
        )

    def to_public_decision(self, *, eval_mode: bool = True) -> Decision:
        if self.execution_env == "no_execute":
            return "block"
        if self.human_gate == "approval_required" and eval_mode:
            return "block"
        if self.human_gate == "approval_required":
            return "sandbox_then_approval"
        if self.execution_env == "sandbox":
            return "allow_in_sandbox"
        if self.network_scope == "deny" or self.data_scope == "no_private":
            return "allow_in_sandbox"
        return "allow"

def _max_order(left: str, right: str, order: list[str]) -> str:
    return left if order.index(left) >= order.index(right) else right
