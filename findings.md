# 发现与决策

## 需求
- 审查整个项目中与 WP1-1 相关的代码。
- 解释为什么使用阿里大模型时，系统在 `run_main.txt` 中落到 `"strategy_executed": "rules_only_degraded"`。
- 对比 OpenAI 模型几乎正常运行的情况，找出差异根因并给出解决方案。
- 调试时优先关注 `.runtime`。

## 研究发现
- `run_main.txt:274`、`run_main.txt:563`、`run_main.txt:2160`、`run_main.txt:3533` 等位置记录了同一根因：DashScope 返回 400，提示 `tool_choice` 在 thinking mode 下不支持 `required/object`。
- `run_main.txt` 顶部运行上下文显示的是 `source_runtime_mode="stub"` 且各策略为 `llm_optional`，这不是一次 `default_live()` 的输出。
- 本地执行 `python main.py -live` 会直接报 `unrecognized arguments: -live`；当前 CLI 只支持 `--live`。
- WP1-1 的 7 个结构化 LLM 工具都直接使用 `ChatOpenAI(...).with_structured_output(..., method="function_calling")`。
- LangChain `with_structured_output(..., method="function_calling")` 会绑定强制 `tool_choice=<specific function>`，这与 DashScope Qwen3/Qwen3.5 的 thinking mode 限制冲突。
- 项目此前没有任何针对 DashScope/Qwen 的 provider 兼容层，因此只要用户把 `OPENAI_BASE_URL` 指向 DashScope 并使用 Qwen3/Qwen3.5，就会在结构化输出节点上反复降级。
- 已新增 `backend/agents/intel_agents/tools/llm_client_factory.py`，对 DashScope `qwen3*`/`qwen3.5*` 结构化输出场景默认注入 `extra_body={"enable_thinking": False}`，并支持 `OPENAI_ENABLE_THINKING` 显式覆盖。

## 技术决策
| 决策 | 理由 |
|------|------|
| 以日志驱动代码审查 | 先固定真实失败路径，减少误判 |
| 将“阿里 vs OpenAI”做链路对照 | 这是定位 provider-specific 假设的最快方式 |
| 保留 LangChain 的 `function_calling` 结构化输出，但对 DashScope Qwen 自动关闭 thinking | 最小改动即可消除本次 400 错误，并保持现有 Pydantic 解析链路 |

## 遇到的问题
| 问题 | 解决方案 |
|------|---------|
| 系统 Python 缺少项目依赖，直接跑 `pytest` 失败 | 改用 `.venv\\Scripts\\python.exe -m pytest ...` |
| Phase 6 若干测试与当前主干代码签名/DTO 不一致 | 记录为仓库已有测试漂移，不将其归因于本次修复 |

## 资源
- `run_main.txt`
- `.runtime/`
- `main.py`
- `backend/`
- 阿里云官方文档：
- OpenAI 兼容接口参数 `enable_thinking`
- 阿里云错误码文档关于 `tool_choice`

## 视觉/浏览器发现
- 本任务暂不涉及浏览器取证。
