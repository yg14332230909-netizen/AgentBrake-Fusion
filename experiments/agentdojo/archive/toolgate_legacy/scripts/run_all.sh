#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

source experiments/agentdojo_toolgate/scripts/00_setup_env.sh

MODEL="${MODEL:-deepseek-chat}"
ATTACK_NAME="${ATTACK_NAME:-important_instructions}"
GATEWAY_PORT="${GATEWAY_PORT:-8765}"
GATEWAY_API_KEY="${AGENTBRAKE_GATEWAY_API_KEY:-agentbrake-fusion-local}"
UPSTREAM_BASE_URL="${OPENAI_BASE_URL:-https://api.deepseek.com/v1}"
UPSTREAM_API_KEY="${OPENAI_API_KEY:-}"
SUITES=("banking" "slack" "workspace" "travel")

mkdir -p experiments/agentdojo_toolgate/reports/runs

if [[ -z "$UPSTREAM_API_KEY" ]]; then
  echo "OPENAI_API_KEY is required for upstream DeepSeek access" >&2
  exit 1
fi

CURRENT_STEP=""
on_error() {
  local step="${CURRENT_STEP:-unknown}"
  local status=$?
  cat > "experiments/agentdojo_toolgate/reports/error_${step}.md" <<EOF
# Step Failed

- step: ${step}
- exit_status: ${status}
EOF
}
trap on_error ERR

run_step() {
  CURRENT_STEP="$1"
  shift
  echo "==> ${CURRENT_STEP}"
  "$@"
}

start_gateway() {
  local audit="experiments/agentdojo_toolgate/logs/agentbrake_gateway_only/gateway_audit.jsonl"
  mkdir -p experiments/agentdojo_toolgate/logs/agentbrake_gateway_only
  nohup python -m agentbrake.cli gateway-start \
    --repo "$ROOT" \
    --host 127.0.0.1 \
    --port "$GATEWAY_PORT" \
    --audit "$audit" \
    --policy-mode enforce \
    --upstream-base-url "$UPSTREAM_BASE_URL" \
    --upstream-api-key "$UPSTREAM_API_KEY" \
    --gateway-api-key "$GATEWAY_API_KEY" \
    --release-mode gateway_only \
    > experiments/agentdojo_toolgate/logs/agentbrake_gateway_only/gateway.stdout.log \
    2> experiments/agentdojo_toolgate/logs/agentbrake_gateway_only/gateway.stderr.log &
  echo $! > experiments/agentdojo_toolgate/logs/agentbrake_gateway_only/gateway.pid
  sleep 3
}

stop_gateway() {
  local pid_file="experiments/agentdojo_toolgate/logs/agentbrake_gateway_only/gateway.pid"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]]; then
      kill "$pid" || true
    fi
  fi
}

cleanup() {
  stop_gateway || true
}
trap cleanup EXIT

set_direct_env() {
  export OPENAI_BASE_URL="$UPSTREAM_BASE_URL"
  export OPENAI_API_KEY="$UPSTREAM_API_KEY"
  export AGENTBRAKE_OPENAI_COMPAT_SYSTEM_ROLE=1
}

set_gateway_env() {
  export OPENAI_BASE_URL="http://127.0.0.1:${GATEWAY_PORT}/v1"
  export OPENAI_API_KEY="$GATEWAY_API_KEY"
  export AGENTBRAKE_OPENAI_COMPAT_SYSTEM_ROLE=1
}

set_direct_env
run_step dump_tools python experiments/agentdojo_toolgate/scripts/01_dump_agentdojo_tools.py

for suite in "${SUITES[@]}"; do
  run_step "${suite}_no_defense" env ATTACK_NAME="$ATTACK_NAME" MODEL="$MODEL" SUITE="$suite" bash experiments/agentdojo_toolgate/scripts/02_run_no_defense.sh
  run_step "${suite}_tool_filter" env ATTACK_NAME="$ATTACK_NAME" MODEL="$MODEL" SUITE="$suite" bash experiments/agentdojo_toolgate/scripts/03_run_agentdojo_tool_filter.sh
