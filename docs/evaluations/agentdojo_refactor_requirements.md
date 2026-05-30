# RepoShield AgentDojo 评测代码整理要求文档

## 1. 文档目的

本文档定义 RepoShield 仓库中 **AgentDojo 评测相关代码** 的整理目标、目录结构、迁移步骤、验收标准和约束条件。

本次整理的核心目标不是修改 RepoShield 的核心安全逻辑，而是解决当前 AgentDojo 相关代码分散、命名不统一、实验脚本与核心实现混杂的问题，使仓库结构更清晰、可维护、可复现实验。

建议将本文档保存为：

```text
docs/evaluations/agentdojo_refactor_requirements.md
```

---

## 2. 背景问题

当前仓库中 AgentDojo 相关代码存在以下问题。

### 2.1 多套 AgentDojo 实现并存

目前仓库中同时存在类似以下几类 AgentDojo 相关实现：

```text
src/reposhield/eval/agentdojo/
src/reposhield/eval/agentdojo_firewall/
experiments/agentdojo_firewall/
experiments/agentdojo_toolgate/
experiments/agentdojo_gateway_only/
tests/eval/agentdojo/
tests/eval_agentdojo_firewall/
tests/test_agentdojo_toolgate.py
```

这会导致以下问题：

- 无法明确哪个目录是当前推荐实现；
- `ToolGate`、`ToolFirewall`、`Firewall` 等概念混用；
- 测试文件和源码结构不一致；
- 实验脚本、历史 baseline、核心评测适配逻辑混在一起；
- 新开发者难以判断应该从哪里开始阅读和运行。

### 2.2 AgentDojo 评测逻辑侵入主仓库结构

AgentDojo 本质上应当是 RepoShield 的一个**可选评测适配层**，而不是 RepoShield 核心逻辑的一部分。

整理后应当明确：

```text
RepoShield 核心能力     -> src/reposhield/
AgentDojo 评测适配层    -> src/reposhield/eval/agentdojo/
AgentDojo 实验脚本      -> experiments/agentdojo/
AgentDojo 文档          -> docs/evaluations/agentdojo.md
AgentDojo 测试          -> tests/eval/agentdojo/
```

---

## 3. 整理目标

本次整理需要达到以下目标。

### 3.1 确立唯一主线

将 **AgentDojo Tool Firewall** 作为唯一推荐的 AgentDojo 评测主线。

整理后，仓库中不应再让读者困惑于以下多个并列主线：

```text
agentdojo
agentdojo_firewall
agentdojo_toolgate
agentdojo_gateway_only
```

推荐命名：

```text
AgentDojo Tool Firewall
```

推荐代码包路径：

```text
src/reposhield/eval/agentdojo/
```

### 3.2 隔离历史实现

`gateway-only`、旧版 `toolgate`、DeepSeek no-defense baseline 等内容应当被标记为历史实现或 baseline，不应与当前主线并列。

历史内容统一放入：

```text
experiments/agentdojo/archive/
```

### 3.3 统一源码结构

所有 AgentDojo 评测适配代码统一收敛到：

```text
src/reposhield/eval/agentdojo/
```

不再保留并列的：

```text
src/reposhield/eval/agentdojo_firewall/
```

### 3.4 统一测试结构

所有 AgentDojo 相关测试统一收敛到：

```text
tests/eval/agentdojo/
```

不再保留：

```text
tests/eval_agentdojo_firewall/
tests/test_agentdojo_toolgate.py
```

### 3.5 隔离可选依赖

AgentDojo、OpenAI 等评测依赖不应成为 RepoShield 基础安装的硬依赖。

AgentDojo 相关依赖必须放入 optional dependencies，例如：

```bash
pip install -e ".[agentdojo]"
```

---

## 4. 非目标

本次整理不要求完成以下工作：

