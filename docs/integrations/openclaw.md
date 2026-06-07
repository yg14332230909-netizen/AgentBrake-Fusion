# OpenClaw

## 一、适用场景

适用于将 OpenClaw 的 OpenAI-compatible provider 指向 AgentBrake Gateway。

## 二、一键接入命令

```bash
agentbrake connect --agent openclaw --repo . --mode full
agentbrake start --repo .
agentbrake doctor --repo .
```

## 三、Agent 侧配置

使用 `.agentbrake/agent.env` 中的：

```text
OPENAI_BASE_URL=http://127.0.0.1:8765/v1
OPENAI_API_KEY=agentbrake-local
AGENTBRAKE_RUN_ID=...
AGENTBRAKE_CONVERSATION_ID=...
```

## 四、如何验证成功

运行 `agentbrake coverage --repo .`，再打开 Studio 查看 Gateway 事件、ActionIR、PolicyDecision 和审计轨迹。

## 五、保护覆盖范围

Full 模式覆盖 Gateway、常见执行 shim、Approval API、AuditLog、SessionState 和 Studio。

## 六、当前不能保护什么

OpenClaw 中绕过 provider 或绕过 PATH shim 的直接执行路径仍需要额外 adapter 接入。

## 七、常见问题

如果请求被拆成多轮，必须保持同一个 `metadata.agentbrake_run_id` 与 `metadata.conversation_id`。
