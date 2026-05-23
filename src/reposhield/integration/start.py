"""Startup summary for generated RepoShield integrations."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from .templates import load_config


def build_start_summary(
    repo_root: str | Path,
    *,
    config_path: str | Path | None = None,
    gateway_only: bool = False,
    studio_only: bool = False,
    approval_only: bool = False,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    config = load_config(Path(config_path).resolve() if config_path else repo / ".reposhield" / "config.yaml")
    services: list[dict[str, Any]] = []
    if not studio_only and not approval_only:
        gateway = config["gateway"]
        services.append(
            {
                "name": "gateway",
                "enabled": True,
                "url": f"http://{gateway['host']}:{gateway['port']}/v1",
                "script": str(repo / ".reposhield" / "scripts" / "run_gateway.sh"),
            }
        )
    if not gateway_only and not approval_only and config.get("studio", {}).get("enabled"):
        studio = config["studio"]
        services.append(
            {
                "name": "studio",
                "enabled": True,
                "url": f"http://{studio['host']}:{studio['port']}",
                "script": str(repo / ".reposhield" / "scripts" / "run_studio.sh"),
            }
        )
    if not gateway_only and not studio_only and config.get("approval", {}).get("enabled"):
        approval = config["approval"]
        services.append(
            {
                "name": "approval_api",
                "enabled": True,
                "url": f"http://{approval['host']}:{approval['port']}",
                "script": str(repo / ".reposhield" / "scripts" / "run_approval.sh"),
            }
        )
    return {
        "ok": True,
        "repo_root": str(repo),
        "mode": config["mode"],
        "agent": config["agent"],
        "services": services,
        "audit_log": config["audit"]["path"],
        "session_state": config["session"].get("state_path", str(repo / ".reposhield" / "session_state.jsonl")),
        "next_step": f"Set your agent base_url to {config['gateway']['base_url']}",
        "run_id": config["session"]["run_id"],
        "conversation_id": config["session"]["conversation_id"],
    }


def launch_start_services(
    repo_root: str | Path,
    *,
    config_path: str | Path | None = None,
    gateway_only: bool = False,
    studio_only: bool = False,
    approval_only: bool = False,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    config_file = Path(config_path).resolve() if config_path else repo / ".reposhield" / "config.yaml"
    config = load_config(config_file)
    summary = build_start_summary(
        repo,
        config_path=config_file,
        gateway_only=gateway_only,
        studio_only=studio_only,
        approval_only=approval_only,
    )
    logs_dir = repo / ".reposhield" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    launched: list[dict[str, Any]] = []
    if not studio_only and not approval_only:
        gateway = config["gateway"]
        command = [
            sys.executable,
            "-m",
            "reposhield.cli",
            "gateway-start",
            "--repo",
            str(repo),
            "--host",
            str(gateway["host"]),
            "--port",
            str(gateway["port"]),
            "--audit",
            str(config["audit"]["path"]),
            "--policy-mode",
            str(config["policy"]["mode"]),
            "--release-mode",
            str(config["policy"].get("release_mode") or "gateway_only"),
        ]
        if gateway.get("upstream_base_url"):
            command.extend(["--upstream-base-url", str(gateway["upstream_base_url"])])
        if config["policy"].get("pack"):
            command.extend(["--policy-config", str(config["policy"]["pack"])])
        launched.append(_launch("gateway", command, repo, logs_dir))
    if not gateway_only and not approval_only and config.get("studio", {}).get("enabled"):
        studio = config["studio"]
        command = [
            sys.executable,
            "-m",
            "reposhield.cli",
            "studio-server",
            "--audit",
            str(config["audit"]["path"]),
            "--approvals",
            str(config["approval"]["store"]),
            "--repo",
            str(repo),
            "--host",
            str(studio["host"]),
            "--port",
            str(studio["port"]),
        ]
        launched.append(_launch("studio", command, repo, logs_dir))
    if not gateway_only and not studio_only and config.get("approval", {}).get("enabled"):
        approval = config["approval"]
        command = [
            sys.executable,
            "-m",
            "reposhield.cli",
            "approval-api-start",
            "--store",
            str(approval["store"]),
            "--host",
            str(approval["host"]),
            "--port",
            str(approval["port"]),
        ]
        launched.append(_launch("approval_api", command, repo, logs_dir))
    summary["launched"] = launched
    summary["logs_dir"] = str(logs_dir)
    return summary


def _launch(name: str, command: list[str], repo: Path, logs_dir: Path) -> dict[str, Any]:
    stdout_path = logs_dir / f"{name}.log"
    stderr_path = logs_dir / f"{name}.err.log"
    stdout = stdout_path.open("ab")
    stderr = stderr_path.open("ab")
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(command, cwd=repo, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, creationflags=creationflags)
    return {
        "name": name,
        "pid": process.pid,
        "command": command,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }
