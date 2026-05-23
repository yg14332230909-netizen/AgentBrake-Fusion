# Codex CLI

## 一、适用场景

适用于支持 OpenAI-compatible endpoint 的 Codex CLI 或等价命令行 agent。

## 二、一键接入命令

```bash
reposhield connect --agent codex --repo . --mode standard
reposhield start --repo .
```

## 三、Agent 侧配置

使用 `.reposhield/agent.env` 中生成的 Gateway、run id 和 conversation id。

## 四、如何验证成功

运行 `reposhield doctor --repo .`，确认 Gateway、AuditLog、SessionState 和 shims 状态。

## 五、保护覆盖范围

Standard 模式适合本地开发试用；Full 模式适合演示和实验评测。

## 六、当前不能保护什么

未经过 Gateway 或 shims 的直接执行路径无法完整治理。

## 七、常见问题

如果 Gateway 返回 `X-RepoShield-Run-Id`，下一轮请求可以继续带回该值。
