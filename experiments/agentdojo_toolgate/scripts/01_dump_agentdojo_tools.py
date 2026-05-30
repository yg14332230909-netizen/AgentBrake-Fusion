from __future__ import annotations

import json
from pathlib import Path

from agentdojo.task_suite.load_suites import get_suite

from reposhield.eval.agentdojo.tool_taxonomy import coverage_report, load_agentdojo_taxonomy

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)


def main() -> int:
    suites = ["banking", "slack", "workspace", "travel"]
    inventory: dict[str, list[str]] = {}
    lines = ["# AgentDojo Tool Inventory", ""]
    for suite_name in suites:
        suite = get_suite("v1.2.2", suite_name)
        tools = sorted(t.name for t in suite.tools)
        inventory[suite_name] = tools
        coverage = coverage_report(tools)
        lines.append(f"## {suite_name}")
        lines.append(f"- tools: {len(tools)}")
        lines.append(f"- registered rate: {coverage['registered_tool_rate']:.3f}")
        lines.append("")
        for tool in tools:
            info = load_agentdojo_taxonomy().get(tool.lower(), {})
            lines.append(
                f"- {tool} | {info.get('semantic_action', 'unknown')} | {info.get('category', 'unknown')} | {info.get('risk', 'unknown')}"
            )
        lines.append("")

    (REPORTS / "tool_inventory.md").write_text("\n".join(lines), encoding="utf-8")
    (REPORTS / "tool_coverage.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
