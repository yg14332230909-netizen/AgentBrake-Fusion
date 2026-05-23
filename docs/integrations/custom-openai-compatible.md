# Custom OpenAI-Compatible Agent

## 一、适用场景

适用于任何可以配置 OpenAI-compatible `base_url`、`api_key` 和 request `metadata` 的 coding agent。

## 二、一键接入命令

```bash
reposhield connect --agent custom-openai --repo . --mode standard
reposhield start --repo .
reposhield doctor --repo .
```

## 三、Agent 侧配置

```text
base_url = http://127.0.0.1:8765/v1
api_key  = reposhield-local
```

每轮请求必须携带：

```json
{
  "metadata": {
    "reposhield_run_id": "<REPOSHIELD_RUN_ID>",
    "conversation_id": "<REPOSHIELD_CONVERSATION_ID>"
  }
}
```

## 四、如何验证成功

```bash
reposhield doctor --repo .
reposhield coverage --repo .
```

## 五、保护覆盖范围

Quick 保护模型响应和 OpenAI tool_calls；Standard 额外生成 shell、package、Python、Git、curl shims；Full 额外启用 Studio、Approval API 和 demo request。

## 六、当前不能保护什么

未通过 Gateway、shim、file-guard 或 MCPProxy 的直接系统调用无法被完整治理。

## 七、常见问题

如果 Studio 看不到同一任务的连续事件，优先检查每轮请求是否复用了稳定 `reposhield_run_id` 和 `conversation_id`。