done

start_gateway
set_gateway_env

for suite in "${SUITES[@]}"; do
  run_step "${suite}_gateway_only" env ATTACK_NAME="$ATTACK_NAME" MODEL="$MODEL" SUITE="$suite" bash experiments/agentdojo_toolgate/scripts/05_run_agentbrake_gateway_only.sh
  run_step "${suite}_toolgate" env ATTACK_NAME="$ATTACK_NAME" MODEL="$MODEL" SUITE="$suite" bash experiments/agentdojo_toolgate/scripts/06_run_agentbrake_toolgate.sh
  run_step "${suite}_toolgate_benign" env MODEL="$MODEL" SUITE="$suite" bash experiments/agentdojo_toolgate/scripts/07_run_agentbrake_toolgate_benign.sh
  run_step "${suite}_toolgate_no_taxonomy" env ATTACK_NAME="$ATTACK_NAME" MODEL="$MODEL" SUITE="$suite" python -m agentbrake.eval.agentdojo.run_toolgate_eval --suite "$suite" --model "$MODEL" --defense agentbrake_toolgate --attack "$ATTACK_NAME" --run-name "${suite}_agentbrake_toolgate_no_taxonomy_attack" --disable-taxonomy --logdir "experiments/agentdojo_toolgate/logs/agentbrake_toolgate_no_taxonomy/${suite}" --report-dir experiments/agentdojo_toolgate/reports/runs
  run_step "${suite}_toolgate_no_state_tracker" env ATTACK_NAME="$ATTACK_NAME" MODEL="$MODEL" SUITE="$suite" python -m agentbrake.eval.agentdojo.run_toolgate_eval --suite "$suite" --model "$MODEL" --defense agentbrake_toolgate --attack "$ATTACK_NAME" --run-name "${suite}_agentbrake_toolgate_no_state_tracker_attack" --disable-state-tracker --logdir "experiments/agentdojo_toolgate/logs/agentbrake_toolgate_no_state_tracker/${suite}" --report-dir experiments/agentdojo_toolgate/reports/runs
  run_step "${suite}_toolgate_no_invariants" env ATTACK_NAME="$ATTACK_NAME" MODEL="$MODEL" SUITE="$suite" python -m agentbrake.eval.agentdojo.run_toolgate_eval --suite "$suite" --model "$MODEL" --defense agentbrake_toolgate --attack "$ATTACK_NAME" --run-name "${suite}_agentbrake_toolgate_no_invariants_attack" --disable-invariants --logdir "experiments/agentdojo_toolgate/logs/agentbrake_toolgate_no_invariants/${suite}" --report-dir experiments/agentdojo_toolgate/reports/runs
  run_step "${suite}_full_fast" env ATTACK_NAME="$ATTACK_NAME" MODEL="$MODEL" SUITE="$suite" OPENAI_BASE_URL="http://127.0.0.1:${GATEWAY_PORT}/v1" OPENAI_API_KEY="$GATEWAY_API_KEY" python -m agentbrake.eval.agentdojo.run_toolgate_eval --suite "$suite" --model "$MODEL" --defense agentbrake_toolgate --attack "$ATTACK_NAME" --run-name "${suite}_full_agentbrake_fast_attack" --logdir "experiments/agentdojo_toolgate/logs/full_agentbrake_fast/${suite}" --report-dir experiments/agentdojo_toolgate/reports/runs
done

set_direct_env
run_step collect python experiments/agentdojo_toolgate/scripts/08_collect_results.py
run_step latency python experiments/agentdojo_toolgate/scripts/09_profile_latency.py
run_step stop_gateway bash experiments/agentdojo_toolgate/scripts/10_stop_agentbrake_gateway.sh
