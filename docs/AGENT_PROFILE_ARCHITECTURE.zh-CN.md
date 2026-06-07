# 智能体接入 Profile 架构

AgentBrake 的正式接入原则是：新增或切换智能体时，优先新增或调整 agent profile 和文档模板，不为单个智能体修改 Gateway 核心逻辑。

## Profile 负责什么

每个智能体的差异集中在 `src/agentbrake/integration/profiles/*.yaml`，Python 代码只保留兜底 profile：

- `wire_api`：使用 `chat` 还是 `responses`
- `api_key_env`：智能体侧读取哪个环境变量
- `stable_identity_channels`：如何传入稳定 `run_id` / `conversation_id`
- `config_files`：该智能体通常需要改哪些配置文件
- `config_apply`：原生写入、片段生成还是手动接入
- `real_agent_command`：真实 agent CLI smoke-test 命令
- `smoke_endpoint`：doctor / smoke-test 应该探测哪个端点

Gateway 只长期维护 OpenAI-compatible 协议面：

- `/v1/chat/completions`
- `/v1/responses`

如果某个新智能体接入时需要修改 Gateway，默认视为通用兼容性缺口，应先判断能否通过 profile 或模板解决。

## 标准接入流程

```bash
agentbrake connect --repo . --agent codex --mode standard
agentbrake start --repo .
agentbrake doctor --repo . --agent codex
agentbrake smoke-test --repo . --agent codex
```

查看当前 profile：

```bash
agentbrake profiles
agentbrake profiles --agent codex
agentbrake integration-matrix
```

真实 agent CLI smoke-test：

```bash
agentbrake smoke-test --repo . --agent codex --real-agent
```

显式写入支持的本机智能体配置：

```bash
agentbrake connect --repo . --agent codex --mode standard --apply-agent-config
```

恢复本机智能体配置：

```bash
agentbrake connect --repo . --agent codex --restore-agent-config
```

## 多轮稳定身份要求

所有多轮 agent 必须在每轮请求中稳定传入：

- `metadata.agentbrake_run_id`
- `metadata.conversation_id`

可额外传入：

- `X-AgentBrake-Run-Id`

不要在同一任务中重新生成这些值。否则 AgentBrake 无法把 PersistentSessionState、ActionGraph、secret taint 和审批约束串起来。

## 新增智能体检查清单

1. 在 `src/agentbrake/integration/profiles/<agent>.yaml` 中增加 profile。
2. 声明 `wire_api`，只能选择 `chat` 或 `responses`。
3. 增加 `docs/integrations/<agent>.md`。
4. 增加或复用 smoke-test。
5. 运行：

```bash
agentbrake connect --repo . --agent <agent> --mode quick --dry-run
agentbrake doctor --repo . --agent <agent>
agentbrake smoke-test --repo . --agent <agent>
```

若以上流程需要改 Gateway，说明该智能体暴露了新的通用协议兼容问题，需要先抽象成 OpenAI-compatible 能力。
