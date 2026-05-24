# RepoShield 正式智能体接入指南

本文档对应 `reposhield connect / start / status / stop / doctor / smoke-test / coverage / profiles / integration-matrix`，用于把真实 coding agent 低摩擦接入 RepoShield。

## 三种接入模式

| 模式 | 适用场景 | 生成内容 |
| --- | --- | --- |
| Quick | 只需要 OpenAI-compatible Gateway 治理模型边界 | `.reposhield/config.yaml`、`agent.env`、agent instructions、Gateway 启动脚本 |
| Standard | 需要 Gateway + 常见 shell/file 工具治理 | Quick 内容 + `.reposhield/shims/*` 工具 shim |
| Full | 需要完整本地治理闭环 | Standard 内容 + Studio、Approval API、demo request |

## 标准流程

```bash
reposhield connect --repo . --agent codex --mode standard
reposhield start --repo .
reposhield status --repo .
reposhield doctor --repo . --agent codex
reposhield smoke-test --repo . --agent codex
```

停止：

```bash
reposhield stop --repo .
```

只查看计划，不启动服务：

```bash
reposhield start --repo . --print-only
```

## Agent Profile 化原则

新增或切换智能体时，差异必须优先进入 `src/reposhield/integration/profiles/*.yaml`：

- `wire_api`：`chat` 或 `responses`
- `api_key_env`：智能体侧读取的 API key 环境变量
- `config_files`：该智能体通常需要修改或参考的配置文件
- `config_apply`：`native`、`snippet` 或 `manual`
- `real_agent_command`：可选的真实 agent CLI smoke-test 命令
- `stable_identity_channels`：稳定身份传递方式

Gateway 核心只长期维护两个通用协议面：

- `/v1/chat/completions`
- `/v1/responses`

如果接入新智能体时需要修改 Gateway，应先判断它是否暴露的是通用 OpenAI-compatible 兼容性缺口，而不是给单个智能体写临时分支。

查看 profile：

```bash
reposhield profiles
reposhield profiles --agent codex
reposhield integration-matrix
```

## 本机智能体配置写入与恢复

默认 `connect` 只生成仓库内 `.reposhield` 文件，不修改真实智能体配置。

显式写入支持的本机配置：

```bash
reposhield connect --repo . --agent codex --mode standard --apply-agent-config
```

恢复：

```bash
reposhield connect --repo . --agent codex --restore-agent-config
```

Codex 当前是 `native` 写入；其他 OpenAI-compatible 智能体会生成 `.reposhield/agent-config/<agent>.env` 片段，供用户或上层工具接入。

## Smoke Test

只探测 RepoShield Gateway：

```bash
reposhield smoke-test --repo . --agent codex
```

按 profile 调用真实 agent CLI：

```bash
reposhield smoke-test --repo . --agent codex --real-agent
```

Codex profile 会使用 `/v1/responses`；generic / Cline / OpenHands / Aider 等默认使用 `/v1/chat/completions`。

## 多轮稳定身份要求

正式接入的多轮 agent 必须在每轮请求中稳定传入：

- `metadata.reposhield_run_id`
- `metadata.conversation_id`

可额外传入：

```text
X-RepoShield-Run-Id: run_xxxxxxxxxxxxxxxx
```

不要在同一任务中重新生成这些值。否则 RepoShield 无法把 PersistentSessionState、ActionGraph、secret taint、依赖风险和审批约束连续起来。

## doctor 修复提示

`doctor` 会检查：

- 配置文件是否存在
- agent profile 与配置中的协议是否一致
- audit 与 session state 目录是否可写
- 稳定 `run_id` / `conversation_id`
- Gateway / Studio 端口状态
- shims 是否存在以及是否在 PATH
- 按 agent profile 选择的 smoke endpoint 是否可用

失败项会带 `repair`，整体报告还会返回 `next_commands`，例如：

```json
{
  "next_commands": [
    "reposhield connect --repo . --agent codex --mode full --force",
    "reposhield start --repo . --gateway-only",
    "reposhield smoke-test --repo . --agent codex"
  ]
}
```

## 覆盖矩阵

```bash
reposhield coverage --repo .
```

覆盖矩阵用于确认 Quick / Standard / Full 对应能力是否已声明并能由本地文件系统验证。
