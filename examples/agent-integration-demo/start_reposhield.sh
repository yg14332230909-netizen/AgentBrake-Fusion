#!/usr/bin/env sh
set -eu

reposhield connect --agent custom-openai --repo demo_repo --mode full --force
reposhield start --repo demo_repo
reposhield doctor --repo demo_repo
