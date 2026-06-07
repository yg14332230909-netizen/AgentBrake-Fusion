# AgentDojo Evaluation

Recommended path:

```text
Tool-boundary AgentDojo Tool Firewall
```

Run:

```bash
python experiments/agentdojo/scripts/07_run_mini_benchmark.py
```

Historical baselines:

```text
experiments/agentdojo/archive/
```

`gateway-only` is a historical comparison baseline. `ToolGate` is legacy terminology; new code should use `AgentDojo Tool Firewall` and `tool-firewall`.

---

# AgentBrake-ADJ AgentDojo Tool Firewall

This is the recommended AgentDojo evaluation path.  It inserts AgentBrake at the
AgentDojo tool boundary rather than only in front of the model API.

```text
AgentDojo tool output -> sanitizer -> LLM -> tool call -> AgentBrake ToolGate -> original tool or safe blocked result
```

## Why this ActionGraph is different

This folder does not reuse the coding-agent shell ActionGraph as the AgentDojo
story.  AgentDojo is a tool benchmark, so the graph is a tool relation graph:

- untrusted tool output -> side-effecting tool call
- injection-like output -> high-risk tool call
- private data read -> external send/share
- private financial data -> financial commit
- attack-goal target -> current tool arguments

These edges are conservative security evidence, not exact program data-flow.

## Smoke test

```bash
pytest -q tests/eval/agentdojo/unit
python experiments/agentdojo/scripts/smoke_agentdojo_firewall.py
```

Expected behavior:

- authorized booking after benign reviews is allowed;
- malicious review causing wrong booking is blocked;
- private data followed by external email is blocked;
- unauthorized financial commit driven by untrusted output is blocked;
- read-only tools are allowed and update state.

## Do not delete old data

Do not delete the previous DeepSeek No Defense logs or reports.  They are needed
as baseline data.  If you reorganize the repository, move old files into:

```text
experiments/agentdojo/archive/deepseek_no_defense_baseline/
```

rather than deleting them.

