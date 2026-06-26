# AgentBrake-Fusion AgentDojo Experiments

This directory contains the recommended AgentDojo experiment workflow for agentbrake. The experiments use the prototype under `src/agentbrake/eval/agentdojo` and evaluate safety judgments at the general agent tool boundary.

## Recommended Path

```text
AgentDojo tool output
  -> agent reasoning step
  -> candidate tool call
  -> AgentBrake-Fusion tool boundary
  -> ActionGraph
  -> MSJ Engine
  -> Constraint Product Lattice
  -> allow / confirm / quarantine / block
  -> BrakeTrace
```

## Quick Validation

```bash
pytest -q tests/eval/agentdojo/unit
python experiments/agentdojo/scripts/smoke_agentdojo_firewall.py
```

Expected behavior:

- Authorized benign actions remain executable.
- Untrusted or injection-like output influencing risky side effects is blocked or requires confirmation.
- Private data flowing toward external sinks is blocked or requires confirmation.
- High-impact financial or membership mutations require task authorization.
- Read-only tools remain available and update the state tracker.

## Mini Benchmark

```bash
python experiments/agentdojo/scripts/07_run_mini_benchmark.py --suites travel banking --limit 2
```

Outputs:

```text
experiments/agentdojo/reports/mini_benchmark.json
experiments/agentdojo/reports/mini_benchmark.md
experiments/agentdojo/logs/
```

## Paired Comparison

Generate the plan first:

```bash
python experiments/agentdojo/scripts/12_run_paired_mini.py --dry-run
```

Run the paired comparison:

```bash
python experiments/agentdojo/scripts/12_run_paired_mini.py
```

The paired workflow compares baseline methods against the AgentBrake-Fusion tool-boundary judgment path using a shared manifest.

## Ablation Profiles

Ablation profiles are defined in `src/agentbrake/eval/agentdojo/compat/types.py` and are used to study how much each evidence source contributes:

- `rule_only`
- `no_binding`
- `no_recovery_guidance`
- `flatten_action_graph`
- `no_actiongraph_provenance_edges`
- `no_actiongraph_dataflow_edges`
- `no_actiongraph_history_edges`

## Historical Data

Historical baselines are kept under:

```text
experiments/agentdojo/archive/
```

Keep historical baselines separate from new agentbrake runs so current reports remain easy to interpret.

