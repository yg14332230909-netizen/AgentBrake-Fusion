"""Implementation of ``reposhield doctor``."""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .coverage import build_coverage_report, filesystem_checks
from .templates import load_config


@dataclass(slots=True)
class DoctorReport:
    ok: bool
    config_path: str
    checks: list[dict[str, Any]]
    coverage: dict[str, Any]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "config_path": self.config_path,
            "checks": self.checks,
            "coverage": self.coverage,
            "warnings": self.warnings,
        }


def run_doctor(repo_root: str | Path, *, config_path: str | Path | None = None) -> DoctorReport:
    repo = Path(repo_root).resolve()
    config_file = Path(config_path).resolve() if config_path else repo / ".reposhield" / "config.yaml"
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    if not config_file.exists():
        return DoctorReport(
            False,
            str(config_file),
            [
                {
                    "name": "config",
                    "ok": False,
                    "detail": "missing config.yaml",
                    "repair": "Run: reposhield connect --repo . --agent custom-openai --mode quick",
                }
            ],
            {},
            warnings,
        )
    config = load_config(config_file)
    _check(checks, "config", True, str(config_file))
    audit_path = Path(str(config.get("audit", {}).get("path", repo / ".reposhield" / "gateway_audit.jsonl")))
    _check(checks, "audit_dir_writable", _is_writable(audit_path.parent), str(audit_path.parent))
    session_path = Path(str(config.get("session", {}).get("state_path", repo / ".reposhield" / "session_state.jsonl")))
    _check(checks, "session_state_writable", _is_writable(session_path.parent), str(session_path))
    session = config.get("session", {})
    has_stable_identity = bool(session.get("run_id") and session.get("conversation_id"))
    _check(checks, "stable_run_identity", has_stable_identity, "run_id and conversation_id are required")
    if not str(session.get("run_id") or "").startswith("run_"):
        warnings.append("session run_id does not use the expected run_ prefix")
    shims = config.get("shims", {})
    if shims.get("enabled"):
        shim_path = Path(str(shims.get("path", "")))
        _check(checks, "shims_exist", shim_path.exists(), str(shim_path))
        _check(checks, "shims_on_path", _path_contains(shim_path), str(shim_path))
        if not _path_first(shim_path):
            warnings.append(f"shim path is not first on PATH: {shim_path}")
        elif not _path_contains(shim_path):
            warnings.append(f"shim path is not on PATH: {shim_path}")
    gateway = config.get("gateway", {})
    _check(checks, "gateway_configured", bool(gateway.get("enabled") and gateway.get("port")), str(gateway))
    gateway_host = str(gateway.get("host") or "127.0.0.1")
    gateway_port = int(gateway.get("port") or 0)
    gateway_listening = _port_open(gateway_host, gateway_port)
    _check(checks, "gateway_port_listening", gateway_listening, "warning-only")
    if gateway_listening:
        _check(checks, "gateway_chat_completions", _probe_gateway(gateway_host, gateway_port, session), "/v1/chat/completions")
    if gateway.get("upstream_base_url") and not os.getenv("OPENAI_API_KEY"):
        warnings.append("OPENAI_API_KEY is not set; upstream forwarding may fail")
    policy_pack = str(config.get("policy", {}).get("pack") or "")
    if policy_pack:
        _check(checks, "policy_pack_exists", Path(policy_pack).exists(), policy_pack)
    studio = config.get("studio", {})
    if studio.get("enabled"):
        studio_host = str(studio.get("host") or "127.0.0.1")
        studio_port = int(studio.get("port") or 0)
        studio_listening = _port_open(studio_host, studio_port)
        _check(checks, "studio_port_listening", studio_listening, "warning-only")
        if studio_listening:
            _check(checks, "studio_health", _probe_studio(studio_host, studio_port), "/api/health")
    coverage = build_coverage_report(config, filesystem_checks(config))
    hard_checks = [
        item
        for item in checks
        if item["name"]
        not in {"gateway_port_listening", "gateway_chat_completions", "studio_port_listening", "studio_health", "shims_on_path"}
    ]
    ok = all(item["ok"] for item in hard_checks) and bool(coverage.get("ok"))
    return DoctorReport(ok, str(config_file), checks, coverage, warnings)


def _check(checks: list[dict[str, Any]], name: str, ok: bool, detail: str) -> None:
    item = {"name": name, "ok": bool(ok), "detail": detail}
    repair = _repair_hint(name, ok, detail)
    if repair:
        item["repair"] = repair
    checks.append(item)


def _repair_hint(name: str, ok: bool, detail: str) -> str:
    if ok:
        return ""
    hints = {
        "config": "Run: reposhield connect --repo . --agent custom-openai --mode quick",
        "audit_dir_writable": f"Create or fix permissions for: {detail}",
        "session_state_writable": f"Create or fix permissions for: {detail}",
        "stable_run_identity": "Regenerate config: reposhield connect --repo . --mode quick --force",
        "shims_exist": "Regenerate shims: reposhield connect --repo . --mode standard --force",
        "shims_on_path": 'Put shims first: export PATH="$(pwd)/.reposhield/shims:$PATH"',
        "gateway_configured": "Regenerate config: reposhield connect --repo . --mode quick --force",
        "gateway_port_listening": "Start Gateway: reposhield start --repo . --gateway-only",
        "gateway_chat_completions": "Check logs in .reposhield/logs/gateway.err.log and verify Authorization uses Bearer reposhield-local.",
        "policy_pack_exists": f"Fix --policy-pack path or remove it from config: {detail}",
        "studio_port_listening": "Start Studio: reposhield start --repo .",
        "studio_health": "Check logs in .reposhield/logs/studio.err.log and verify Studio bearer token.",
    }
    return hints.get(name, "Inspect this check and rerun: reposhield doctor --repo .")


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".reposhield_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _path_contains(path: Path) -> bool:
    wanted = str(path.resolve()).lower()
    return any(str(Path(part).resolve()).lower() == wanted for part in os.environ.get("PATH", "").split(os.pathsep) if part)


def _path_first(path: Path) -> bool:
    parts = [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]
    if not parts:
        return False
    try:
        return str(Path(parts[0]).resolve()).lower() == str(path.resolve()).lower()
    except OSError:
        return False


def _port_open(host: str, port: int) -> bool:
    if port <= 0:
        return False
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def _probe_gateway(host: str, port: int, session: dict[str, Any]) -> bool:
    payload = {
        "model": "reposhield/local-heuristic",
        "messages": [{"role": "user", "content": "reposhield doctor connectivity check"}],
        "metadata": {
            "reposhield_run_id": session.get("run_id"),
            "conversation_id": session.get("conversation_id"),
            "client_id": "reposhield-doctor",
        },
    }
    try:
        request = Request(
            f"http://{host}:{port}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer reposhield-local"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            return response.status == 200 and bool(response.headers.get("X-RepoShield-Run-Id"))
    except (HTTPError, URLError, OSError):
        return False


def _probe_studio(host: str, port: int) -> bool:
    try:
        request = Request(
            f"http://{host}:{port}/api/health",
            headers={"Authorization": "Bearer reposhield-local"},
            method="GET",
        )
        with urlopen(request, timeout=2) as response:
            return response.status == 200
    except (HTTPError, URLError, OSError):
        return False
