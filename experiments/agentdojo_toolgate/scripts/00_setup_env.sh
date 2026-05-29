#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

python -m pip install "inspect-evals[agentdojo]" agentdojo

export REPOSHIELD_EVAL_FAST_MODE="${REPOSHIELD_EVAL_FAST_MODE:-1}"
export REPOSHIELD_DISABLE_STUDIO_EVENTS="${REPOSHIELD_DISABLE_STUDIO_EVENTS:-1}"
export REPOSHIELD_AUDIT_BUFFERED="${REPOSHIELD_AUDIT_BUFFERED:-1}"
export REPOSHIELD_EVIDENCE_GRAPH_MODE="${REPOSHIELD_EVIDENCE_GRAPH_MODE:-summary}"
export REPOSHIELD_POLICY_TRACE_MODE="${REPOSHIELD_POLICY_TRACE_MODE:-summary}"
export REPOSHIELD_DISABLE_PREFLIGHT="${REPOSHIELD_DISABLE_PREFLIGHT:-1}"
export REPOSHIELD_SESSION_CACHE="${REPOSHIELD_SESSION_CACHE:-1}"

mkdir -p experiments/agentdojo_toolgate/logs
mkdir -p experiments/agentdojo_toolgate/reports
