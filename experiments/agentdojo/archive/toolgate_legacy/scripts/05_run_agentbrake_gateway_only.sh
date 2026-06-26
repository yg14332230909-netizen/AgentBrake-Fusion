#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

ATTACK_NAME="${ATTACK_NAME:-important_instructions}"
MODEL="${MODEL:-openai-api/deepseek/deepseek-chat}"
LIMIT="${LIMIT:-}"
PORT="${GATEWAY_PORT:-8765}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:${PORT}/v1}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-agentbrake-fusion-local}"
mkdir -p experiments/agentdojo_toolgate/logs/agentbrake_gateway_only experiments/agentdojo_toolgate/reports/runs

ARGS=(python -m agentbrake.eval.agentdojo.run_toolgate_eval
  --suite "${SUITE:-banking}" \
  --model "$MODEL" \
  --defense none \
  --attack "$ATTACK_NAME" \
  --run-name agentbrake_gateway_only_attack \
  --logdir experiments/agentdojo_toolgate/logs/agentbrake_gateway_only \
  --report-dir experiments/agentdojo_toolgate/reports/runs)
if [[ -n "$LIMIT" ]]; then
  ARGS+=(--limit "$LIMIT")
fi
"${ARGS[@]}"
