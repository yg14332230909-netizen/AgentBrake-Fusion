from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = ROOT / "experiments" / "agentdojo" / "configs" / "paired_mini_manifest.json"
DEFAULT_OUT = ROOT / "experiments" / "agentdojo" / "reports" / "paired_mini"

METHOD_TO_DEFENSE = {
    "no_defense": "none",
    "gateway_only": "reposhield_toolgate",
    "agentdojo_tool_filter": "tool_filter",
    "reposhield_tool_firewall": "agentdojo_firewall",
    "reposhield_full": "agentdojo_firewall",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run paired AgentDojo mini benchmark from a shared manifest")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    plan = build_plan(manifest, args.out_dir)
    (args.out_dir / "paired_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    if args.dry_run:
        print(args.out_dir / "paired_plan.json")
        return 0
    for command in plan:
        subprocess.run(command, cwd=ROOT, check=True)
    return 0


def build_plan(manifest: dict, out_dir: Path) -> list[list[str]]:
    commands: list[list[str]] = []
    for suite, suite_spec in manifest["suites"].items():
        for method in manifest["methods"]:
            command = [
                    sys.executable,
                    "-m",
                    "reposhield.eval.agentdojo.runner.run_tool_firewall_eval",
                    "--suite",
                    suite,
                    "--model",
                    manifest["model"],
                    "--benchmark-version",
                    manifest["agentdojo_version"],
                    "--attack",
                    manifest["attack"],
                    "--defense",
                    METHOD_TO_DEFENSE.get(method, method),
                    "--report-dir",
                    str(out_dir),
                    "--run-name",
                    f"{suite}_{method}_{manifest['attack']}",
                ]
            user_tasks = [str(item) for item in suite_spec.get("user_tasks", [])]
            injection_tasks = [str(item) for item in suite_spec.get("injection_tasks", [])]
            if user_tasks:
                command.extend(["--user-tasks", *user_tasks])
            if injection_tasks:
                command.extend(["--injection-tasks", *injection_tasks])
            commands.append(command)
    return commands


if __name__ == "__main__":
    raise SystemExit(main())
