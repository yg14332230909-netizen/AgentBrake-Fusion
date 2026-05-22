"""Session-level history summaries for cross-action policy evidence."""
from __future__ import annotations

from dataclasses import asdict

from .models import ActionIR, ExecTrace, PolicyDecision, SecretTaintEvent, SessionState, new_id, sha256_json


class SessionStateStore:
    def __init__(self) -> None:
        self._states: dict[str, SessionState] = {}

    def load(self, run_id: str, task_id: str | None = None) -> SessionState:
        state = self._states.get(run_id)
        if state is None:
            state = SessionState(new_id("state"), run_id, task_id)
            self._states[run_id] = _finalise(state)
        elif task_id and not state.task_id:
            state.task_id = task_id
            _finalise(state)
        return state

    def update(
        self,
        action: ActionIR,
        decision: PolicyDecision,
        trace: ExecTrace | None = None,
        secret_event: SecretTaintEvent | None = None,
        *,
        run_id: str,
        task_id: str | None = None,
    ) -> SessionState:
        state = self.load(run_id, task_id)
        if secret_event or action.semantic_action == "read_secret_file":
            state.secret_taint = True
            for asset in [*(action.affected_assets or []), secret_event.asset if secret_event else ""]:
                if asset:
                    state.touched_secret_assets.append(str(asset))
        if action.metadata.get("source_has_untrusted"):
            state.untrusted_source_seen = True
        if action.semantic_action in {"install_git_dependency", "install_tarball_dependency", "install_registry_dependency"}:
            state.package_taint = True
        if action.semantic_action == "modify_ci_pipeline":
            state.ci_taint = True
        if action.semantic_action == "send_network_request":
            state.prior_external_sinks.extend(str(item) for item in action.affected_assets if item)
        if trace:
            state.prior_external_sinks.extend(str(item.get("host") or item.get("url") or item) for item in trace.network_attempts)
        state.last_decisions.append(decision.decision)
        state.touched_secret_assets = list(dict.fromkeys(state.touched_secret_assets))[-20:]
        state.prior_external_sinks = list(dict.fromkeys(state.prior_external_sinks))[-20:]
        state.last_decisions = state.last_decisions[-20:]
        return _finalise(state)


def session_state_payload(state: SessionState) -> dict:
    payload = asdict(state)
    payload["touched_secret_assets"] = [str(item) for item in state.touched_secret_assets]
    payload["prior_external_sinks"] = [str(item) for item in state.prior_external_sinks]
    return payload


def _finalise(state: SessionState) -> SessionState:
    payload = asdict(state)
    payload.pop("state_hash", None)
    state.state_hash = sha256_json(payload)
    return state