1. 不重写 RepoShield 核心检测算法；
2. 不重写 AgentDojo benchmark 本身；
3. 不修改已有评测指标的语义；
4. 不删除历史实验结果；
5. 不强制一次性删除所有兼容 import；
6. 不要求一次 PR 完成全部重构。

---

## 5. 目标目录结构

整理后的目标结构如下：

```text
RepoShield/
├── src/
│   └── reposhield/
│       ├── gateway/
│       ├── policy_engine/
│       ├── sandbox/
│       ├── cli.py
│       ├── cli_commands/
│       │   ├── __init__.py
│       │   ├── core.py
│       │   ├── gateway.py
│       │   ├── studio.py
│       │   └── eval_agentdojo.py
│       └── eval/
│           ├── fast_mode.py
│           └── agentdojo/
│               ├── __init__.py
│               ├── README.md
│               ├── compat/
│               │   ├── __init__.py
│               │   ├── agentdojo_api.py
│               │   ├── models_compat.py
│               │   └── types.py
│               ├── gate/
│               │   ├── __init__.py
│               │   ├── tool_firewall.py
│               │   ├── runtime_wrapper.py
│               │   └── blocked_result.py
│               ├── evidence/
│               │   ├── __init__.py
│               │   ├── action_graph.py
│               │   ├── entity_extractor.py
│               │   ├── evidence.py
│               │   ├── fusion.py
│               │   ├── state.py
│               │   ├── task_authorizer.py
│               │   ├── taxonomy.py
│               │   └── tool_taxonomy.yaml
│               ├── runner/
│               │   ├── __init__.py
│               │   ├── run_benchmark.py
│               │   ├── run_tool_firewall_eval.py
│               │   ├── result_exporter.py
│               │   └── metrics.py
│               └── adapters/
│                   ├── __init__.py
│                   ├── pipeline_wrapper.py
│                   ├── native_defense.py
│                   └── inspect_adapter.py
│
├── experiments/
│   └── agentdojo/
│       ├── README.md
│       ├── configs/
│       ├── scripts/
│       │   ├── 00_setup_env.sh
│       │   ├── 01_dump_tools.py
│       │   ├── 02_run_baseline.sh
│       │   ├── 03_run_gateway_only.sh
│       │   ├── 04_run_tool_firewall.sh
│       │   ├── 05_profile_report.py
│       │   └── run_all.sh
│       ├── reports/
│       │   └── .gitkeep
│       └── archive/
│           ├── gateway_only/
│           ├── toolgate_legacy/
│           └── deepseek_no_defense_baseline/
│
├── tests/
│   └── eval/
│       └── agentdojo/
│           ├── unit/
│           │   ├── test_taxonomy.py
│           │   ├── test_state.py
│           │   ├── test_action_graph.py
│           │   ├── test_fusion.py
│           │   └── test_tool_firewall.py
│           ├── integration/
│           │   ├── test_runtime_wrapper.py
│           │   ├── test_pipeline_wrapper.py
│           │   └── test_legacy_toolgate_compat.py
│           └── smoke/
│               └── test_agentdojo_smoke.py
│
└── docs/
    └── evaluations/
        ├── agentdojo.md
        └── agentdojo_refactor_requirements.md
```

---

## 6. 源码整理要求

### 6.1 AgentDojo 主包

必须将 AgentDojo 相关实现统一到：

```text
src/reposhield/eval/agentdojo/
```

不得继续保留以下并列主实现：

```text
src/reposhield/eval/agentdojo_firewall/
```

### 6.2 子模块职责

#### `compat/`

用于放置与外部 AgentDojo API 版本兼容有关的代码。

包括：

```text
models_compat.py
agentdojo_api.py
types.py
```

要求：

- 不放核心防御逻辑；
- 只处理外部依赖 API 差异；
- 所有 AgentDojo 版本差异应集中在此层处理。

#### `gate/`

用于放置工具调用边界防护逻辑。

包括：

```text
tool_firewall.py
runtime_wrapper.py
blocked_result.py
```

要求：

