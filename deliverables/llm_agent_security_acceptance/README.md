# LLM Agent Security Deliverable Package

本目录是面向题目“红队视角下大语言模型与智能体应用攻击面研究及行为监督机制设计”的独立成果包。它把报告、对抗样本、攻击回放脚本、监督插件、模拟业务工具、模型过滤原型和实时监督端整理到一个目录中，便于验收、演示和二次开发。

## 一、快速运行

在仓库根目录执行：

```powershell
python deliverables\llm_agent_security_acceptance\scripts\run_all_attacks.py
```

运行后会生成：

- `runtime/audit_log.jsonl`：模型输入、工具调用、文件访问、代码执行、输出过滤的逐条审计记录。
- `runtime/alerts.jsonl`：告警和阻断记录。
- `runtime/summary.json`：各场景的 allow / ask / block 汇总。
- `runtime/mock_workspace/`：本地模拟业务工作区。

启动监督端页面：

```powershell
python deliverables\llm_agent_security_acceptance\prototype\realtime_dashboard.py --port 8899
```

然后打开 `http://127.0.0.1:8899` 查看近实时告警和阻断记录。

## 二、验收项映射

| 预期成果要求 | 本目录对应文件 |
| --- | --- |
| 安全风险分析报告 | `reports/security_risk_analysis.md` |
| 至少 3 类攻击场景 | `cases/adversarial_cases.jsonl` 中提供 5 类攻击场景和 1 个正常基线 |
| 模型对抗样本与越狱测试用例集 | `cases/adversarial_cases.jsonl`、`cases/jailbreak_test_cases.md` |
| 智能体攻击脚本 | `attack_scripts/*.py`、`scripts/run_case.py`、`scripts/run_all_attacks.py` |
| 行为监督原型系统 | `prototype/supervisor_plugin.py` |
| 拦截工具调用、代码执行、文件访问 | `prototype/mock_agent_app.py` 调用 `supervisor_plugin.py` 统一拦截 |
| 策略 allow / deny / ask 与异常检测 | `policies/supervisor_policy.json`、`prototype/filter_model.py` |
| 开源智能化应用接入示例，如 OpenClaw | `openclaw/README.md`、`openclaw/openclaw-provider-agentbrake-fusion.json` |
| 模拟业务工具 | `prototype/mock_business_tools.py`，包含发送邮件、读写文件、调用 API、记忆写入、代码执行模拟 |
| 模型调用链路安全监控插件 | `prototype/supervisor_plugin.py` 的 `MonitoringPlugin` |
| 基座模型检测或过滤原型 | `prototype/filter_model.py` |
| 监督端实时展示告警或阻断记录 | `prototype/realtime_dashboard.py` |

## 三、推荐演示流程

1. 先阅读 `reports/security_risk_analysis.md`，了解攻击面、风险链路和防御策略。
2. 执行 `python deliverables\llm_agent_security_acceptance\scripts\run_all_attacks.py` 生成审计记录。
3. 执行 `python deliverables\llm_agent_security_acceptance\prototype\realtime_dashboard.py --port 8899` 打开监督端。
4. 单独运行一个攻击场景，例如：

```powershell
python deliverables\llm_agent_security_acceptance\attack_scripts\attack_prompt_injection.py
python deliverables\llm_agent_security_acceptance\attack_scripts\attack_jailbreak_code_exec.py
python deliverables\llm_agent_security_acceptance\attack_scripts\attack_training_data_leak.py
```

5. 查看 `runtime/alerts.jsonl`，确认高危工具调用被阻断或转人工询问。

## 四、安全边界

本成果包中的攻击脚本都是本地 mock 回放：

- 邮件发送只写入 `runtime/outbox.jsonl`。
- API 调用只写入 `runtime/api_calls.jsonl`。
- 代码执行工具不执行真实任意代码，只做静态风险判断和模拟返回。
- 文件读写被限制在 `runtime/mock_workspace/` 内。
- 所有密钥、训练数据和泄露内容均为演示用 canary 字符串。

因此可以用于课堂、论文答辩、内网演示和策略调试，不会对真实系统产生外部影响。

## 五、与现有 AgentBrake-Fusion / AgentBrake-Fusion 的关系

本目录是一个独立可运行的验收包；仓库根目录已有更完整的 AgentBrake-Fusion 原型，包括 Gateway、PolicyGraph、Studio、OpenClaw 集成和 benchmark。当前成果包提取了题目要求的核心链路，便于评审快速复现：

```text
模型输入 -> 基座模型过滤 -> 智能体计划工具调用 -> 监督插件判定
        -> mock 工具执行或阻断 -> 输出过滤 -> JSONL 审计 -> 实时监督端
```

如需接入真实 OpenClaw，可参考 `openclaw/README.md`，让 OpenClaw 的 OpenAI-compatible provider 指向 AgentBrake-Fusion Gateway。
