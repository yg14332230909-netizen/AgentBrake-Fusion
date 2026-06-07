# Cline

## 一、适用场景

适用于 Cline 使用 OpenAI-compatible endpoint，并希望 AgentBrake 管理模型响应和常见本地执行路径。

## 二、一键接入命令

```bash
agentbrake connect --agent cline --repo . --mode standard
agentbrake start --repo .
```

## 三、Agent 侧配置

将 Cline 的 API endpoint 指向 `http://127.0.0.1:8765/v1`，API key 使用 `agentbrake-local`。

## 四、如何验证成功

```bash
agentbrake doctor --repo .
```

## 五、保护覆盖范围

Standard 模式生成常见 shell、package、Python、Git、curl shims。请确保 `.agentbrake/shims` 位于 PATH 最前面。

## 六、当前不能保护什么

未走 shim 的 IDE 内部文件操作需要专用 adapter 或 file-guard 接入。

## 七、常见问题

多轮任务不要重置 run id；否则 SessionState 会被拆散。