- `tool_firewall.py` 是当前推荐主实现；
- `runtime_wrapper.py` 负责包装 AgentDojo 的工具执行边界；
- 不在此目录中放 benchmark runner；
- 不在此目录中写实验脚本。

#### `evidence/`

用于放置 evidence、状态跟踪、动作图、taxonomy、fusion 等逻辑。

包括：

```text
action_graph.py
evidence.py
fusion.py
state.py
taxonomy.py
task_authorizer.py
tool_taxonomy.yaml
```

要求：

- `taxonomy.py` 与 `tool_taxonomy.yaml` 只保留一套；
- 不再同时保留 `tool_taxonomy.py` 和另一套 `taxonomy.py` 表达同类概念；
- `state.py` 作为状态跟踪主实现，不再额外保留功能重复的 `state_tracker.py`。

#### `runner/`

用于放置评测运行入口。

包括：

```text
run_benchmark.py
run_tool_firewall_eval.py
result_exporter.py
metrics.py
```

要求：

- runner 可以 import `gate/`、`evidence/`、`adapters/`；
- runner 不应被 `src/reposhield/eval/agentdojo/__init__.py` 顶层导入；
- runner 中的 AgentDojo / OpenAI 依赖必须懒加载。

#### `adapters/`

用于放置与 AgentDojo pipeline 或 inspect 框架集成的适配代码。

包括：

```text
pipeline_wrapper.py
native_defense.py
inspect_adapter.py
```

要求：

- adapters 只做适配，不承载核心安全决策逻辑；
- 核心判断逻辑必须位于 `gate/` 或 `evidence/`。

---

## 7. 命名要求

### 7.1 推荐术语

统一使用：

```text
AgentDojo Tool Firewall
```

推荐类名：

```python
AgentDojoToolFirewall
```

推荐 CLI mode：

```text
tool-firewall
```

推荐脚本名：

```text
run_tool_firewall_eval.py
```

### 7.2 废弃术语

以下术语不应再作为新代码或新文档中的主命名：

```text
ToolGate
agentdojo_toolgate
agentdojo_firewall
gateway_only
```

其中：

- `ToolGate` 只允许作为兼容层出现；
- `gateway-only` 只允许作为 baseline 或 archive 出现；
- `agentdojo_firewall` 不应作为最终目录名继续存在；
- `agentdojo_toolgate` 不应作为主实验目录继续存在。

### 7.3 兼容 wrapper

为了降低迁移风险，允许临时保留兼容 wrapper，例如：

```python
# src/reposhield/eval/agentdojo/tool_gate.py

"""
Deprecated compatibility wrapper.

Use:
    reposhield.eval.agentdojo.gate.tool_firewall.AgentDojoToolFirewall
instead.
"""

from .gate.tool_firewall import AgentDojoToolFirewall as RepoShieldToolGate

__all__ = ["RepoShieldToolGate"]
```

---

## 8. 实验目录整理要求

### 8.1 唯一实验入口

AgentDojo 相关实验统一放入：

```text
experiments/agentdojo/
```

不得继续保留多个并列目录作为主入口：

```text
experiments/agentdojo_firewall/
experiments/agentdojo_toolgate/
experiments/agentdojo_gateway_only/
```

### 8.2 实验目录职责

`experiments/agentdojo/` 只允许放：

```text
README.md
configs/
scripts/
reports/
archive/
```

要求：

- 不放核心 Python 实现；
- 不复制 `src/reposhield/eval/agentdojo/` 中的逻辑；
- 脚本只负责调用 CLI 或 runner；
- 实验结果报告统一放入 `reports/`；
- 历史 baseline 放入 `archive/`。

### 8.3 archive 目录

历史内容统一放入：

```text
experiments/agentdojo/archive/
```

建议结构：

```text
archive/
├── gateway_only/
├── toolgate_legacy/
└── deepseek_no_defense_baseline/
```

要求：

