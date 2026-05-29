from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from agentdojo.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.basic_elements import InitQuery
from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop, ToolsExecutor
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
from agentdojo.types import ChatMessage

from .tool_firewall import AgentDojoToolFirewall
from .types import ToolCallContext


@dataclass(slots=True)
class AgentDojoFirewallTaskContext:
    suite: str = "workspace"
    user_task: str = ""
    user_task_id: str | int | None = None
    injection_task_id: str | int | None = None
    allowed_tools: list[str] = field(default_factory=list)
    allowed_groups: list[str] = field(default_factory=list)
    attack_goal_signatures: list[str] = field(default_factory=list)
    run_id: str = "agentdojo_run"
    sample_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any] | None, *, suite: str | None = None) -> "AgentDojoFirewallTaskContext":
        data = dict(mapping or {})
        if suite is not None:
            data.setdefault("suite", suite)
        return cls(
            suite=str(data.get("suite", "workspace")),
            user_task=str(data.get("user_task", "")),
            user_task_id=data.get("user_task_id"),
            injection_task_id=data.get("injection_task_id"),
            allowed_tools=[str(item) for item in data.get("allowed_tools", []) or []],
            allowed_groups=[str(item) for item in data.get("allowed_groups", []) or []],
            attack_goal_signatures=[str(item) for item in data.get("attack_goal_signatures", []) or []],
            run_id=str(data.get("run_id", "agentdojo_run")),
            sample_id=data.get("sample_id"),
            metadata={k: v for k, v in data.items() if k not in {"suite", "user_task", "user_task_id", "injection_task_id", "allowed_tools", "allowed_groups", "attack_goal_signatures", "run_id", "sample_id"}},
        )

    def to_tool_context(self, *, tool_name: str, tool_args: dict[str, Any]) -> ToolCallContext:
        return ToolCallContext(
            suite=self.suite,
            tool_name=tool_name,
            tool_args=tool_args,
            user_task=self.user_task,
            user_task_id=self.user_task_id,
            injection_task_id=self.injection_task_id,
            allowed_tools=set(self.allowed_tools),
            allowed_groups=set(self.allowed_groups),
            attack_goal_signatures=list(self.attack_goal_signatures),
            run_id=self.run_id,
            sample_id=self.sample_id,
        )


class AgentDojoGuardedFunctionsRuntime:
    """Drop-in runtime wrapper that gates every tool call through RepoShield."""

    def __init__(
        self,
        runtime: FunctionsRuntime,
        firewall: AgentDojoToolFirewall | None = None,
        *,
        task_context: Mapping[str, Any] | None = None,
        suite: str | None = None,
    ) -> None:
        self.runtime = runtime
        self.firewall = firewall or AgentDojoToolFirewall()
        self._task_context = AgentDojoFirewallTaskContext.from_mapping(task_context, suite=suite)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.runtime, name)

    def set_context(self, task_context: Mapping[str, Any] | AgentDojoFirewallTaskContext | Any = None, **kwargs: Any) -> None:
        if isinstance(task_context, AgentDojoFirewallTaskContext):
            self._task_context = task_context
            return
        if hasattr(task_context, "as_dict"):
            data = dict(task_context.as_dict())
        elif isinstance(task_context, Mapping):
            data = dict(task_context)
        else:
            data = {}
        data.update(kwargs)
        self._task_context = AgentDojoFirewallTaskContext.from_mapping(data, suite=data.get("suite", self._task_context.suite))

    def run_function(
        self,
        env: Env | None,
        function: str,
        kwargs: Mapping[str, Any],
        raise_on_error: bool = False,
    ) -> tuple[Any, str | None]:
        tool_args = dict(kwargs or {})
        context = self._task_context.to_tool_context(tool_name=function, tool_args=tool_args)
        decision = self.firewall.guard_before_tool(context)
        if not decision.execute:
            return decision.safe_result, None

        result, error = self.runtime.run_function(env, function, tool_args, raise_on_error=raise_on_error)
        if error is not None and raise_on_error:
            return result, error
        sanitized = self.firewall.observe_after_tool(context, result)
        return sanitized, error


