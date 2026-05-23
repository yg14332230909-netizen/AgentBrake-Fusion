# RepoShield 小白接入教程

这份教程假设你只想把一个真实 coding agent 接到 RepoShield，不想先理解所有内部概念。

## 1. 安装

```bash
python -m pip install -e ".[test]"
```

## 2. 选择模式

| 模式 | 什么时候用 |
| --- | --- |
| Quick | 第一次试用，只保护模型请求和 OpenAI tool_calls |
| Standard | 本地开发试用，额外保护 shell、git、npm、pip、python、curl 等常见命令 |
| Full | 演示、比赛、实验评测，额外打开 Studio 和 Approval API |

不知道选哪个时，先用 Standard：

```bash
reposhield connect --repo . --agent custom-openai --mode standard
```

## 3. 启动

```bash
reposhield start --repo .
```

查看状态：

```bash
reposhield status --repo .
```

停止：

```bash
reposhield stop --repo .
```

如果只想看会启动什么，不真正启动：

```bash
reposhield start --repo . --print-only
```

## 4. 配置 Agent

打开 `.reposhield/agent.env`，里面会有：

```bash
OPENAI_BASE_URL=http://127.0.0.1:8765/v1
OPENAI_API_KEY=reposhield-local
REPOSHIELD_RUN_ID=run_xxx
REPOSHIELD_CONVERSATION_ID=conv_xxx
```

把你的 Agent 的 OpenAI-compatible endpoint 指向：

```text
base_url = http://127.0.0.1:8765/v1
api_key  = reposhield-local
```

多轮任务每一轮都要带：

```json
{
  "metadata": {
    "reposhield_run_id": "run_xxx",
    "conversation_id": "conv_xxx"
  }
}
```

## 5. 检查

```bash
reposhield doctor --repo .
reposhield coverage --repo .
```

`doctor` 输出里的每个失败项都会带 `repair`，照着命令修即可。

常见例子：

```text
gateway_port_listening = false
repair: Start Gateway: reposhield start --repo . --gateway-only
```

```text
shims_on_path = false
repair: export PATH="$(pwd)/.reposhield/shims:$PATH"
```

## 6. 打开 Studio

Full 模式默认会启动 Studio：

```text
http://127.0.0.1:8780
```

Studio 里的“保护矩阵”页会显示哪些路径已经被保护，哪些只是部分保护，哪些还缺接入。

## 7. 最小成功标准

你应该看到：

```text
reposhield status --repo .  -> Gateway running
reposhield doctor --repo .  -> 关键检查 ok
Studio 保护矩阵             -> model_response / openai_tool_calls protected
```

如果你使用 Standard / Full，还应该把 shim 放到 PATH 最前：

```bash
export PATH="$(pwd)/.reposhield/shims:$PATH"
```
