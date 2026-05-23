# OpenHands

## 一、适用场景

适用于 OpenHands 通过 OpenAI-compatible Gateway 访问模型，并在本地演示 RepoShield 治理链路。

## 二、一键接入命令

```bash
reposhield connect --agent openhands --repo . --mode full
reposhield start --repo .
```

## 三、Agent 侧配置

配置模型 base URL 为 `http://127.0.0.1:8765/v1`，API key 为 `reposhield-local`。

## 四、如何验证成功

运行 `reposhield doctor --repo .` 并查看 Studio 的实时事件。

## 五、保护覆盖范围

Full 模式适合展示模型边界、执行边界、审批、审计和 Studio 可视化。

## 六、当前不能保护什么

OpenHands 如果通过容器内直接执行命令，需要在容器 PATH 中注入 `.reposhield/shims`。

## 七、常见问题

如果 doctor 提示 shims 不在 PATH，请把 `.reposhield/shims` 放在 PATH 最前面。
