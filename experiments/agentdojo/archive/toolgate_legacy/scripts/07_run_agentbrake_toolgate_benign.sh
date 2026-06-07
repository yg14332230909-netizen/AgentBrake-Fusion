#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

MODEL="${MODEL:-openai-api/deepseek/deepseek-chat}"
LIMIT="${LIMIT:-}"
mkdir -p experiments/agentdojo_toolgate/logs/agentbrake_toolgate_benign experiments/agentdojo_toolgate/reports/runs

ARGS=(python -m agentbrake.eval.agentdojo.run_toolgate_eval
  --suite "${SUITE:-banking}" \
  --model "$MODEL" \
  --defense agentbrake_toolgate \
  --attack none \
  --run-name agentbrake_toolgate_benign \
  --disable-invariants \
  --logdir experiments/agentdojo_toolgate/logs/agentbrake_toolgate_benign \
  --report-dir experiments/agentdojo_toolgate/reports/runs)
if [[ -n "$LIMIT" ]]; then
  ARGS+=(--limit "$LIMIT")
fi
"${ARGS[@]}"
