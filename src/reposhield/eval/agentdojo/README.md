# AgentDojo Integration

This package maps AgentDojo tool calls into RepoShield semantic facts and guards
them with `RepoShieldToolGate`.

Key outputs:

- `agentdojo.*` facts in `policy_fact_set`
- `agentdojo_tool_gate_decision` audit events
- AgentDojo-compatible blocked results with `safe_to_continue=true`

