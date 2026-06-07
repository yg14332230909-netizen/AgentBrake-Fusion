#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

ATTACK_NAME="${ATTACK_NAME:-important_instructions}"
MODEL="${MODEL:-openai-api/deepseek/deepseek-chat}"
LIMIT="${LIMIT:-}"
mkdir -p experiments/agentdojo_toolgate/logs/agentbrake_toolgate experiments/agentdojo_toolgate/reports/runs

ARGS=(python -m agentbrake.eval.agentdojo.run_toolgate_eval
  --suite "${SUITE:-banking}" \
  --model "$MODEL" \
  --defense agentbrake_toolgate \
  --attack "$ATTACK_NAME" \
  --run-name agentbrake_toolgate_attack \
  --disable-invariants \
  --logdir experiments/agentdojo_toolgate/logs/agentbrake_toolgate \
  --report-dir experiments/agentdojo_toolgate/reports/runs)
if [[ -n "$LIMIT" ]]; then
  ARGS+=(--limit "$LIMIT")
fi
"${ARGS[@]}"
