# RepoShield 正式智能体接入简化指南

本文档对应 `reposhield connect / start / doctor / coverage` 四个命令，用于把真实 coding agent 以低摩擦方式接入 RepoShield。

## 三种接入模式

| 模式 | 适用场景 | 生成内容 |
| --- | --- | --- |
| Quick | 只需要 OpenAI-compatible Gateway 拦截模型输出 | `.reposhield/config.yaml`、`agent.env`、agent instructions、Gateway 启动脚本 |
| Standard | 需要 Gateway + guarded shell/file 工具路径 | Quick 内容 + `.reposhield/shims/*` 工具 shim |
| Full | 需要完整本地治理闭环 | Standard 内容 + Studio、Approval API、demo request |

## 初始化

```bash
reposhield connect --repo . --agent codex --mode quick
reposhield connect --repo . --agent codex --mode standard --force
reposhield connect --repo . --agent openclaw --mode full --force
```

生成的关键文件：

- `.reposhield/config.yaml`：正式接入配置。
- `.reposhield/agent.env`：agent 侧环境变量。
- `.reposhield/agent-instructions.md`：给 agent 的接入说明。
- `.reposhield/scripts/run_gateway.sh` / `.ps1`：Gateway 启动脚本。
- `.reposhield/shims/*`：Standard / Full 模式下的 guarded tool shim。

## 启动计划

```bash
reposhield start --repo .
reposhield start --repo . --gateway-only
reposhield status --repo .
reposhield stop --repo .
```

`start` 会读取 `.reposhield/config.yaml`，后台启动 Gateway / Studio / Approval API，并输出服务 URL、进程 PID、日志路径、`run_id` 与 `conversation_id`。在 CI 或只想查看计划时，可以使用 `--print-only`。

`status` 会读取 `.reposhield/run/*.pid.json` 和端口状态，显示服务是否仍在运行。`stop` 会停止由 `start` 记录的后台服务，并清理 pid 文件。

## 体检与覆盖矩阵

```bash
reposhield doctor --repo .
reposhield coverage --repo .
```

`doctor` 检查配置、审计目录可写性、稳定会话身份、Gateway 配置、shim 目录与 PATH 状态。`coverage` 输出 Quick / Standard / Full 对应能力是否声明并可由本地文件系统验证。

每个失败检查都会包含 `repair` 字段，例如：

```json
{
  "name": "gateway_port_listening",
  "ok": false,
  "repair": "Start Gateway: reposhield start --repo . --gateway-only"
}
```

## 多轮 agent 稳定身份要求

正式接入的多轮 agent 必须在每一轮请求中传入稳定：

- `metadata.reposhield_run_id`
- `metadata.conversation_id`

也可以额外传入 HTTP header：

```text
X-RepoShield-Run-Id: run_xxxxxxxxxxxxxxxx
```

但 header 不能替代长期配置中的 `conversation_id`。同一次任务中重置这些值会切断 PersistentSessionState 与 ActionGraph 的连续性，使跨轮风险、secret taint、依赖风险和审批约束无法稳定累积。
