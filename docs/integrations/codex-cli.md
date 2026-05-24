# Codex CLI 接入 RepoShield

Codex CLI 的接入差异由 agent profile 描述，不需要为 Codex 修改 Gateway 核心代码。

## 一键生成

```bash
reposhield connect --agent codex --repo . --mode standard
reposhield start --repo .
reposhield doctor --repo . --agent codex
```

Codex profile 的关键声明：

- `wire_api: responses`
- Gateway endpoint: `/v1/responses`
- API key env: `REPOSHIELD_GATEWAY_API_KEY`
- 稳定 run id header: `X-RepoShield-Run-Id`
- 多轮稳定身份仍建议同时保留 `metadata.reposhield_run_id` 和 `metadata.conversation_id`

## 可选：让 RepoShield 写入 Codex 配置

只有在你明确希望 RepoShield 修改本机 Codex 配置时才运行：

```bash
reposhield connect --agent codex --repo . --mode standard --apply-agent-config
```

该命令会创建备份清单。恢复：

```bash
reposhield connect --agent codex --repo . --restore-agent-config
```

## Smoke Test

Gateway 已启动后可运行：

```bash
reposhield connect --agent codex --repo . --mode standard --smoke-test
```

或：

```bash
reposhield doctor --repo . --agent codex
reposhield smoke-test --repo . --agent codex
```

doctor 会按 Codex profile 探测 `/v1/responses`，而不是默认探测 `/v1/chat/completions`。

## 新增其他智能体时的边界

如果更换智能体后发现需要改 Gateway，先不要直接为该智能体写特殊分支。应先检查：

1. 该智能体实际使用 `chat` 还是 `responses`。
2. 是否只是 API key、base URL、header 或 metadata 传递方式不同。
3. 能否通过 `src/reposhield/integration/profiles.py` 增加 profile 解决。

只有当它暴露出新的通用 OpenAI-compatible 协议兼容问题时，才应扩展 Gateway。
