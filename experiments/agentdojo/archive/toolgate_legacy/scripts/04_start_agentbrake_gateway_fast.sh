#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PORT="${GATEWAY_PORT:-8765}"
HOST="${GATEWAY_HOST:-127.0.0.1}"
AUDIT="experiments/agentdojo_toolgate/logs/agentbrake_gateway_only/gateway_audit.jsonl"
mkdir -p experiments/agentdojo_toolgate/logs/agentbrake_gateway_only

nohup python -m agentbrake.cli gateway-start \
  --repo "$ROOT" \
  --host "$HOST" \
  --port "$PORT" \
  --audit "$AUDIT" \
  --policy-mode enforce \
  --release-mode gateway_only \
  > experiments/agentdojo_toolgate/logs/agentbrake_gateway_only/gateway.stdout.log \
  2> experiments/agentdojo_toolgate/logs/agentbrake_gateway_only/gateway.stderr.log &

echo $! > experiments/agentdojo_toolgate/logs/agentbrake_gateway_only/gateway.pid
sleep 3
