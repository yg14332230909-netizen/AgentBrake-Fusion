# Claude Code

## 一、适用场景

适用于可通过 OpenAI-compatible 中转层或自定义 provider 指向 RepoShield Gateway 的 Claude Code 类 agent。

## 二、一键接入命令

```bash
reposhield connect --agent claude-code --repo . --mode standard
reposhield start --repo .
```

## 三、Agent 侧配置

将模型请求送到 `http://127.0.0.1:8765/v1`，并在 metadata 中保留稳定 `reposhield_run_id` 和 `conversation_id`。

## 四、如何验证成功

```bash
reposhield doctor --repo .
```

## 五、保护覆盖范围

Standard 模式覆盖 Gateway 与常见本地执行 shim；Full 模式增加 Studio 和 Approval API。

## 六、当前不能保护什么

如果 agent 的 shell 或文件操作完全绕开 RepoShield shim / file-guard，需要额外 adapter 接入。

## 七、常见问题

若 doctor 显示 Gateway 未运行，请先运行 `.reposhield/scripts/run_gateway.sh` 或 `reposhield start --repo .`。
