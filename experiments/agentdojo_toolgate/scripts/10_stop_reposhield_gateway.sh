#!/usr/bin/env bash
set -euo pipefail

PID_FILE="experiments/agentdojo_toolgate/logs/reposhield_gateway_only/gateway.pid"
if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if [[ -n "$PID" ]]; then
    kill "$PID" || true
  fi
  rm -f "$PID_FILE"
fi
