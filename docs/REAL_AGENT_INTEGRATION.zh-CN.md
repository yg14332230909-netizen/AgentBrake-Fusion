# 真实 Agent 接入指南

本文面向第一次接触 AgentBrake 的使用者，解释它如何插入真实 coding agent，以及当前能跑到什么程度。

## 一句话理解

AgentBrake 不是装进 agent 内部的插件，而是放在 agent 和模型 API / 工具执行之间的安全层：

```text
真实 agent
  -> AgentBrake Gateway
  -> 真实 OpenAI-compatible upstream
  -> 模型返回 assistant message / tool_calls
  -> AgentBrake 解析 InstructionIR / ActionIR
  -> PolicyRuntime 判断 allow / sandbox / approval / block
  -> 安全响应返回给 agent
```

如果 agent 支持 OpenAI-compatible `base_url`，通常只需要把它原来的模型地址改成 AgentBrake 本地地址。

## 方式一：Gateway 接入

启动 Gateway：

```bash
export OPENAI_API_KEY=sk-...

PYTHONPATH=src python -m agentbrake gateway-start \
  --repo ./your-repo \
  --host 127.0.0.1 \
  --port 8765 \
  --upstream-base-url https://api.openai.com/v1
```

agent 侧配置：

```text
base_url = http://127.0.0.1:8765/v1
api_key  = agentbrake-local
model    = gpt-4.1
```

`api_key` 在本地 Gateway 侧只用于兼容 agent；真实上游密钥来自 `OPENAI_API_KEY` 或 `--upstream-api-key`。

如果上游不是 OpenAI，而是其他 OpenAI-compatible 服务，需要把 `--upstream-base-url` 改成对应平台的地址。例如 LongCat：

```bash
export OPENAI_API_KEY=ak-your-longcat-key

PYTHONPATH=src python -m agentbrake gateway-start \
  --repo ./your-repo \
  --host 127.0.0.1 \
  --port 8765 \
  --upstream-base-url https://api.longcat.chat/openai
```

OpenClaw 侧仍然只配置 AgentBrake 本地地址：

```text
base_url = http://127.0.0.1:8765/v1
api_key  = agentbrake-local
model    = LongCat-Flash-Chat
```

可以用一条命令生成 OpenClaw provider 和启动脚本：

```bash
PYTHONPATH=src python -m agentbrake openclaw-quickstart \
  --repo ./your-repo \
  --agentbrake-home . \
  --model LongCat-Flash-Chat \
  --upstream-base-url https://api.longcat.chat/openai
```

## 方式二：exec-guard 接入 shell

## 多轮 Agent 必须传入稳定身份

如果 agent 会把一个任务拆成多轮模型请求，请务必在每轮 OpenAI-compatible request 中传入稳定的 `metadata.agentbrake_run_id`，或至少传入稳定的 `metadata.conversation_id` / `metadata.thread_id` / `metadata.session_id`。AgentBrake 会用它恢复跨请求历史摘要，例如 attempted / confirmed secret taint、package taint、CI taint 和 prior external sinks。

推荐：

```json
{
  "metadata": {
    "agentbrake_run_id": "run_login_fix_001",
    "conversation_id": "conv_login_fix_001"
  }
}
```

不要只依赖每轮都会变化的 `request_id`。没有稳定身份时，Gateway 仍会兼容处理请求，但无法保证多轮历史自动合并到同一个 SessionState。

如果 agent 会直接运行 shell 命令，把命令包进：

```bash
PYTHONPATH=src python -m agentbrake exec-guard \
  --repo ./your-repo \
  --task "fix login and run tests" \
  -- npm test
```

危险命令会被阻断；普通允许命令会执行；`allow_in_sandbox` 会走 sandbox preflight。

## 方式三：init-agent 一键初始化

```bash
PYTHONPATH=src python -m agentbrake init-agent \
  --repo ./your-repo \
  --agent cline \
  --task "fix login and run tests"
```

它会生成：

```text
.agentbrake/config.json
.agentbrake/agent-instructions.md
.agentbrake/shims/npm
.agentbrake/shims/git
.agentbrake/shims/curl
.agentbrake/shims/python
.agentbrake/shims/*.ps1
```

把 `.agentbrake/shims` 放到 PATH 前面后，常用命令会先经过 `exec-guard`。

## 文件动作治理

`file-guard` 用来治理 agent 的读写删改：

```bash
PYTHONPATH=src python -m agentbrake file-guard \
  --repo ./your-repo \
  --task "fix login and run tests" \
  --operation edit \
  --path .github/workflows/release.yml \
  --source-file ./issue.md
```

这适合接到真实 agent 的 file tool adapter 前面。

## 审批闭环

审批事件持久化在 JSONL：

```bash
PYTHONPATH=src python -m agentbrake approvals list \
  --store ./your-repo/.agentbrake/approvals.jsonl

PYTHONPATH=src python -m agentbrake approvals approve <approval_request_id> \
  --store ./your-repo/.agentbrake/approvals.jsonl \
  --granted-by alice

PYTHONPATH=src python -m agentbrake approvals deny <approval_request_id> \
  --store ./your-repo/.agentbrake/approvals.jsonl \
  --denied-by alice
```

当前是 CLI 闭环，不是完整 Web 审批产品。

## Policy YAML

```yaml
rules:
  - name: block_ci_from_issue
    match:
      operation: edit
      file_path: .github/workflows/release.yml
    decision: block
    reason: configured_ci_protection
```

使用：

```bash
PYTHONPATH=src python -m agentbrake gateway-start \
  --repo ./your-repo \
  --upstream-base-url https://api.openai.com/v1 \
  --policy-config ./agentbrake-policy.yaml
```

## Streaming 状态

Gateway 已支持 agent 侧 `stream=true`，并返回 OpenAI-compatible `text/event-stream`。

真实 upstream streaming 现在会被 AgentBrake 内部消费和聚合：`delta.content` 与 `delta.tool_calls` 会先组合成完整 assistant message，再进入治理流程。治理完成后，Gateway 再把安全响应以 SSE 返回给 agent。

这解决了很多真实 agent 喜欢 streaming 的兼容问题，但仍不是 token-by-token 透传。原因是 AgentBrake 不能在 tool call 尚未完整识别前，把未治理的 delta 直接放给 agent 执行。

## 当前边界

已经能做真实小范围试接：

- Gateway 指向真实 OpenAI-compatible upstream
- OpenAI tool calls 治理
- exec-guard 包 shell
- file-guard 包文件动作
- init-agent 生成 shims
- approvals CLI 闭环
- Studio Pro 实时查看 audit / approvals、证据图谱、策略调试、沙箱证据和人工审批

仍需继续做：

- 更完整的 Cline / Codex / OpenHands / Claude Code / Aider adapter
- 更强 shell parser 和脚本间接执行识别
- 真正隔离的 sandbox
- 团队策略、权限模型、持久权限记忆和生产级审计存储
- token-by-token streaming governance