- 历史日志和报告不得直接删除；
- 历史实现不得与当前主线并列；
- archive 中必须包含 README，解释该目录内容已废弃或仅用于历史对比。

示例：

```md
# AgentDojo Archived Experiments

This directory contains historical AgentDojo evaluation artifacts.

Current recommended path:
    experiments/agentdojo/scripts/04_run_tool_firewall.sh

Archived paths:
    gateway_only/                  Historical gateway-only baseline
    toolgate_legacy/               Legacy ToolGate implementation
    deepseek_no_defense_baseline/  Historical DeepSeek no-defense results
```

---

## 9. 测试整理要求

### 9.1 统一测试根目录

所有 AgentDojo 测试必须统一放入：

```text
tests/eval/agentdojo/
```

不得继续保留：

```text
tests/eval_agentdojo_firewall/
tests/test_agentdojo_toolgate.py
```

### 9.2 测试分层

AgentDojo 测试分为三类。

#### Unit tests

路径：

```text
tests/eval/agentdojo/unit/
```

用于测试纯逻辑模块：

```text
taxonomy
state
action_graph
fusion
tool_firewall
task_authorizer
```

要求：

- 不调用真实 LLM；
- 不访问网络；
- 不要求真实 AgentDojo benchmark 全量运行；
- 默认 CI 必须运行。

#### Integration tests

路径：

```text
tests/eval/agentdojo/integration/
```

用于测试：

```text
runtime_wrapper
pipeline_wrapper
legacy compatibility wrapper
```

要求：

- 尽量 mock 外部依赖；
- 不应默认调用真实 API；
- 可以依赖本地安装的 AgentDojo，但必须可跳过。

#### Smoke tests

路径：

```text
tests/eval/agentdojo/smoke/
```

用于测试最小 AgentDojo benchmark 运行链路。

要求：

- 允许标记为 slow；
- 默认 CI 可以不运行；
- 必须通过 pytest marker 控制。

### 9.3 pytest marker

`pyproject.toml` 中应增加：

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-q --basetemp=.pytest_tmp"
markers = [
  "agentdojo: AgentDojo evaluation tests",
  "external: requires real external API or installed benchmark package",
  "slow: slow benchmark-style tests",
]
```

默认测试命令：

```bash
pytest -q tests/eval/agentdojo/unit
pytest -q tests/eval/agentdojo/integration -m "not external"
```

完整 AgentDojo 测试命令：

```bash
pytest -q tests/eval/agentdojo -m agentdojo
```

外部 API 测试命令：

```bash
pytest -q tests/eval/agentdojo -m external
```

---

## 10. 依赖整理要求

### 10.1 基础安装不引入 AgentDojo

基础安装：

```bash
pip install -e .
```

不得强制安装：

```text
agentdojo
openai
```

### 10.2 新增 optional dependency

`pyproject.toml` 中应增加：

```toml
[project.optional-dependencies]
agentdojo = [
  "agentdojo>=0.1.35,<0.2",
  "openai>=1.0",
  "PyYAML>=6",
]

eval = [
  "agentdojo>=0.1.35,<0.2",
  "openai>=1.0",
  "PyYAML>=6",
]
```

如果实际使用的 AgentDojo 版本不同，应根据当前可运行版本调整版本范围，但不得裸写：

```toml
agentdojo
```

### 10.3 AgentDojo 依赖必须懒加载

禁止在以下文件中顶层导入重依赖：

```text
src/reposhield/eval/agentdojo/__init__.py
src/reposhield/__init__.py
src/reposhield/cli.py
```

推荐写法：

```python
def require_agentdojo() -> None:
    try:
        import agentdojo  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "AgentDojo evaluation requires: pip install -e '.[agentdojo]'"
        ) from exc
```

runner 或 CLI 子命令可以在执行时调用：

```python
require_agentdojo()
```

---

## 11. CLI 整理要求

### 11.1 主 CLI 不继续膨胀

`src/reposhield/cli.py` 只负责：

- 创建 parser；
- 注册子命令；
- 分发命令。

AgentDojo 相关 CLI 逻辑应放入：

```text
src/reposhield/cli_commands/eval_agentdojo.py
```

### 11.2 推荐 CLI 结构

推荐命令结构：

```bash
reposhield eval agentdojo inventory
reposhield eval agentdojo run --mode baseline
reposhield eval agentdojo run --mode gateway-only
reposhield eval agentdojo run --mode tool-firewall
reposhield eval agentdojo summarize
reposhield eval agentdojo profile
```

### 11.3 CLI mode 要求

允许以下 mode：

```text
baseline
gateway-only
tool-firewall
```

其中：

- `baseline` 表示无 RepoShield 防御；
- `gateway-only` 表示历史/对照评测路径；
- `tool-firewall` 表示当前推荐路径。

默认 mode 应为：

```text
tool-firewall
```

---

## 12. 文档要求

### 12.1 新增主文档

新增：

```text
docs/evaluations/agentdojo.md
```

该文档必须说明：

1. AgentDojo 评测目的；
2. 当前推荐路径；
3. baseline 与 gateway-only 的区别；
4. 如何安装依赖；
5. 如何运行最小评测；
6. 如何运行完整评测；
7. 如何查看报告；
8. 哪些目录是历史 archive。

### 12.2 实验 README

更新：

```text
experiments/agentdojo/README.md
```

必须包含：

```md
# AgentDojo Evaluation

Recommended path:
    Tool-boundary AgentDojo Tool Firewall

Run:
    bash experiments/agentdojo/scripts/04_run_tool_firewall.sh

Historical baselines:
    experiments/agentdojo/archive/
