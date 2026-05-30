> Deprecated.
>
> Use:
> - `src/reposhield/eval/agentdojo/`
> - `experiments/agentdojo/`
>
> This directory will be removed after compatibility migration.

# RepoShield AgentDojo ToolGate

这个实验不是 Gateway-only。Gateway 只能看模型响应链路，ToolGate 才是每个 AgentDojo tool call 真正执行前的拦截点。

## 关键点

- `Gateway-only`：模型响应先过 RepoShield Gateway，再由 AgentDojo 执行工具
- `ToolGate`：AgentDojo 的每一次 tool call 在 `FunctionsRuntime.run_function()` 前先过 RepoShield
- `AgentDojo` 评分仍然使用官方 `TaskSuite.run_task_with_pipeline()`，没有改 ground truth

## 运行方式

1. 先准备环境
   ```bash
   bash experiments/agentdojo_toolgate/scripts/00_setup_env.sh
   ```

2. 查看本地 AgentDojo 工具清单
   ```bash
   python experiments/agentdojo_toolgate/scripts/01_dump_agentdojo_tools.py
   ```

3. 跑最小实验
   ```bash
   bash experiments/agentdojo_toolgate/scripts/02_run_no_defense.sh
   bash experiments/agentdojo_toolgate/scripts/06_run_reposhield_toolgate.sh
   ```

4. 跑完整实验
   ```bash
   bash experiments/agentdojo_toolgate/scripts/run_all.sh
   ```

## 模型配置

脚本默认读取这些环境变量：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_API_BASE`
- `REPOSHIELD_LLM_PROVIDER`
- `REPOSHIELD_LLM_BASE_URL`

DeepSeek 可按 OpenAI-compatible 端点配置；如果走本地 Gateway，就把 `OPENAI_BASE_URL` 指到 Gateway 地址。

## 为什么要 ToolGate

Gateway-only 只能影响模型输出，不足以约束 AgentDojo 里后续的工具执行。RepoShield 要真正评测工具防御能力，必须在 `runtime.run_function()` 之前做判断。

## 输出

`reports/summary.md`、`reports/summary.json`、`reports/tool_inventory.md`、`reports/tool_coverage.json`、`reports/latency_profile.md`、`reports/reposhield_audit_check.md`

## 当前限制

- `workspace_plus` 不是当前安装版 AgentDojo 的 suite，当前代码按 `v1.2.2` 的 `banking/slack/workspace/travel` 适配
- AgentDojo 本身不支持自定义 defense registry，RepoShield 用 pipeline wrapper 接入
- `sandbox_then_approval` 在自动评测里会映射为安全拒绝，不会弹人工审批
