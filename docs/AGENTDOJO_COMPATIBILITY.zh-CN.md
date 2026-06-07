# AgentBrake AgentDojo Compatibility

AgentBrake 现在支持三层 AgentDojo 接入：

1. Gateway-only Fast Mode，用于快速验证网关兼容性。
2. `AgentBrakeToolGate`，用于在工具执行前裁决。
3. `agentbrake_agentdojo` / `agentbrake_toolgate`，用于 Inspect 或原生 AgentDojo 的对接入口。

关键能力：

- `agentdojo_tool_taxonomy.yaml` 提供官方工具到 `semantic_action` 的映射
- `AgentDojoStateTracker` 维护 `untrusted_observation_seen`、`private_data_seen`、`financial_data_seen`
- `agentdojo.*` facts 与 `source.has_untrusted` 桥接，避免不可信事实断裂
- `performance_trace`、buffered audit、summary evidence graph 支持评测降延迟

报告建议同时输出：

- `registered_tool_rate`
- `unknown_tool_rate`
- `tool_gate_call_count`
- `blocked_tool_call_count`
- `untrusted_observation_seen_count`
- `private_data_seen_count`
- `agentdojo_invariant_hit_count`
- `policy_latency_p95`

