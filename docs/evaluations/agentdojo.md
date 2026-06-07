# AgentDojo Evaluation

AgentBrake keeps AgentDojo as an optional evaluation adapter. The current recommended path is **AgentDojo Tool Firewall**, exposed as the `tool-firewall` mode.

## Layout

- Source adapter: `src/agentbrake/eval/agentdojo/`
- Tool firewall: `src/agentbrake/eval/agentdojo/gate/`
- Evidence, state, taxonomy, and fusion: `src/agentbrake/eval/agentdojo/evidence/`
- Runners: `src/agentbrake/eval/agentdojo/runner/`
- Experiments: `experiments/agentdojo/`
- Tests: `tests/eval/agentdojo/`
- Historical material: `experiments/agentdojo/archive/`

## Install

Base AgentBrake installation does not install AgentDojo or OpenAI:

```bash
pip install -e .
```

AgentDojo evaluation dependencies are optional:

```bash
pip install -e ".[agentdojo]"
```

## Modes

- `tool-firewall`: recommended AgentDojo Tool Firewall path. Tool calls are checked at the AgentDojo tool execution boundary.
- `baseline`: no AgentBrake defense.
- `gateway-only`: historical comparison baseline, retained for reports and comparison.

`ToolGate` is a legacy compatibility term. New code should use `AgentDojoToolFirewall`.

## Run

Minimal local smoke path:

```bash
python experiments/agentdojo/scripts/07_run_mini_benchmark.py
```

Runner module path:

```bash
python -m agentbrake.eval.agentdojo.runner.run_tool_firewall_eval --suite travel --model local --defense agentdojo_firewall --limit 1
```

Reports should be written under `experiments/agentdojo/reports/`.

## Historical Archive

Historical baselines and migrated artifacts live under `experiments/agentdojo/archive/`.
