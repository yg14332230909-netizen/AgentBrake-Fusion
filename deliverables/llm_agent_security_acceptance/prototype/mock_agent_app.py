from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

try:
    from .mock_business_tools import MockBusinessTools
    from .supervisor_plugin import Decision, MonitoringPlugin
except ImportError:  # pragma: no cover - direct script execution fallback
    from mock_business_tools import MockBusinessTools
    from supervisor_plugin import Decision, MonitoringPlugin


class MockAgentApp:
    """A deterministic vulnerable agent used to replay red-team cases."""

    def __init__(self, supervisor: MonitoringPlugin, tools: MockBusinessTools) -> None:
        self.supervisor = supervisor
        self.tools = tools

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        case_id = case["id"]
        decisions: list[dict[str, Any]] = []
        slots: dict[str, Any] = {}

        input_decision = self.supervisor.on_model_input(case_id, case.get("user_prompt", ""), case.get("untrusted_context", ""))
        decisions.append({"stage": "model_input", "decision": input_decision.action, "reason": input_decision.reason})

        for raw_action in case.get("agent_actions", []):
            action = copy.deepcopy(raw_action)
            tool = action["tool"]
            args = self._render_args(action.get("args", {}), slots)
            decision = self.supervisor.before_tool_call(case_id, tool, args)
            decisions.append({"stage": "before_tool_call", "tool": tool, "decision": decision.action, "reason": decision.reason})
            result = self._execute_or_skip(tool, args, decision)
            self.supervisor.after_tool_call(case_id, tool, decision, result)
            if action.get("save_as"):
                slots[action["save_as"]] = self._slot_value(result)

        output_decision = self.supervisor.on_model_output(case_id, case.get("model_output", ""))
        decisions.append({"stage": "model_output", "decision": output_decision.action, "reason": output_decision.reason})
        return {
            "case_id": case_id,
            "category": case.get("category"),
            "objective": case.get("objective"),
            "decisions": decisions,
            "counts": self._count_decisions(decisions),
        }

    def _execute_or_skip(self, tool: str, args: dict[str, Any], decision: Decision) -> dict[str, Any]:
        if decision.action == "allow":
            try:
                return self.tools.call(tool, args)
            except Exception as exc:  # noqa: BLE001 - result is intentionally audited
                return {"status": "tool_error", "error": str(exc)}
        return {"status": "not_executed", "decision": decision.action, "reason": decision.reason}

    def _render_args(self, value: Any, slots: dict[str, Any]) -> Any:
        if isinstance(value, str):
            return self._render_string(value, slots)
        if isinstance(value, dict):
            return {key: self._render_args(item, slots) for key, item in value.items()}
        if isinstance(value, list):
            return [self._render_args(item, slots) for item in value]
        return value

    @staticmethod
    def _render_string(text: str, slots: dict[str, Any]) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(slots.get(key, ""))

        return re.sub(r"\$\{([A-Za-z0-9_]+)\}", replace, text)

    @staticmethod
    def _slot_value(result: dict[str, Any]) -> Any:
        if result.get("status") == "not_executed":
            return ""
        if "content" in result:
            return result["content"]
        if "output" in result:
            return result["output"]
        return json.dumps(result, ensure_ascii=False)

    @staticmethod
    def _count_decisions(decisions: list[dict[str, Any]]) -> dict[str, int]:
        counts = {"allow": 0, "ask": 0, "block": 0}
        for decision in decisions:
            value = decision.get("decision")
            if value in counts:
                counts[value] += 1
        return counts


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases
