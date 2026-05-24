# RepoShield / PepoShield v0.3

RepoShield 是面向 coding agent 的执行前安全治理网关。它拦在模型 API、tool call、shell、文件操作、MCP 工具和包管理器动作之前，把即将执行的行为转换成结构化 `ActionIR`，再结合任务边界、来源可信度、资产类型、密钥事件、供应链信号、沙箱预检和策略图谱，决定动作是放行、仅沙箱执行、需要审批，还是直接阻断。

```text
RepoShield = coding agent 的 pre-execution safety gate
```

## 统一状态口径

当前定位：**研究级强化原型 / 早期工程 MVP**。

适合：论文演示、课程项目、内部实验、网关拦截研究、有限本地试用。  
不适合直接宣称：生产级商用安全产品、企业级多租户平台、完整供应链情报系统。

成熟度统一表述：

| 场景 | 当前成熟度 |
| --- | --- |
| 论文 demo / 项目展示 | 成熟 |
| 内部实验平台 | 可用 |
| 小团队本地试用 | 可试用，需要人工配置和边界说明 |
| 商业安全产品 | 未完成，仍需生产级 sandbox、真实情报、多租户与长期审计 |

Studio 完成度统一表述：

| 形态 | 当前状态 |
| --- | --- |
| Studio Lite 静态报告 | 可用，适合离线归档和演示材料 |
| Studio Pro 本地实时仪表盘 | 本地 demo / 实验可用，支持实时事件、攻击演示、证据图、策略调试、审批中心、沙箱证据和保护矩阵 |
| 生产级 Studio | 未完成，仍需团队权限、长期存储、跨项目搜索、多租户视图和运维能力 |

当前可复现验证基线：

```text
pytest --collect-only -q                    -> 202 collected
python -m pytest -q --basetemp=.pytest_tmp_final_all -> passed
python -m ruff check src tests              -> passed
python -m ruff format --check src tests web/studio/src -> passed
cd web/studio && npm run build              -> passed
```

Bench 样本数口径：

| 套件 | 默认生成数量 |
| --- | --- |
| Stage2 bench | 40 |
| Stage3 Gateway bench | 80 |

## 正式智能体接入

```bash
reposhield connect --repo . --agent codex --mode quick
reposhield connect --repo . --agent codex --mode standard
reposhield connect --repo . --agent openclaw --mode full
reposhield start --repo .
reposhield doctor --repo . --agent codex
reposhield smoke-test --repo . --agent codex
reposhield coverage --repo .
reposhield status --repo .
reposhield stop --repo .
```

- **Quick**：Gateway + `.reposhield/config.yaml`、`agent.env`、agent instructions。
- **Standard**：Quick + shell、包管理器、Python、Git 等 guarded tool shim。
- **Full**：Standard + Studio、Approval API、demo request。

多轮 agent 每一轮都必须传入稳定 `metadata.reposhield_run_id` 和 `metadata.conversation_id`。Gateway 也会返回 `X-RepoShield-Run-Id`，便于客户端确认本轮解析到的 run id。

RepoShield 现在使用 YAML agent profile 管理智能体差异：

```bash
reposhield profiles
reposhield profiles --agent codex
reposhield integration-matrix
```

新增智能体优先新增 `src/reposhield/integration/profiles/<agent>.yaml`，不应为单个智能体修改 Gateway 核心代码。

## 核心算法：多源证据综合判断算法（R-MPF）

R-MPF 全称 **Repository-aware Multi-Evidence Policy Fusion**，即“仓库感知的多源证据策略融合算法”。它不是只看工具名或黑名单，而是把多个证据源统一成事实，再通过 PolicyGraph 和 RuleIndex 形成可解释决策。

```text
ActionIR + Evidence
  -> Fact Extraction
  -> Invariants
  -> EvidenceIndex / RuleIndex
  -> PredicateEval
  -> DecisionLattice
  -> EvidenceGraph
  -> PolicyDecision
```

关键性质：

- **Invariant non-downgrade**：不可降级安全门命中后，普通策略不能把结果降级为直接放行。
- **Indexed retrieval soundness**：RuleIndex 可以多召回，但不能漏召回；测试验证索引候选与全量扫描命中等价。
- **Decision monotonicity**：更强证据或更高风险规则只会让决策保持或升级到更严格决策。

## 已完成能力

- OpenAI-compatible Gateway：`/v1/chat/completions` 与 `/v1/responses`
- Gateway bearer token 认证
- 每个请求隔离 `TaskContract`、`ContextGraph`、`SecretSentry`
- 统一决策语义：`allow`、`allow_in_sandbox`、`sandbox_then_approval`、`block`
- OpenAI、Anthropic、Cline、OpenClaw、OpenHands、Aider parser mapping
- ToolIntrospector / ToolMappingRegistry
- transcript provenance 与 strict transcript mode
- compound command lowering
- 文件路径 canonicalize、repo escape、symlink escape、hidden secret 检查
- SecretSentry、PackageGuard、MCPProxy、MemoryStore gate
- SandboxRunner dry-run / overlay / preflight
- PolicyGraph / RuleIndex 多源证据检索、候选规则缩小和可解释 trace
- ApprovalCenter / ApprovalStore
- AuditLog hash-chain、schema version、replay evidence validation
- Studio Lite 静态报告与 Studio Pro 本地实时仪表盘
- Stage2 / Stage3 bench、gateway bench、baseline / ablation 报告框架
- agent profile 化接入、doctor 修复建议、smoke-test、integration-matrix

## 仍需加强

- 生产级 sandbox：container、Linux namespace、seccomp/eBPF、网络监控等
- 真实供应链情报：npm/PyPI metadata、tarball inspection、Sigstore、typosquatting、maintainer reputation
- 更大规模真实 agent trace 兼容测试
- 策略签名、租户策略、团队权限、API key rotation
- 生产级 Studio：长期存储、跨项目搜索、多租户视图、团队协作、运维部署
- 更多真实样本上的误报、漏报和 ablation 指标

## 文档入口

1. [文档目录](docs/README.zh-CN.md)
2. [正式智能体接入指南](docs/FORMAL_AGENT_INTEGRATION.zh-CN.md)
3. [智能体接入 Profile 架构](docs/AGENT_PROFILE_ARCHITECTURE.zh-CN.md)
4. [PolicyGraph / RuleIndex 多源证据引擎](docs/POLICYGRAPH_RULEINDEX.zh-CN.md)
5. [Studio 指南](docs/STUDIO_GUIDE.zh-CN.md)
6. [项目状态与商用化评估](docs/PROJECT_STATUS.zh-CN.md)
