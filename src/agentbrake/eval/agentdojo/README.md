# AgentDojo Integration

This package maps AgentDojo tool calls into AgentBrake semantic facts and guards
them with `AgentBrakeToolGate`.

Key outputs:

- `agentdojo.*` facts in `policy_fact_set`
- `agentdojo_tool_gate_decision` audit events
- AgentDojo-compatible blocked results with `safe_to_continue=true`