class AgentDojoRuntimeInjector(BasePipelineElement):
    """Pipeline element that replaces the runtime with a guarded wrapper."""

    def __init__(
        self,
        firewall: AgentDojoToolFirewall,
        context_getter: Callable[[], Mapping[str, Any] | dict[str, Any] | None],
        *,
        default_suite: str = "workspace",
    ) -> None:
        self.firewall = firewall
        self.context_getter = context_getter
        self.default_suite = default_suite

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: list[ChatMessage] | tuple[ChatMessage, ...] = (),
        extra_args: dict[str, Any] | None = None,
    ) -> tuple[str, FunctionsRuntime, Env, list[ChatMessage] | tuple[ChatMessage, ...], dict[str, Any]]:
        context = self.context_getter() or {}
        suite = str(context.get("suite", self.default_suite))
        if isinstance(runtime, AgentDojoGuardedFunctionsRuntime):
            runtime.set_context(context, suite=suite)
            return query, runtime, env, messages, extra_args or {}
        guarded = AgentDojoGuardedFunctionsRuntime(runtime, self.firewall, task_context=context, suite=suite)
        return query, guarded, env, messages, extra_args or {}


@dataclass(slots=True)
class AgentDojoFirewallPipelineContext:
    context: dict[str, Any] = field(default_factory=dict)

    def set(self, value: Mapping[str, Any] | None) -> None:
        self.context = dict(value or {})

    def as_dict(self) -> dict[str, Any]:
        return dict(self.context)


class AgentDojoFirewallPipeline(BasePipelineElement):
    def __init__(
        self,
        llm: BasePipelineElement,
        *,
        firewall: AgentDojoToolFirewall | None = None,
        system_message: str | None = None,
        max_iters: int = 15,
        default_suite: str = "workspace",
    ) -> None:
        self.llm = llm
        self.firewall = firewall or AgentDojoToolFirewall()
        self.system_message = system_message
        self.max_iters = max_iters
        self.name = f"{getattr(llm, 'name', getattr(llm, 'model', 'llm'))}-agentdojo_firewall"
        self.context = AgentDojoFirewallPipelineContext()
        self._runtime_injector = AgentDojoRuntimeInjector(self.firewall, self.context.as_dict, default_suite=default_suite)
        self._pipeline = AgentPipeline(elements=[InitQuery(), llm, ToolsExecutionLoop([self._runtime_injector, ToolsExecutor(), llm], max_iters=max_iters)])
        self._pipeline.name = self.name

    def set_context(self, context: Mapping[str, Any] | Any | None) -> None:
        if hasattr(context, "as_dict"):
            self.context.set(context.as_dict())
        else:
            self.context.set(context)

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: list[ChatMessage] | tuple[ChatMessage, ...] = (),
        extra_args: dict[str, Any] | None = None,
    ) -> tuple[str, FunctionsRuntime, Env, list[ChatMessage] | tuple[ChatMessage, ...], dict[str, Any]]:
        extra_args = dict(extra_args or {})
        extra_args["agentdojo_firewall_context"] = self.context.as_dict()
        return self._pipeline.query(query, runtime, env, messages, extra_args)


def wrap_functions_runtime(
    runtime: FunctionsRuntime,
    *,
    firewall: AgentDojoToolFirewall | None = None,
    task_context: Mapping[str, Any] | None = None,
    suite: str | None = None,
) -> AgentDojoGuardedFunctionsRuntime:
    return AgentDojoGuardedFunctionsRuntime(runtime, firewall, task_context=task_context, suite=suite)


def build_agentdojo_firewall_pipeline(
    llm: BasePipelineElement,
    *,
    firewall: AgentDojoToolFirewall | None = None,
    system_message: str | None = None,
    max_iters: int = 15,
    default_suite: str = "workspace",
) -> AgentDojoFirewallPipeline:
    return AgentDojoFirewallPipeline(
        llm,
        firewall=firewall,
        system_message=system_message,
        max_iters=max_iters,
        default_suite=default_suite,
    )
