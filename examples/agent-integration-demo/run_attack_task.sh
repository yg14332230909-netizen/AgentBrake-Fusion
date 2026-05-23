#!/usr/bin/env sh
set -eu

curl -sS http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer reposhield-local' \
  --data-binary @demo_repo/.reposhield/demo/attack_request.json
