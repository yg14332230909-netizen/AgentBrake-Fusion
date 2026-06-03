from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
VARIANTS = ("rule_only", "no_binding", "no_context_graph", "no_recovery_guidance")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Qwen-Plus ablation diagnostic variants")
    parser.add_argument("--case-plan", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", default="qwen-plus")
    parser.add_argument("--attack", default="important_instructions")
    parser.add_argument("--variants", nargs="+", default=list(VARIANTS))
    parser.add_argument("--confirmation-mode", default="strict_eval", choices=["strict_eval"])
    parser.add_argument("--save-full-trace", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args()

    plan = json.loads(args.case_plan.read_text(encoding="utf-8-sig"))
    cases = list(plan["cases"])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "raw").mkdir(parents=True, exist_ok=True)
    raw_runs = args.out_dir / "raw_runs"
    trace_root = args.out_dir / "full_traces"
    python_bin = os.environ.get("PYTHON", "python")
    commands = build_commands(cases, args, raw_runs, trace_root, python_bin)
    write_json(args.out_dir / "run_plan.json", commands)

    failures: list[dict[str, Any]] = []
    completed: dict[str, list[str]] = {variant: [] for variant in args.variants}
    for item in commands:
        out_file = Path(item["raw_output"])
        if args.skip_existing and out_file.exists():
            completed[item["variant"]].append(str(out_file.as_posix()))
            continue
        out_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(item["command"], cwd=ROOT, check=True, env=os.environ.copy())
            completed[item["variant"]].append(str(out_file.as_posix()))
        except subprocess.CalledProcessError as exc:
            failure = {
                "case_id": item["case_id"],
                "variant": item["variant"],
                "returncode": exc.returncode,
                "raw_output": item["raw_output"],
            }
            failures.append(failure)
            if args.fail_fast:
                break

    for variant, files in completed.items():
        write_json(args.out_dir / "raw" / f"{variant}.json", {"variant": variant, "raw_outputs": sorted(set(files))})
    manifest = {
        "experiment": "qwen_plus_ablation_diagnostic",
        "case_plan": str(args.case_plan.as_posix()),
        "case_count": len(cases),
        "variants": list(args.variants),
        "expected_run_count": len(cases) * len(args.variants),
        "completed_run_count": sum(len(set(files)) for files in completed.values()),
        "failure_count": len(failures),
        "failures": failures,
        "confirmation_mode": args.confirmation_mode,
        "save_full_trace": bool(args.save_full_trace),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(args.out_dir / "run_manifest.json", manifest)
    write_json(args.out_dir / "ablation_run_failures.json", failures)
    return 1 if failures and args.fail_fast else 0


def build_commands(
    cases: list[dict[str, Any]],
    args: argparse.Namespace,
    raw_runs: Path,
    trace_root: Path,
    python_bin: str,
) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for variant in args.variants:
        if variant not in VARIANTS:
            raise ValueError(f"unsupported ablation variant: {variant}")
        for case in cases:
            case_id = str(case["phase2_case_id"])
            run_name = f"{case_id}_{variant}"
            command = [
                python_bin,
                "-m",
                "reposhield.eval.agentdojo.runner.run_tool_firewall_eval",
                "--suite",
                str(case["suite"]),
                "--model",
                args.model,
                "--benchmark-version",
                "v1.2.2",
                "--attack",
                args.attack,
                "--defense",
                "agentdojo_firewall",
                "--report-dir",
                str(raw_runs),
                "--run-name",
                run_name,
                "--user-tasks",
                str(case["user_task_id"]),
                "--injection-tasks",
                str(case["injection_task_id"]),
                "--confirmation-mode",
                args.confirmation_mode,
                "--ablation-profile",
                variant,
            ]
            if args.save_full_trace:
                command.extend(["--save-full-trace", "--trace-dir", str(trace_root / variant)])
            commands.append(
                {
                    "case_id": case_id,
                    "variant": variant,
                    "suite": case["suite"],
                    "raw_output": str((raw_runs / f"{run_name}.json").as_posix()),
                    "command": command,
                }
            )
    return commands


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
