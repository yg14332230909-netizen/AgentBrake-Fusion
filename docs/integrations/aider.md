# Aider

## 一、适用场景

适用于 Aider 或类似 CLI coding agent 的本地试用。

## 二、一键接入命令

```bash
reposhield connect --agent aider --repo . --mode standard
reposhield start --repo .
```

## 三、Agent 侧配置

让 Aider 使用 OpenAI-compatible endpoint：

```text
OPENAI_BASE_URL=http://127.0.0.1:8765/v1
OPENAI_API_KEY=reposhield-local
```

## 四、如何验证成功

```bash
reposhield doctor --repo .
reposhield coverage --repo .
```

## 五、保护覆盖范围

Standard 模式覆盖模型响应、tool_calls 和常见命令 shim。

## 六、当前不能保护什么

Aider 的直接文件编辑路径若不经过 RepoShield file-guard，只能由 Gateway 侧证据和后续审计间接观察。

## 七、常见问题

保持稳定 `conversation_id`，可以让跨轮历史摘要连续积累。
