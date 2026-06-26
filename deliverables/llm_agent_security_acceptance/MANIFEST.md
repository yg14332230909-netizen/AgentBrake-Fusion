# File Manifest

## 文档

- `README.md`：成果包说明书、验收项映射和运行方法。
- `MANIFEST.md`：本文件，列出目录内容。
- `reports/security_risk_analysis.md`：安全风险分析报告，覆盖 5 类攻击场景、对抗样本、攻击脚本和防御策略。
- `cases/jailbreak_test_cases.md`：越狱与对抗测试用例说明。
- `openclaw/README.md`：OpenClaw 接入 AgentBrake-Fusion / 本原型的说明。

## 样本与策略

- `cases/adversarial_cases.jsonl`：可回放的对抗样本，每行一个测试场景。
- `policies/supervisor_policy.json`：监督插件使用的 allow / ask / block 策略与异常检测阈值。
- `openclaw/openclaw-provider-agentbrake-fusion.json`：OpenClaw OpenAI-compatible provider 示例配置。

## 原型代码

- `prototype/filter_model.py`：规则型基座模型输入输出过滤原型。
- `prototype/supervisor_plugin.py`：模型调用链路和工具调用的监督插件。
- `prototype/mock_business_tools.py`：模拟业务工具，包括邮件、文件、API、记忆、代码执行模拟。
- `prototype/mock_agent_app.py`：模拟智能体应用，按样本描述发起工具调用。
- `prototype/realtime_dashboard.py`：本地监督端页面和 JSON 审计接口。

## 攻击脚本

- `scripts/run_case.py`：按 `case_id` 回放单个场景。
- `scripts/run_all_attacks.py`：批量回放全部攻击场景。
- `attack_scripts/attack_prompt_injection.py`：提示注入与工具调用劫持回放。
- `attack_scripts/attack_jailbreak_code_exec.py`：越狱与代码执行滥用回放。
- `attack_scripts/attack_training_data_leak.py`：训练数据 / 机密输出泄露回放。
- `attack_scripts/attack_tool_hijack_api.py`：业务 API 调用劫持回放。
- `attack_scripts/attack_memory_poisoning.py`：记忆中毒与上下文污染回放。

## 测试与运行产物

- `tests/test_supervisor_prototype.py`：监督原型的最小单元测试。
- `runtime/.gitkeep`：运行产物目录占位文件。
- `runtime/audit_log.jsonl`、`runtime/alerts.jsonl`、`runtime/summary.json`：运行回放后生成的样例审计、告警和汇总记录。
