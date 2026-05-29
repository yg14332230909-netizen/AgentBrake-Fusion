from __future__ import annotations

import json
from pathlib import Path

from agentdojo.task_suite.load_suites import get_suite

from reposhield.eval.agentdojo_firewall import AgentDojoToolTaxonomy


ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "experiments" / "agentdojo_firewall" / "reports"


def suite_tool_names(suite_name: str, benchmark_version: str = "v1.2.2") -> list[str]:
    suite = get_suite(benchmark_version, suite_name)
    return sorted({tool.name for tool in suite.tools})


def main() -> None:
    taxonomy = AgentDojoToolTaxonomy()
    suites = ("banking", "slack", "workspace", "travel")
    per_suite: dict[str, dict[str, object]] = {}
    all_names: set[str] = set()
    for suite_name in suites:
        names = suite_tool_names(suite_name)
        all_names.update(names)
        coverage = taxonomy.coverage(names, suite=suite_name)
        per_suite[suite_name] = {
            "tool_count": len(names),
            "tools": names,
            "coverage": coverage,
        }

    combined = sorted(all_names)
    combined_coverage = taxonomy.coverage(combined)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "benchmark_version": "v1.2.2",
        "suites": per_suite,
        "combined": {
            "tool_count": len(combined),
            "tools": combined,
            "coverage": combined_coverage,
        },
    }
    (REPORT_DIR / "tool_coverage.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["# AgentDojo Official Suite Tool Coverage", ""]
    for suite_name, item in per_suite.items():
        coverage = item["coverage"]
        lines.extend(
            [
                f"## {suite_name}",
                "",
                f"- tools: {item['tool_count']}",
                f"- registered_rate: {coverage['registered_rate']:.3f}",
                f"- unknown_rate: {coverage['unknown_rate']:.3f}",
                f"- unknown_tools: {', '.join(coverage['unknown_tools']) if coverage['unknown_tools'] else 'none'}",
                "",
            ]
        )
    lines.extend(
        [
            "## Combined",
            "",
            f"- tools: {combined_coverage['total']}",
            f"- registered_rate: {combined_coverage['registered_rate']:.3f}",
            f"- unknown_rate: {combined_coverage['unknown_rate']:.3f}",
            f"- unknown_tools: {', '.join(combined_coverage['unknown_tools']) if combined_coverage['unknown_tools'] else 'none'}",
            "",
        ]
    )
    (REPORT_DIR / "tool_coverage.md").write_text("\n".join(lines), encoding="utf-8")
    print(REPORT_DIR / "tool_coverage.md")


if __name__ == "__main__":
    main()
