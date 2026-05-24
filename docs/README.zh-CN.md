# RepoShield 文档目录

RepoShield 是面向 coding agent 的执行前安全治理网关。它可以作为 OpenAI-compatible Gateway 接入模型请求，也可以通过 `exec-guard`、file guard、PATH shim、Studio 和 Approval API 治理真实工具执行路径。

## 推荐阅读顺序

1. [顶层中文 README](../README.zh-CN.md)  
   项目定位、核心能力、快速开始和整体架构。
2. [正式智能体接入简化指南](FORMAL_AGENT_INTEGRATION.zh-CN.md)  
   `connect / start / status / stop / doctor / smoke-test / coverage` 的完整流程。
3. [智能体接入 Profile 架构](AGENT_PROFILE_ARCHITECTURE.zh-CN.md)  
   说明为什么新增智能体应优先新增 YAML profile，而不是修改 Gateway 核心代码。
4. [小白接入教程](BEGINNER_AGENT_ONBOARDING.zh-CN.md)  
   从安装、接入、启动、体检到 Studio 保护矩阵的一步步教程。
5. [真实 Agent 接入指南](REAL_AGENT_INTEGRATION.zh-CN.md)  
   Gateway、exec-guard、tool call 解析，以及 OpenClaw / OpenHands / Aider 等接入方式。
6. [Gateway 指南](GATEWAY_GUIDE.zh-CN.md)  
   OpenAI-compatible Gateway、认证、上游转发、streaming 和 release mode。
7. [Studio 指南](STUDIO_GUIDE.zh-CN.md)  
   如何启动实时前端，以及如何查看证据图谱、策略判断、审批和沙箱证据。
8. [Policy Pack / PolicyGraph 规则指南](POLICY_PACK_GUIDE.zh-CN.md)  
   决策语义、runtime 模式、YAML 规则、`index_hints` 和验证方式。
9. [项目状态与商用化评估](PROJECT_STATUS.zh-CN.md)  
   当前成熟度、已完成能力、剩余差距和路线图。

## 智能体接入

- [正式智能体接入简化指南](FORMAL_AGENT_INTEGRATION.zh-CN.md)
- [智能体接入 Profile 架构](AGENT_PROFILE_ARCHITECTURE.zh-CN.md)
- [Adapter 指南](ADAPTER_GUIDE.zh-CN.md)
- [Tool Parser Plugin 指南](TOOL_PARSER_PLUGIN_GUIDE.zh-CN.md)
- [Agent exec-guard recipes](AGENT_EXEC_GUARD_RECIPES.zh-CN.md)

Agent 专用模板：

- [custom-openai-compatible](integrations/custom-openai-compatible.md)
- [openclaw](integrations/openclaw.md)
- [cline](integrations/cline.md)
- [openhands](integrations/openhands.md)
- [aider](integrations/aider.md)
- [codex-cli](integrations/codex-cli.md)
- [claude-code](integrations/claude-code.md)

## 常用命令

```bash
reposhield connect --repo . --agent codex --mode standard
reposhield start --repo .
reposhield status --repo .
reposhield doctor --repo . --agent codex
reposhield smoke-test --repo . --agent codex
reposhield profiles --agent codex
reposhield integration-matrix
reposhield stop --repo .
```

## Bench / Replay / Studio

- [Gateway Bench 指南](BENCH_GATEWAY_GUIDE.zh-CN.md)
- [Bench Report 指南](BENCH_REPORT_GUIDE.zh-CN.md)
- [Studio 指南](STUDIO_GUIDE.zh-CN.md)
- [测试用例说明](TEST_CASES.zh-CN.md)

## 当前能力摘要

RepoShield 当前已经具备：

- OpenAI-compatible Gateway：`/v1/chat/completions` 与 `/v1/responses`
- agent profile 化接入：`src/reposhield/integration/profiles/*.yaml`
- 多轮稳定身份：`run_id` / `conversation_id`
- 多源证据综合判断算法（R-MPF）
- PolicyGraph / RuleIndex
- PersistentSessionState / ActionGraph
- SecretSentry / PackageGuard
- exec-guard / file-guard / PATH shim
- ApprovalCenter / ApprovalStore / Approval API
- AuditLog hash-chain
- Studio Pro 实时前端
- Stage2 / Stage3 bench 与报告

当前仍可继续产品化的方向：

- 更多智能体的原生配置写入器
- 生产级强隔离 sandbox
- 团队权限、长期存储、审计查询和多租户管理
- 更大规模真实 agent trace 兼容性矩阵
