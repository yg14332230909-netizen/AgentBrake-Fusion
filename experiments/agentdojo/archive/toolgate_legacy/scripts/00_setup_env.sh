#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

python -m pip install "inspect-evals[agentdojo]" agentdojo

export AGENTBRAKE_EVAL_FAST_MODE="${AGENTBRAKE_EVAL_FAST_MODE:-1}"
export AGENTBRAKE_DISABLE_STUDIO_EVENTS="${AGENTBRAKE_DISABLE_STUDIO_EVENTS:-1}"
export AGENTBRAKE_AUDIT_BUFFERED="${AGENTBRAKE_AUDIT_BUFFERED:-1}"
export AGENTBRAKE_EVIDENCE_GRAPH_MODE="${AGENTBRAKE_EVIDENCE_GRAPH_MODE:-summary}"
export AGENTBRAKE_POLICY_TRACE_MODE="${AGENTBRAKE_POLICY_TRACE_MODE:-summary}"
export AGENTBRAKE_DISABLE_PREFLIGHT="${AGENTBRAKE_DISABLE_PREFLIGHT:-1}"
export AGENTBRAKE_SESSION_CACHE="${AGENTBRAKE_SESSION_CACHE:-1}"

mkdir -p experiments/agentdojo_toolgate/logs
mkdir -p experiments/agentdojo_toolgate/reports
