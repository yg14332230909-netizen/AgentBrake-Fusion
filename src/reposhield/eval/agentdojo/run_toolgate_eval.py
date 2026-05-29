"""Run AgentDojo evaluations with RepoShield ToolGate."""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from functools import partial
from pathlib import Path
from typing import Any

from openai import OpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from agentdojo.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.agent_pipeline.agent_pipeline import TOOL_FILTER_PROMPT
from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
from agentdojo.agent_pipeline.llms.local_llm import LocalLLM
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.agent_pipeline.llms import openai_llm as agentdojo_openai_llm
from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop, ToolsExecutor, tool_result_to_str
from agentdojo.attacks.base_attacks import MODEL_NAMES
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.benchmark import benchmark_suite_without_injections, benchmark_suite_with_injections
from agentdojo.logging import OutputLogger, TraceLogger
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.types import ChatUserMessage, get_text_content_as_str, text_content_block_from_string

from ...control_plane import RepoShieldControlPlane
from ...eval.fast_mode import load_eval_fast_mode_config
from .pipeline_wrapper import RepoShieldAgentDojoContext, build_reposhield_agentdojo_pipeline
from .result_exporter import summarize_agentdojo_audit
from .state_tracker import AgentDojoStateTracker


TRANSIENT_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}


def _is_transient_llm_error(exc: BaseException) -> bool:
    if isinstance(exc, (APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        return int(getattr(exc, "status_code", 0) or 0) in TRANSIENT_STATUS_CODES
    text = str(exc).lower()
    return any(marker in text for marker in ["error code: 502", "error code: 503", "timeout", "rate limit"])


def _run_agentdojo_task_with_retries(suite: Any, pipeline: AgentPipeline, user_task: Any, injection_task: Any, injections: dict[str, str]) -> tuple[bool, bool]:
    max_attempts = int(os.getenv("AGENTDOJO_LLM_RETRY_ATTEMPTS", "4"))
    delay_sec = float(os.getenv("AGENTDOJO_LLM_RETRY_INITIAL_SEC", "2"))
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return suite.run_task_with_pipeline(pipeline, user_task, injection_task, injections)
        except Exception as exc:  # noqa: BLE001 - AgentDojo/provider errors vary by adapter.
            last_exc = exc
            if attempt >= max_attempts or not _is_transient_llm_error(exc):
                raise
            print(
                f"[agentdojo-retry] transient LLM/API error on attempt {attempt}/{max_attempts}: {exc}",
                flush=True,
            )
            time.sleep(delay_sec)
            delay_sec = min(delay_sec * 2, 30)
    assert last_exc is not None
    raise last_exc


class OpenAICompatibleLLM(OpenAILLM):
    """OpenAI-compatible LLM that keeps system messages as `system` for DeepSeek-like APIs."""

    def query(self, query, runtime, env=None, messages=(), extra_args=None):  # type: ignore[override]
        env = env if env is not None else None
        extra_args = extra_args or {}
        openai_messages = [agentdojo_openai_llm._message_to_openai(message, self.model) for message in messages]
        for msg in openai_messages:
            if msg.get("role") == "developer":
                msg["role"] = "system"
        openai_tools = [agentdojo_openai_llm._function_to_openai(tool) for tool in runtime.functions.values()]
        completion = agentdojo_openai_llm.chat_completion_request(
            self.client, self.model, openai_messages, openai_tools, self.reasoning_effort, self.temperature
        )
        output = agentdojo_openai_llm._openai_to_assistant_message(completion.choices[0].message)
        return query, runtime, env, [*messages, output], extra_args


class OpenAICompatibleToolFilter(agentdojo_openai_llm.OpenAILLMToolFilter):
    """Tool-filter defense that preserves `system` role for OpenAI-compatible APIs."""

    def query(self, query, runtime, env=None, messages=(), extra_args=None):  # type: ignore[override]
        env = env if env is not None else None
        extra_args = extra_args or {}
        messages = [*messages, ChatUserMessage(role="user", content=[text_content_block_from_string(self.prompt)])]
        openai_messages = [agentdojo_openai_llm._message_to_openai(message, self.model) for message in messages]
        for msg in openai_messages:
            if msg.get("role") == "developer":
                msg["role"] = "system"
        openai_tools = [agentdojo_openai_llm._function_to_openai(tool) for tool in runtime.functions.values()]
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            tools=openai_tools or agentdojo_openai_llm.NOT_GIVEN,
            tool_choice="none",
            temperature=self.temperature,
        )
        output = agentdojo_openai_llm._openai_to_assistant_message(completion.choices[0].message)

        new_tools = {}
        for tool_name, tool in runtime.functions.items():
            if output["content"] is not None and tool_name in get_text_content_as_str(output["content"]):
                new_tools[tool_name] = tool
        runtime.update_functions(new_tools)
        return query, runtime, env, [*messages, output], extra_args


def build_llm(model: str, model_id: str | None, tool_delimiter: str) -> tuple[OpenAILLM | LocalLLM, str]:
    provider = (os.getenv("REPOSHIELD_LLM_PROVIDER") or "").strip().lower()
    model_key = model.lower()
    if provider == "local" or model_key == "local":
        port = os.getenv("LOCAL_LLM_PORT", "8000")
        client = OpenAI(api_key="EMPTY", base_url=f"http://localhost:{port}/v1")
        if model_id is None:
            model_id = os.getenv("LOCAL_LLM_MODEL_ID") or "local-model"
        llm = LocalLLM(client, model_id, tool_delimiter=tool_delimiter)
        setattr(llm, "name", _agentdojo_pipeline_name(model_id))
        return llm, str(getattr(llm, "name"))

    base_url = (
        os.getenv("REPOSHIELD_LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("DEEPSEEK_API_BASE")
        or "https://api.openai.com/v1"
    )
    api_key = (
        os.getenv("REPOSHIELD_LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or "EMPTY"
    )
    client = OpenAI(api_key=api_key, base_url=base_url)
    compat = "deepseek" in base_url.lower() or os.getenv("REPOSHIELD_OPENAI_COMPAT_SYSTEM_ROLE", "").lower() in {"1", "true", "yes"}
    llm = OpenAICompatibleLLM(client, model) if compat else OpenAILLM(client, model)
    setattr(llm, "name", _agentdojo_pipeline_name(model))
    return llm, str(getattr(llm, "name"))


def _agentdojo_pipeline_name(model: str) -> str:
    explicit = os.getenv("AGENTDOJO_MODEL_ALIAS")
    if explicit:
        return explicit
    if any(known in model for known in MODEL_NAMES):
        return model
    return f"local-{model}"


def build_pipeline(
    defense: str,
    llm: OpenAILLM | LocalLLM,
    control_plane: RepoShieldControlPlane | None,
    *,
    system_message: str,
    max_iters: int,
) -> AgentPipeline:
    if defense == "reposhield_toolgate":
        assert control_plane is not None
        return build_reposhield_agentdojo_pipeline(llm, control_plane, system_message=system_message, max_iters=max_iters)
    if defense == "tool_filter" and isinstance(llm, OpenAICompatibleLLM):
        formatter = partial(tool_result_to_str, dump_fn=json.dumps) if False else tool_result_to_str
        tools_loop = ToolsExecutionLoop([ToolsExecutor(formatter), llm])
        pipeline = AgentPipeline(
            [
                SystemMessage(system_message),
                InitQuery(),
                OpenAICompatibleToolFilter(TOOL_FILTER_PROMPT, llm.client, getattr(llm, "model", "deepseek-chat")),
                llm,
                tools_loop,
            ]
        )
        pipeline.name = f"{getattr(llm, 'name', getattr(llm, 'model', 'openai-compatible'))}-tool_filter"
        return pipeline
    defense_name = None if defense in {"none", "", "null"} else defense
    return AgentPipeline.from_config(
        PipelineConfig(
            llm=llm,
            model_id=getattr(llm, "model", None),
            defense=defense_name,
            system_message_name=None,
            system_message=system_message,
            tool_output_format="yaml",
        )
    )


class _NoopInvariantEngine:
    version = "noop-agentdojo-invariants"

    def evaluate(self, facts: Any) -> list[Any]:
        return []


def run_suite(
    suite_name: str,
    model: str,
    defense: str,
    *,
    model_id: str | None = None,
    benchmark_version: str = "v1.2.2",
    attack: str | None = None,
    limit: int | None = None,
    logdir: Path | None = None,
    report_dir: Path | None = None,
    system_message: str = "You are a helpful assistant.",
    tool_delimiter: str = "tool",
    repo_root: Path | None = None,
    disable_taxonomy: bool = False,
    disable_state_tracker: bool = False,
    disable_invariants: bool = False,
    policy_config: Path | None = None,
    max_iters: int = 15,
    run_name: str | None = None,
) -> dict[str, Any]:
    suite = get_suite(benchmark_version, suite_name)
    llm, llm_name = build_llm(model, model_id, tool_delimiter)
    repo_root = repo_root or Path.cwd()
    fast_mode = load_eval_fast_mode_config()
    control_plane = None
    if defense == "reposhield_toolgate":
        control_plane = RepoShieldControlPlane(
            repo_root,
            audit_path=(logdir / "agentdojo_audit.jsonl") if logdir else (repo_root / ".reposhield" / "agentdojo_audit.jsonl"),
            policy_config=policy_config,
            fast_mode=fast_mode,
        )
        if disable_invariants:
            control_plane.policy.policygraph.invariants = _NoopInvariantEngine()  # type: ignore[attr-defined]
    pipeline = build_pipeline(defense, llm, control_plane, system_message=system_message, max_iters=max_iters)
    if defense == "reposhield_toolgate" and disable_taxonomy:
        pipeline.tool_gate.taxonomy = {}  # type: ignore[attr-defined]
    if defense == "reposhield_toolgate" and disable_state_tracker:
        pipeline.state_tracker = AgentDojoStateTracker()  # type: ignore[attr-defined]
        pipeline.tool_gate.state_tracker = pipeline.state_tracker  # type: ignore[attr-defined]

    attack_obj = None if attack in {None, "", "none"} else load_attack(attack, suite, pipeline)
    user_tasks = list(suite.user_tasks.values())
    if limit is not None:
        user_tasks = user_tasks[:limit]

    utility_results: dict[tuple[str, str], bool] = {}
    security_results: dict[tuple[str, str], bool] = {}
    per_run: list[dict[str, Any]] = []

    start = time.perf_counter()
    with OutputLogger(str(logdir) if logdir else None):
        if attack_obj is None:
            for user_task in user_tasks:
                user_task_id = user_task.ID
                attack_name = "none"
                injection_task_id = "none"
                injections: dict[str, str] = {}
                if hasattr(pipeline, "set_context"):
                    pipeline.set_context(
                        RepoShieldAgentDojoContext(
                            suite=suite_name,
                            user_task_id=user_task_id,
                            injection_task_id=None,
                            task_instruction=getattr(user_task, "PROMPT", None),
                            attack_goal=getattr(user_task, "GOAL", None),
                            attack_goal_signatures=[getattr(user_task, "PROMPT", "") or getattr(user_task, "GOAL", "") or ""],
                            source_ids=[],
                            source_has_untrusted=False,
                            allowed_tools=[],
                            allowed_tool_categories=[],
                            run_id=f"{suite_name}-{user_task_id}-benign",
                            metadata={"disable_state_tracker": disable_state_tracker},
                        )
                    )
                with TraceLogger(
                    delegate=OutputLogger(str(logdir) if logdir else None),
                    suite_name=suite.name,
                    user_task_id=user_task_id,
                    injection_task_id=injection_task_id,
                    injections=injections,
                    attack_type=attack_name,
                    pipeline_name=getattr(pipeline, "name", llm_name),
                    benchmark_version=benchmark_version,
                ) as logger:
                    utility, security = _run_agentdojo_task_with_retries(suite, pipeline, user_task, None, injections)
                    logger.set_contextarg("utility", utility)
                    logger.set_contextarg("security", security)
                utility_results[(user_task_id, injection_task_id)] = utility
                security_results[(user_task_id, injection_task_id)] = security
                per_run.append({"user_task_id": user_task_id, "injection_task_id": None, "utility": utility, "security": security})
        else:
            if attack_obj.is_dos_attack:
                injection_task_ids = [next(iter(suite.injection_tasks.keys()))]
            else:
                injection_task_ids = list(suite.injection_tasks.keys())
            for user_task in user_tasks:
                for injection_task_id in injection_task_ids:
                    injection_task = suite.get_injection_task_by_id(injection_task_id)
                    injections = attack_obj.attack(user_task, injection_task)
                    if hasattr(pipeline, "set_context"):
                        pipeline.set_context(
                            RepoShieldAgentDojoContext(
                                suite=suite_name,
                                user_task_id=user_task.ID,
                                injection_task_id=injection_task_id,
                                task_instruction=getattr(user_task, "PROMPT", None),
                                injection_instruction=getattr(injection_task, "GOAL", None),
                                attack_goal=getattr(injection_task, "GOAL", None),
                                attack_goal_signatures=[
                                    getattr(injection_task, "GOAL", "") or "",
                                    getattr(injection_task, "PROMPT", "") or "",
                                ],
                                source_ids=list(injections.keys()),
                                source_has_untrusted=bool(injections),
                                untrusted_observation_seen=bool(injections),
                                allowed_tools=[],
                                allowed_tool_categories=[],
                                run_id=f"{suite_name}-{user_task.ID}-{injection_task_id}",
                                metadata={"disable_state_tracker": disable_state_tracker},
                            )
                        )
                    with TraceLogger(
                        delegate=OutputLogger(str(logdir) if logdir else None),
                        suite_name=suite.name,
                        user_task_id=user_task.ID,
                        injection_task_id=injection_task_id,
                        injections=injections,
                        attack_type=attack_obj.name,
                        pipeline_name=getattr(pipeline, "name", llm_name),
                        benchmark_version=benchmark_version,
                    ) as logger:
                        utility, security = _run_agentdojo_task_with_retries(suite, pipeline, user_task, injection_task, injections)
                        logger.set_contextarg("utility", utility)
                        logger.set_contextarg("security", security)
                    utility_results[(user_task.ID, injection_task_id)] = utility
                    security_results[(user_task.ID, injection_task_id)] = security
                    per_run.append(
                        {
                            "user_task_id": user_task.ID,
                            "injection_task_id": injection_task_id,
                            "utility": utility,
                            "security": security,
                            "injections": injections,
                        }
                    )

    duration_sec = time.perf_counter() - start
    run_summary = {
        "run_name": run_name or f"{suite_name}_{defense}_{attack_obj.name if attack_obj else 'none'}",
        "suite": suite_name,
        "benchmark_version": benchmark_version,
        "model": model,
        "model_id": model_id,
        "defense": defense,
        "attack": attack_obj.name if attack_obj else "none",
        "total_runtime_sec": duration_sec,
        "total_runtime_min": duration_sec / 60.0,
        "utility_results": {f"{u}::{i}": v for (u, i), v in utility_results.items()},
        "security_results": {f"{u}::{i}": v for (u, i), v in security_results.items()},
        "utility_under_attack": _avg_bool(utility_results.values()),
        "security": _avg_bool(security_results.values()) if security_results else 1.0,
        "targeted_asr": 1.0 - _avg_bool(security_results.values()) if security_results else 0.0,
        "per_run": per_run,
    }
    if control_plane is not None:
        run_summary["reposhield_audit_summary"] = summarize_agentdojo_audit(control_plane.audit.read_events())
        run_summary["reposhield_audit_latency"] = control_plane.audit.latency_stats()
    default_name = run_name or f"{suite_name}_{defense}_{attack_obj.name if attack_obj else 'none'}"
    if report_dir:
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"{default_name}.json"
        report_file.write_text(
            json.dumps(run_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return run_summary


def _avg_bool(values: Any) -> float:
    vals = [1.0 if bool(v) else 0.0 for v in values]
    return float(sum(vals) / len(vals)) if vals else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--attack", default="none")
    parser.add_argument("--defense", default="none")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--logdir", type=Path, default=None)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--system-message", default="You are a helpful assistant.")
    parser.add_argument("--tool-delimiter", default="tool")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--policy-config", type=Path, default=None)
    parser.add_argument("--disable-taxonomy", action="store_true")
    parser.add_argument("--disable-state-tracker", action="store_true")
    parser.add_argument("--disable-invariants", action="store_true")
    parser.add_argument("--max-iters", type=int, default=15)
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()

    summary = run_suite(
        args.suite,
        args.model,
        args.defense,
        model_id=args.model_id,
        benchmark_version=args.benchmark_version,
        attack=args.attack,
        limit=args.limit,
        logdir=args.logdir,
        report_dir=args.report_dir,
        system_message=args.system_message,
        tool_delimiter=args.tool_delimiter,
        repo_root=args.repo_root,
        policy_config=args.policy_config,
        disable_taxonomy=args.disable_taxonomy,
        disable_state_tracker=args.disable_state_tracker,
        disable_invariants=args.disable_invariants,
        max_iters=args.max_iters,
        run_name=args.run_name,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
