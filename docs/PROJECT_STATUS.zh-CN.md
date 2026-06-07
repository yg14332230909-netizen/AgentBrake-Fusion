# AgentBrake 项目状态与商用化评估

更新时间：2026-05-24

## 总体判断

AgentBrake 当前是 **研究级强化原型 / 早期工程 MVP**。

它已经具备完整的本地安全治理主链路：Gateway、ActionIR、TaskContract、ContextGraph、SecretSentry、PackageGuard、MCP/Memory gate、Sandbox preflight、PolicyGraph / RuleIndex、ApprovalCenter、AuditLog、Replay、Studio 和 Bench。

它还不是生产级商业安全产品。商用化仍需要生产级隔离、真实供应链情报、真实 agent trace 兼容、策略/审批产品化、团队权限、长期审计存储和生产级 Studio。

## 统一成熟度表述

| 使用场景 | 当前成熟度 | 说明 |
| --- | --- | --- |
| 论文 demo / 项目展示 | 成熟 | 主链路完整，风险点有测试，适合演示和答辩 |
| 内部实验平台 | 可用 | bench、replay、audit、baseline/ablation、Studio Pro 本地实验链路可用 |
| 小团队本地试用 | 可试用 | 可接 Gateway / exec-guard / agent profile，但需要人工配置和安全边界说明 |
| 商业安全产品 | 未完成 | 缺生产级 sandbox、真实情报、团队权限、多租户、长期审计和生产部署能力 |

不再使用互相冲突的百分比成熟度。对外建议使用上表的文字分级。

## 当前验证基线

```text
pytest --collect-only -q                    -> 202 collected
python -m pytest -q --basetemp=.pytest_tmp_final_all -> passed
python -m ruff check src tests              -> passed
python -m ruff format --check src tests web/studio/src -> passed
cd web/studio && npm run build              -> passed
```

Bench 样本数口径：

| 套件 | 默认生成数量 | 说明 |
| --- | --- | --- |
| Stage2 bench | 40 | 由 `generate-stage2-samples --count 40` 生成 |
| Stage3 Gateway bench | 80 | 由 `generate-stage3-samples --count 80` 生成 |

## Studio 完成度

| 形态 | 当前状态 | 未完成项 |
| --- | --- | --- |
| Studio Lite 静态报告 | 可用 | 不提供实时交互 |
| Studio Pro 本地实时仪表盘 | 本地 demo / 实验可用 | 不等同生产控制台 |
| 生产级 Studio | 未完成 | 团队权限、长期存储、跨项目搜索、多租户视图、部署运维、审计查询 |

Studio Pro 当前已覆盖：

- 运行列表和实时事件流
- 攻击演示
- Trace Graph
- 策略判断视图
- Policy Debugger
- Approval Center
- Sandbox Evidence
- Bench Report
- Coverage Matrix / 保护矩阵
- 记录清空与可选备份
- redacted evidence bundle export

## 已实现安全闭环

### Gateway 闭环

```text
request
  -> per-request control plane
  -> build TaskContract
  -> ingest external contexts
  -> upstream model or local heuristic
  -> InstructionIR
  -> ActionIR
  -> guard_action_ir()
  -> PolicyRuntime
  -> transform_response()
  -> audit / approval / response
```

Gateway-only 模式下，只有真正 host-safe 的 `allow` 才可释放给 agent。`allow_in_sandbox` 会转换成 sandbox-only assistant message，避免 agent 直接在宿主机执行。

### Tool execution 语义

| 决策 | 执行语义 |
| --- | --- |
| `allow` | 可宿主机执行 |
| `allow_in_sandbox` | 只能 sandbox / overlay / preflight |
| `sandbox_then_approval` | 不执行，等待审批 |
| `block` / `quarantine` | 不执行 |

### Audit 与 Replay

AuditLog 使用 hash-chain，事件有 `schema_version`。Replay 不只检查文件存在和 hash-chain，还会检查 policy decision 是否引用了存在的 action/package/exec trace evidence。

## 商用化差距

### 1. Sandbox

当前具备 dry-run evidence、overlay test execution、profile enforcement matrix 和显式 `isolation_level` / `production_ready` 标记。

商用仍需要：

- containerd / Docker / Podman backend
- Linux user/mount/network namespace
- seccomp 或 eBPF tracing
- DNS/HTTP egress monitor
- package lifecycle script capture
- process tree kill 和资源限制

### 2. 供应链情报

当前具备 command parser、registry 检查、lockfile evidence 和本地 `.agentbrake/package_metadata.json` oracle。

商用仍需要：

- npm/PyPI live metadata
- package tarball inspection
- Sigstore/provenance verification
- typosquatting detection
- maintainer/reputation signals
- dependency confusion policy

### 3. Agent 兼容

当前具备 OpenAI / Anthropic / Cline / OpenHands / Aider parser mapping、transcript strict mode、Gateway-compatible flow、YAML agent profile、doctor、smoke-test 和 integration-matrix。

商用仍需要：

- 更大规模真实 Codex / Cline / OpenHands / Aider trace corpus
- schema drift regression tests
- 每个 agent 的原生配置向导
- 长期兼容 CI

### 4. 策略与审批

当前具备 PolicyGraph / RuleIndex、ConfigurablePolicyOverrides、ApprovalCenter / ApprovalStore、Approval API。

商用仍需要：

- 稳定策略语言
- 策略签名和版本迁移
- RBAC / admin approval
- Web approval UI 的团队流程
- API key rotation 和 audit export

### 5. Studio / Dashboard

当前 Studio Pro 本地实验可用，但不是生产控制台。

商用仍需要：

- team workspace
- 长期审计存储
- 跨项目搜索
- 多租户视图
- 权限模型
- 运维部署与数据保留策略

## 对外表述建议

推荐使用：

> AgentBrake is a research-grade pre-execution governance gateway for coding agents, with a working engineering MVP covering gateway interception, tool-call governance, provenance-aware policy decisions, sandbox preflight, approval binding, and tamper-evident audit logs.

不建议现在宣称：

- production-grade sandbox
- enterprise-ready security product
- complete supply-chain intelligence
- complete support for all coding agents

当前最准确的定位：

```text
论文/演示：成熟
内部实验：可用
小团队试用：可试用
商业产品：未完成
```
