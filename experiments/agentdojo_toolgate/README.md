# AgentDojo ToolGate Experiment

This experiment mode routes AgentDojo tool calls through `RepoShieldToolGate`
before execution. `allow` decisions execute the original tool call. `block`,
`quarantine`, and `sandbox_then_approval` return an AgentDojo-compatible blocked
result with `safe_to_continue=true` and do not mutate the environment.

Recommended environment:

```bash
REPOSHIELD_EVAL_FAST_MODE=1
REPOSHIELD_DISABLE_PREFLIGHT=1
REPOSHIELD_POLICY_TRACE_MODE=summary
REPOSHIELD_EVIDENCE_GRAPH_MODE=summary
```
