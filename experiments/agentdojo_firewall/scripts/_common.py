from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "experiments" / "agentdojo_firewall" / "reports" / "runs"
LOG_DIR = ROOT / "experiments" / "agentdojo_firewall" / "logs"


def ensure_dirs() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def run_eval(*, suite: str, defense: str, run_name: str, attack: str, model: str | None = None) -> None:
    ensure_dirs()
    cmd = [
        sys.executable,
        "-m",
        "reposhield.eval.agentdojo.run_toolgate_eval",
        "--suite",
        suite,
        "--model",
        model or os.getenv("MODEL", "deepseek-chat"),
        "--defense",
        defense,
        "--attack",
        attack,
        "--run-name",
        run_name,
        "--logdir",
        str(LOG_DIR / run_name),
        "--report-dir",
        str(REPORT_DIR),
    ]
    subprocess.run(cmd, check=True, cwd=str(ROOT))
