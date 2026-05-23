# RepoShield Agent Integration Demo

This demo shows the simplified formal-agent integration flow:

```bash
reposhield connect --agent custom-openai --repo demo_repo --mode full --force
reposhield start --repo demo_repo
reposhield doctor --repo demo_repo
```

The generated Full-mode setup includes Gateway, shims, Studio, Approval API, audit paths, stable session identity, and demo request payloads.

## Files

- `demo_repo/`: small repository used as the protected target.
- `start_reposhield.sh`: generates Full-mode RepoShield integration files.
- `run_normal_task.sh`: sends a normal task through the Gateway.
- `run_attack_task.sh`: sends an attack-like task through the Gateway.
- `open_studio.md`: Studio URL and expected event flow.
- `expected_outputs/`: short descriptions of expected results.

## Run

```bash
cd examples/agent-integration-demo
sh start_reposhield.sh
sh run_attack_task.sh
```

Then open Studio at `http://127.0.0.1:8780`.
