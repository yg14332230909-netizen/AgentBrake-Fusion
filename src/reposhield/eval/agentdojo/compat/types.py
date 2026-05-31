from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Risk = Literal["low", "medium", "high", "critical"]
Decision = Literal["allow", "allow_in_sandbox", "sandbox_then_approval", "require_confirmation", "quarantine", "block"]
AgentDojoDefenseMode = Literal["fair", "oracle_user", "oracle_full"]
ConfirmationMode = Literal["strict_eval", "oracle_user_eval", "gateway_eval"]
SanitizeMode = Literal["off", "label", "soft", "hard"]
EventStatus = Literal["proposed", "executed", "blocked", "tool_result", "sanitized_result"]
FieldRole = Literal[
    "target_entity",
    "target_attribute",
    "decision_condition",
    "recipient",
    "channel",
    "message_body",
    "amount",
    "date",
    "file_path",
    "unknown",
]
MatchType = Literal["exact", "normalized", "entity_alias", "numeric", "date", "unknown"]
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
    defense_mode: AgentDojoDefenseMode = "fair"
    ablation_config: dict[str, bool] = field(default_factory=dict)


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
    args_match_user_entity: bool
    args_match_untrusted_entity: bool
    args_match_private_entity: bool
    entity_authorization_confidence: float
    tool_args_digest: str
    state_digest: str
    action_graph_id: str | None = None
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ArgumentProvenance:
    arg_name: str
    value: Any
    source_type: Literal[
        "user_task",
        "trusted_tool_result",
        "untrusted_tool_result",
        "injection_text",
        "model_inference",
        "unknown",
    ]
    confidence: float
    evidence_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ValueMatchEvidence:
    field_name: str
    field_role: FieldRole
    value: Any
    source_type: str
    matched_prior_event_id: str | None = None
    matched_span: str | None = None
    match_type: MatchType = "unknown"
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ToolCallEvidence:
    tool_name: str
    action_type: str
    sink_type: str
    arg_provenance: list[ArgumentProvenance]
    task_contract_match: str
    asset_risk: str
    source_influence: dict[str, Any] = field(default_factory=dict)


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
        if self.human_gate == "approval_required":
            return "require_confirmation" if eval_mode else "sandbox_then_approval"
        if self.execution_env == "sandbox":
            return "allow_in_sandbox"
        if self.network_scope == "deny" or self.data_scope == "no_private":
            return "allow_in_sandbox"
        return "allow"


def _max_order(left: str, right: str, order: list[str]) -> str:
    return left if order.index(left) >= order.index(right) else right