```

### 12.3 旧目录 README

如果旧目录在迁移过程中暂时保留，README 顶部必须加：

```md
> Deprecated.
>
> Use:
> - `src/reposhield/eval/agentdojo/`
> - `experiments/agentdojo/`
>
> This directory will be removed after compatibility migration.
```

---

## 13. 迁移步骤

本次整理建议拆成 5 个 PR，不建议一次性完成。

---

### PR 1：文档定线

目标：先明确主线，不移动大量代码。

任务：

1. 新增：

```text
docs/evaluations/agentdojo_refactor_requirements.md
docs/evaluations/agentdojo.md
```

2. 在旧目录 README 中标记 deprecated：

```text
experiments/agentdojo_toolgate/README.md
experiments/agentdojo_gateway_only/README.md
```

3. 明确当前推荐路径：

```text
AgentDojo Tool Firewall
```

验收标准：

- 文档中明确说明 `tool-firewall` 是推荐路径；
- `gateway-only` 被标记为历史 baseline；
- `toolgate` 被标记为 legacy 术语；
- 不修改核心代码。

---

### PR 2：整理 experiments 目录

目标：将实验入口统一到一个目录。

任务：

```bash
mkdir -p experiments/agentdojo/{scripts,configs,reports,archive}
```

迁移推荐实验脚本：

```bash
git mv experiments/agentdojo_firewall/README.md experiments/agentdojo/README.md
git mv experiments/agentdojo_firewall/scripts/* experiments/agentdojo/scripts/
```

迁移旧 ToolGate 内容：

```bash
mkdir -p experiments/agentdojo/archive/toolgate_legacy
git mv experiments/agentdojo_toolgate/* experiments/agentdojo/archive/toolgate_legacy/
```

迁移 gateway-only 内容：

```bash
mkdir -p experiments/agentdojo/archive/gateway_only
git mv experiments/agentdojo_gateway_only/* experiments/agentdojo/archive/gateway_only/
```

迁移历史 baseline：

```bash
mkdir -p experiments/agentdojo/archive/deepseek_no_defense_baseline
git mv <old-baseline-files> experiments/agentdojo/archive/deepseek_no_defense_baseline/
```

验收标准：

- `experiments/agentdojo/` 成为唯一 AgentDojo 实验入口；
- `archive/` 中有 README；
- 旧实验结果未被删除；
- 脚本仍能调用现有 runner 或 CLI。

---

### PR 3：合并源码包

目标：将 AgentDojo 源码合并到单一包。

新建目录：

```bash
mkdir -p src/reposhield/eval/agentdojo/{compat,gate,evidence,runner,adapters}
```

迁移 firewall 主实现：

```bash
git mv src/reposhield/eval/agentdojo_firewall/tool_firewall.py src/reposhield/eval/agentdojo/gate/tool_firewall.py
git mv src/reposhield/eval/agentdojo_firewall/runtime_wrapper.py src/reposhield/eval/agentdojo/gate/runtime_wrapper.py
git mv src/reposhield/eval/agentdojo_firewall/action_graph.py src/reposhield/eval/agentdojo/evidence/action_graph.py
git mv src/reposhield/eval/agentdojo_firewall/evidence.py src/reposhield/eval/agentdojo/evidence/evidence.py
git mv src/reposhield/eval/agentdojo_firewall/fusion.py src/reposhield/eval/agentdojo/evidence/fusion.py
git mv src/reposhield/eval/agentdojo_firewall/state.py src/reposhield/eval/agentdojo/evidence/state.py
git mv src/reposhield/eval/agentdojo_firewall/taxonomy.py src/reposhield/eval/agentdojo/evidence/taxonomy.py
git mv src/reposhield/eval/agentdojo_firewall/task_authorizer.py src/reposhield/eval/agentdojo/evidence/task_authorizer.py
git mv src/reposhield/eval/agentdojo_firewall/types.py src/reposhield/eval/agentdojo/compat/types.py
git mv src/reposhield/eval/agentdojo_firewall/models_compat.py src/reposhield/eval/agentdojo/compat/models_compat.py
```

迁移 runner 和 adapter：

```bash
git mv src/reposhield/eval/agentdojo/run_toolgate_eval.py src/reposhield/eval/agentdojo/runner/run_tool_firewall_eval.py
git mv src/reposhield/eval/agentdojo/result_exporter.py src/reposhield/eval/agentdojo/runner/result_exporter.py
git mv src/reposhield/eval/agentdojo/pipeline_wrapper.py src/reposhield/eval/agentdojo/adapters/pipeline_wrapper.py
git mv src/reposhield/eval/agentdojo/native_defense.py src/reposhield/eval/agentdojo/adapters/native_defense.py
git mv src/reposhield/eval/agentdojo/inspect_adapter.py src/reposhield/eval/agentdojo/adapters/inspect_adapter.py
```

添加 `__init__.py`：

```bash
touch src/reposhield/eval/agentdojo/compat/__init__.py
touch src/reposhield/eval/agentdojo/gate/__init__.py
touch src/reposhield/eval/agentdojo/evidence/__init__.py
touch src/reposhield/eval/agentdojo/runner/__init__.py
touch src/reposhield/eval/agentdojo/adapters/__init__.py
```

添加兼容 wrapper：

```text
src/reposhield/eval/agentdojo/tool_gate.py
```

内容：

```python
"""
Deprecated compatibility wrapper.

Use:
    reposhield.eval.agentdojo.gate.tool_firewall.AgentDojoToolFirewall
instead.
"""

from .gate.tool_firewall import AgentDojoToolFirewall as RepoShieldToolGate

__all__ = ["RepoShieldToolGate"]
```

验收标准：

- 不再存在主实现目录 `src/reposhield/eval/agentdojo_firewall/`；
- 新代码统一 import `reposhield.eval.agentdojo.*`；
- 旧 import 通过兼容 wrapper 暂时可用；
- 单元测试通过。

---

### PR 4：整理测试

目标：测试结构与源码结构保持一致。

新建目录：

```bash
mkdir -p tests/eval/agentdojo/{unit,integration,smoke}
```

迁移测试：

```bash
git mv tests/eval_agentdojo_firewall/test_taxonomy.py tests/eval/agentdojo/unit/test_taxonomy.py
git mv tests/eval_agentdojo_firewall/test_action_graph.py tests/eval/agentdojo/unit/test_action_graph.py
git mv tests/eval_agentdojo_firewall/test_fusion.py tests/eval/agentdojo/unit/test_fusion.py
git mv tests/eval_agentdojo_firewall/test_firewall.py tests/eval/agentdojo/unit/test_tool_firewall.py
git mv tests/eval_agentdojo_firewall/test_tool_firewall.py tests/eval/agentdojo/integration/test_tool_firewall_integration.py
git mv tests/test_agentdojo_toolgate.py tests/eval/agentdojo/integration/test_legacy_toolgate_compat.py
```

根据测试内容调整 import：

```python
from reposhield.eval.agentdojo.gate.tool_firewall import AgentDojoToolFirewall
from reposhield.eval.agentdojo.evidence.taxonomy import ...
from reposhield.eval.agentdojo.evidence.state import ...
```

验收标准：

- `tests/eval_agentdojo_firewall/` 被删除；
- `tests/test_agentdojo_toolgate.py` 不再位于测试根目录；
- unit tests 不依赖真实 LLM；
- integration tests 可通过 marker 跳过外部依赖；
- pytest 通过。

---

### PR 5：整理依赖与 CLI

目标：隔离 AgentDojo 可选依赖，并拆分 CLI。

新增：

```text
src/reposhield/cli_commands/eval_agentdojo.py
```

修改：

```text
src/reposhield/cli.py
pyproject.toml
```

`pyproject.toml` 增加：

```toml
[project.optional-dependencies]
agentdojo = [
  "agentdojo>=0.1.35,<0.2",
  "openai>=1.0",
  "PyYAML>=6",
]

eval = [
  "agentdojo>=0.1.35,<0.2",
  "openai>=1.0",
  "PyYAML>=6",
]
```

CLI 子命令：

```bash
reposhield eval agentdojo inventory
reposhield eval agentdojo run --mode baseline
reposhield eval agentdojo run --mode gateway-only
reposhield eval agentdojo run --mode tool-firewall
reposhield eval agentdojo summarize
reposhield eval agentdojo profile
```

验收标准：

- `pip install -e .` 不安装 AgentDojo；
- `pip install -e ".[agentdojo]"` 可运行 AgentDojo 评测；
- import `reposhield` 不触发 AgentDojo / OpenAI import；
- AgentDojo CLI 逻辑不继续塞进主 `cli.py`；
- 默认运行模式为 `tool-firewall`。

---

## 14. Import 修改要求

迁移后，新代码应使用以下 import。

### 推荐 import

```python
from reposhield.eval.agentdojo.gate.tool_firewall import AgentDojoToolFirewall
from reposhield.eval.agentdojo.gate.runtime_wrapper import ...
from reposhield.eval.agentdojo.evidence.action_graph import ...
from reposhield.eval.agentdojo.evidence.fusion import ...
from reposhield.eval.agentdojo.evidence.state import ...
from reposhield.eval.agentdojo.evidence.taxonomy import ...
from reposhield.eval.agentdojo.runner.result_exporter import ...
from reposhield.eval.agentdojo.adapters.pipeline_wrapper import ...
```

### 禁止新增 import

新代码不得新增：

```python
from reposhield.eval.agentdojo_firewall import ...
from reposhield.eval.agentdojo.tool_gate import ...
```

其中 `tool_gate.py` 只允许旧代码兼容使用，不允许新代码依赖。

---

## 15. Git 操作要求

迁移文件时应优先使用：

```bash
git mv
```

不要使用：

```bash
mv
```

原因：

- 保留 Git 历史；
- 方便 code review；
- 降低误删风险。

每个 PR 应尽量保持单一目的：

| PR | 目的 |
|---|---|
| PR 1 | 文档定线 |
| PR 2 | 整理 experiments |
| PR 3 | 合并源码包 |
| PR 4 | 整理测试 |
| PR 5 | 整理依赖和 CLI |

---

## 16. 验收标准总表

整理完成后，必须满足以下标准。

### 16.1 目录标准

必须存在：

```text
src/reposhield/eval/agentdojo/
experiments/agentdojo/
tests/eval/agentdojo/
docs/evaluations/agentdojo.md
```

不应继续存在主实现目录：

```text
src/reposhield/eval/agentdojo_firewall/
experiments/agentdojo_firewall/
experiments/agentdojo_toolgate/
experiments/agentdojo_gateway_only/
tests/eval_agentdojo_firewall/
```

允许历史内容存在于：

```text
experiments/agentdojo/archive/
```

### 16.2 命名标准

当前推荐路径必须统一叫：

```text
AgentDojo Tool Firewall
```

当前推荐 mode 必须统一叫：

```text
tool-firewall
```

旧术语只允许出现在：

```text
archive/
compatibility wrapper
deprecated README
migration notes
```

### 16.3 测试标准

以下命令必须通过：

```bash
pytest -q tests/eval/agentdojo/unit
pytest -q tests/eval/agentdojo/integration -m "not external"
```

基础测试必须不调用真实外部 API。

### 16.4 安装标准

基础安装必须成功：

```bash
pip install -e .
python -c "import reposhield"
```

AgentDojo 评测安装必须成功：

```bash
pip install -e ".[agentdojo]"
```

### 16.5 文档标准

以下文档必须存在并可读：

```text
docs/evaluations/agentdojo.md
experiments/agentdojo/README.md
experiments/agentdojo/archive/README.md
```

文档中必须明确：

- 推荐路径是 `tool-firewall`；
- `gateway-only` 是 baseline；
- `toolgate` 是 legacy；
- 历史结果位于 `archive/`；
- 如何安装 AgentDojo 评测依赖；
- 如何运行最小评测。

---

## 17. 风险与控制措施

### 17.1 Import 破坏风险

风险：

- 文件移动后旧 import 失效。

控制：

- 使用兼容 wrapper；
- 分阶段迁移；
- 每个 PR 后运行测试；
- 在最终 PR 再删除旧 import。

### 17.2 外部依赖破坏风险

风险：

- AgentDojo API 变化导致 runner 失效。

控制：

- 将 AgentDojo 相关兼容代码集中在 `compat/`；
- optional dependency 中 pin 版本范围；
- 使用懒加载；
- integration tests 中对外部依赖进行 skip 或 mock。

### 17.3 实验结果丢失风险

风险：

- 整理目录时误删历史 baseline 和日志。

控制：

- 历史文件只移动到 `archive/`；
- 使用 `git mv`；
- `archive/README.md` 说明历史结果来源和用途。

### 17.4 PR 过大风险

风险：

- 一次性改动过多，review 困难。

控制：

- 拆成 5 个 PR；
- 每个 PR 保持单一目的；
- 每个 PR 都必须能独立通过测试。

---

## 18. 最终完成状态

整理完成后，RepoShield 的 AgentDojo 相关结构应表达清楚：

```text
RepoShield core
    主体安全能力，与 AgentDojo 解耦。

src/reposhield/eval/agentdojo/
    AgentDojo 评测适配源码。

experiments/agentdojo/
    可复现实验入口、脚本、报告和历史 baseline。

tests/eval/agentdojo/
    AgentDojo 相关测试。

docs/evaluations/agentdojo.md
    AgentDojo 评测说明文档。
```

最终读者应当能够明确知道：

1. 当前推荐方案是什么；
2. 应该运行哪个脚本或 CLI；
3. 哪些目录是历史内容；
4. 哪些代码是核心实现；
5. 哪些代码只是 benchmark adapter；
6. 如何在不安装 AgentDojo 的情况下使用 RepoShield 主功能。
