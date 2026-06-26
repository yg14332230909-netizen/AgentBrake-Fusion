# OpenClaw Integration Note

本成果包中的 mock 智能体用于本地可复现实验。真实开源智能化应用可采用 OpenClaw，接入方式是把 OpenClaw 的 OpenAI-compatible provider 指向 AgentBrake-Fusion Gateway，让模型请求、工具调用和审计链路进入统一监督面。

## 1. AgentBrake-Fusion Gateway 启动示例

在仓库根目录执行：

```powershell
$env:PYTHONPATH="src"
python -m agentbrake gateway-start --repo . --host 127.0.0.1 --port 8765 --upstream-base-url https://api.openai.com/v1
```

实际使用时需要在环境变量中配置真实上游模型密钥。验收演示不需要真实 OpenClaw 和真实上游模型，可以直接运行本目录的 mock 原型。

## 2. OpenClaw Provider 配置

把 `openclaw-provider-agentbrake-fusion.json` 中的 provider 加入 OpenClaw 配置：

```text
Base URL: http://127.0.0.1:8765/v1
API Key:  agentbrake-fusion-local
Model:    gpt-4.1 via AgentBrake-Fusion
```

## 3. 监控覆盖

OpenClaw 侧的模型调用先进入 AgentBrake-Fusion Gateway；工具调用和业务工具再通过监督插件或 adapter 映射成结构化 ActionIR。本成果包中的 `prototype/supervisor_plugin.py` 展示了最小可落地接口：

- `on_model_input`
- `before_tool_call`
- `after_tool_call`
- `on_model_output`

这四个 hook 对应模型输入过滤、工具执行前拦截、工具结果审计和输出过滤。
