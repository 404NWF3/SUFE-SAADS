# saads-wp12 项目阶段总结与说明书

## 1. 当前阶段概览

本项目当前处于 **阶段 0：环境与工程骨架初始化**。

截至目前，已经完成的工作是：

1. 确认本机已安装并可用的开发工具：
   - VS Code
   - uv 0.10.9
   - 系统 Python 3.14.3（仅系统存在，不直接用于本项目）
2. 为项目单独准备了 **Python 3.11** 运行环境方案，避免直接使用系统 Python 3.14 导致团队依赖兼容性风险。
3. 已使用队长提供的 `requirements` 锁定文件作为团队依赖基线，选择“先复刻团队环境，再逐步写项目代码”的稳妥路线。
4. 已完成项目目录树创建，包括：
   - 主包目录 `saads_wp12/`
   - 子图目录 `graphs/subgraphs/`
   - 节点目录 `nodes/`
   - 技能目录 `skills/aibom_env_build_skill/`
   - 测试目录 `tests/`
   - 运行时目录 `runtime_envs/`
   - 结果目录 `artifacts/`
   - 日志目录 `logs/`
5. 已完成基础项目文本文件的第一版填写：
   - `.gitignore`
   - `.env.example`
   - `README.md`
6. 已明确当前工程路线：
   - 外层用 LangGraph 主图做总控
   - 高不确定性环节用 3 个子图完成推理
   - AIBOM 环境构建作为独立 skill
   - 测试包与运行时资产分离

> 说明：截至本说明书撰写时，项目中的大多数 Python 文件已经创建，但仍是“占位文件/待实现文件”。也就是说，**目录骨架已搭好，代码主体尚未开始逐步填充**。

---

## 2. 当前项目目录结构

> 以下目录树描述的是“当前已创建的工程骨架”。其中大量 `.py` 文件目前是空文件或占位文件，但它们的职责已经在架构上确定。

```text
saads-wp12/
├─ .python-version
├─ .venv/
├─ .gitignore
├─ .env.example
├─ README.md
├─ requirements-team.txt
├─ saads_wp12/
│  ├─ __init__.py
│  ├─ agent.py
│  ├─ config.py
│  ├─ run_local.py
│  ├─ state.py
│  ├─ graphs/
│  │  ├─ __init__.py
│  │  ├─ main_graph.py
│  │  └─ subgraphs/
│  │     ├─ __init__.py
│  │     ├─ threat_understanding.py
│  │     ├─ test_package_generation.py
│  │     └─ reflection.py
│  ├─ nodes/
│  │  ├─ __init__.py
│  │  ├─ intel.py
│  │  ├─ routing.py
│  │  ├─ validation.py
│  │  ├─ env_build.py
│  │  ├─ runtime_assets.py
│  │  ├─ execution.py
│  │  └─ persistence.py
│  └─ skills/
│     ├─ __init__.py
│     └─ aibom_env_build_skill/
│        ├─ __init__.py
│        └─ README.md
├─ tests/
│  ├─ __init__.py
│  └─ test_smoke.py
├─ runtime_envs/
├─ artifacts/
└─ logs/
```

---

## 3. 目录级别职责说明

### 3.1 根目录
根目录负责承载整个项目的配置、依赖、文档和运行输出。

- `.python-version`：约束本项目应使用的 Python 版本。
- `.venv/`：本项目专用虚拟环境。
- `.gitignore`：约束不应被 Git 提交的文件。
- `.env.example`：环境变量模板。
- `README.md`：项目的外部说明文档。
- `requirements-team.txt`：团队锁定依赖清单，用于复刻团队环境。

### 3.2 `saads_wp12/`
这是项目的主 Python 包，未来所有智能体编排代码都会放在这里。

### 3.3 `saads_wp12/graphs/`
存放 LangGraph 图结构定义：
- `main_graph.py`：总控主图
- `subgraphs/`：三个子图

### 3.4 `saads_wp12/nodes/`
存放主图中被调用的普通节点函数。一个节点通常只做一类事，例如：
- 情报读取
- 路由
- 校验
- 环境请求准备
- 运行时资产落盘
- 执行
- 证据收集
- 结果持久化

### 3.5 `saads_wp12/skills/`
存放可独立封装和复用的能力模块。当前重点是：
- `aibom_env_build_skill/`：AIBOM + uv 环境构建 skill

### 3.6 `tests/`
放自动化测试。当前阶段先保留 smoke test 的位置。

### 3.7 `runtime_envs/`
运行时生成的本地实验环境目录。未来每个场景会在这里创建独立 workspace。

### 3.8 `artifacts/`
运行结果、证据、输出文件、阶段性 JSON 记录存放处。

### 3.9 `logs/`
放程序运行时日志。

---

## 4. 文件级别职责总表

> 这一部分面向你、队友，以及像 Codex 这样的代码生成/补全工具。
> 对于“当前还没实现”的文件，这里写的是 **目标职责合同（contract）**。

| 文件 | 当前状态 | 在系统中的角色 | 是否已实现 |
|---|---|---|---|
| `.python-version` | 已填写 | 指定项目 Python 版本 | 是 |
| `.gitignore` | 已填写 | 忽略虚拟环境、日志、输出等 | 是 |
| `.env.example` | 已填写 | 环境变量模板 | 是 |
| `README.md` | 已填写基础版 | 项目简要说明 | 是（基础版） |
| `requirements-team.txt` | 已提供 | 团队依赖锁定文件 | 是 |
| `saads_wp12/__init__.py` | 已创建 | 标记主包 | 否（可为空） |
| `saads_wp12/agent.py` | 已创建 | 导出最终 graph 入口 | 否 |
| `saads_wp12/config.py` | 已创建 | 统一读取配置与环境变量 | 否 |
| `saads_wp12/run_local.py` | 已创建 | 本地运行入口 | 否 |
| `saads_wp12/state.py` | 已创建 | 统一定义图共享状态 | 否 |
| `saads_wp12/graphs/main_graph.py` | 已创建 | 主图定义与编译 | 否 |
| `saads_wp12/graphs/subgraphs/threat_understanding.py` | 已创建 | 威胁理解子图 | 否 |
| `saads_wp12/graphs/subgraphs/test_package_generation.py` | 已创建 | 测试包生成子图 | 否 |
| `saads_wp12/graphs/subgraphs/reflection.py` | 已创建 | 反思修复子图 | 否 |
| `saads_wp12/nodes/intel.py` | 已创建 | 情报接入、标准化节点 | 否 |
| `saads_wp12/nodes/routing.py` | 已创建 | 各种路由节点 | 否 |
| `saads_wp12/nodes/validation.py` | 已创建 | 测试包校验节点 | 否 |
| `saads_wp12/nodes/env_build.py` | 已创建 | 环境构建请求准备与 skill 适配 | 否 |
| `saads_wp12/nodes/runtime_assets.py` | 已创建 | 运行时资产落盘节点 | 否 |
| `saads_wp12/nodes/execution.py` | 已创建 | 执行、证据收集、评分节点 | 否 |
| `saads_wp12/nodes/persistence.py` | 已创建 | 结果持久化节点 | 否 |
| `saads_wp12/skills/aibom_env_build_skill/README.md` | 已创建 | 说明 skill 边界与实现目标 | 否（待补充） |
| `tests/test_smoke.py` | 已创建 | 主图最小化冒烟测试 | 否 |

---

## 5. 每个文件的详细功能说明（可供 Codex / 自动化工具理解）

下面采用“文件合同”的方式来描述。格式尽量稳定，便于后续让工具或队友理解。

---

### 5.1 `.python-version`

**类型**：环境配置文件  
**当前用途**：指定当前项目使用 Python 3.11  
**输入**：无  
**输出**：被 `uv` 读取，用于选择项目 Python 解释器  
**跳转/依赖**：被 `uv venv`、`uv run`、`uv pip sync` 间接使用  
**状态**：已完成

---

### 5.2 `.gitignore`

**类型**：版本控制配置文件  
**当前用途**：避免将不必要文件提交到 Git  
**输入**：无  
**输出**：Git 忽略规则  
**跳转/依赖**：Git 读取  
**状态**：已完成

---

### 5.3 `.env.example`

**类型**：环境变量模板文件  
**当前用途**：告诉开发者项目需要哪些环境变量  
**输入**：无  
**输出**：可复制为 `.env` 使用  
**包含变量**：
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `APP_ENV`

**状态**：已完成基础版

---

### 5.4 `README.md`

**类型**：项目说明文档  
**当前用途**：向开发者说明项目是什么、当前做到哪一步  
**输入**：无  
**输出**：项目概览说明  
**状态**：已完成基础版，后续应被更详细版本替换

---

### 5.5 `requirements-team.txt`

**类型**：依赖锁定文件  
**当前用途**：复刻团队一致的 Python 依赖环境  
**输入**：供 `uv pip sync` 读取  
**输出**：在 `.venv` 中安装具体依赖  
**关键依赖**：
- `langgraph==1.0.7`
- `langchain==1.2.8`
- `langchain-openai==1.1.7`
- `google-adk==1.24.0`

**状态**：已完成，由团队提供

---

### 5.6 `saads_wp12/__init__.py`

**类型**：Python 包初始化文件  
**目标用途**：将 `saads_wp12` 标记为可导入 Python 包  
**输入**：无  
**输出**：使其他模块能 `import saads_wp12...`  
**跳转/依赖**：所有子模块导入链  
**建议实现**：可为空或只写 `__all__ = []`

---

### 5.7 `saads_wp12/config.py`

**类型**：配置读取模块  
**目标用途**：统一从环境变量读取配置，避免各文件自行读取 `os.getenv`  
**输入**：`.env` 中的环境变量  
**输出**：
- OpenAI API Key
- Google API Key
- App 环境名称
- 未来可扩展的数据库、日志配置

**被谁调用**：
- `agent.py`
- 未来各 skill / service / model wrapper

**当前建议函数**：
- `get_env(name: str, default: str | None = None) -> str | None`

**状态**：待实现

---

### 5.8 `saads_wp12/state.py`

**类型**：共享状态模型定义文件  
**目标用途**：定义 LangGraph 主图与子图共享的统一 `State`  
**输入**：上游用户输入、图中各节点返回值  
**输出**：统一状态结构定义，例如 `TypedDict`  
**关键字段分组**：
- 基础任务信息：`run_id`, `threat_id`, `scenario_id`, `attack_id`
- 威胁理解：`intel_raw`, `intel_normalized`, `threat_understanding`, `attack_family`
- 测试包：`test_package`, `package_validation`
- 环境构建：`env_build_request`, `env_build_result`, `workspace_path`, `env_status`
- 运行时资产：`runtime_assets_manifest`, `execution_contract`
- 执行与证据：`execution_result`, `evidence_bundle`
- 评分：`score_result`, `verdict`
- 反思：`reflection_result`, `repair_action`, `reflection_round`
- 审计：`risk_flags`, `audit_log`, `stop_reason`

**被谁调用**：
- 所有 graph / node / subgraph 文件

**状态**：待实现

---

### 5.9 `saads_wp12/agent.py`

**类型**：图入口文件  
**目标用途**：导出最终可运行的 `graph` 对象  
**输入**：从 `graphs/main_graph.py` 导入的 `build_main_graph()`  
**输出**：`graph = build_main_graph()`  
**被谁调用**：
- `run_local.py`
- 测试文件
- 未来的 LangGraph dev / Agent Server

**状态**：待实现

---

### 5.10 `saads_wp12/run_local.py`

**类型**：本地运行入口  
**目标用途**：在不接前端、不接远程 server 的情况下，本地调用主图  
**输入**：一个最小化的 demo state，例如：
- `threat_id`
- `scenario_id`
- `attack_id`

**输出**：终端打印主图执行结果  
**被谁调用**：开发者手动运行  
**典型命令**：
- `python -m saads_wp12.run_local`

**状态**：待实现

---

### 5.11 `saads_wp12/graphs/main_graph.py`

**类型**：LangGraph 主图定义文件  
**目标用途**：定义整个系统的总控工作流  
**输入**：`SecurityEvalState`  
**输出**：已编译的主图对象  
**主图目标流程**：
1. `ingest_intel`
2. `normalize_intel`
3. `understand_threat_subgraph`
4. `route_attack_family`
5. `generate_test_package_subgraph`
6. `validate_test_package`
7. `prepare_env_build_request`
8. `run_aibom_env_build_skill`
9. `materialize_runtime_attack_assets`
10. `execute_test`
11. `collect_evidence`
12. `score_result`
13. `reflect_subgraph`
14. `reflection_router`
15. `persist_knowledge`

**条件边（目标）**：
- 环境 ready → 落盘运行时资产
- 环境失败 → 反思子图
- 反思结果为 fix_package → 回测试包子图
- 反思结果为 fix_env → 回环境构建请求
- 反思结果为 fix_runtime_assets → 回运行时资产落盘
- 反思结果为 retrieve_knowledge → 回威胁理解子图
- 反思结果为 done → 持久化并结束

**状态**：待实现

---

### 5.12 `saads_wp12/graphs/subgraphs/threat_understanding.py`

**类型**：LangGraph 子图定义文件  
**目标用途**：把结构化情报翻译成“可测试的威胁理解对象”  
**输入**：
- `intel_normalized`

**输出**：
- `threat_understanding`
- `attack_family`
- `target_surface`
- `threat_hypotheses`
- `missing_knowledge`
- `related_knowledge`

**目标内部节点**：
- `interpret_threat`
- `map_attack_surface`
- `retrieve_related_knowledge`
- `consolidate_understanding`

**状态**：待实现

---

### 5.13 `saads_wp12/graphs/subgraphs/test_package_generation.py`

**类型**：LangGraph 子图定义文件  
**目标用途**：根据威胁理解结果生成抽象测试包 `AttackTestPackage`  
**输入**：
- `threat_understanding`
- `attack_family`
- `target_surface`
- `generation_route`

**输出**：
- `package_fragments`
- `package_review`
- `test_package`
- `package_version`

**目标内部节点**：
- `route_generator`
- `prompt_generator`
- `dialogue_generator`
- `tool_system_generator`
- `rag_generator`
- `other_generator`
- `compose_package`
- `critique_package`
- `finalize_package`

**状态**：待实现

---

### 5.14 `saads_wp12/graphs/subgraphs/reflection.py`

**类型**：LangGraph 子图定义文件  
**目标用途**：在执行与评分之后，诊断失败原因并决定修复方向  
**输入**：
- `package_validation`
- `env_status`
- `execution_result`
- `evidence_bundle`
- `score_result`
- `verdict`

**输出**：
- `failure_summary`
- `root_cause`
- `repair_plan`
- `repair_action`
- `reflection_result`
- `reflection_round`

**目标内部节点**：
- `diagnose_failure`
- `classify_root_cause`
- `propose_repair`
- `decide_repair_action`

**状态**：待实现

---

### 5.15 `saads_wp12/nodes/intel.py`

**类型**：普通节点函数文件  
**目标用途**：处理情报接入与标准化  

**计划包含节点**：
- `ingest_intel(state)`
- `normalize_intel(state)`

**`ingest_intel` 输入**：
- `threat_id`
- 或外部传入的 `intel_raw`

**`ingest_intel` 输出**：
- `run_id`
- `threat_id`
- `intel_raw`
- 初始化的 `reflection_round`
- 初始化 `audit_log`

**`normalize_intel` 输入**：
- `intel_raw`

**`normalize_intel` 输出**：
- `intel_normalized`
- `risk_flags`
- `audit_log`

**状态**：待实现

---

### 5.16 `saads_wp12/nodes/routing.py`

**类型**：普通节点函数文件  
**目标用途**：集中放各种路由逻辑  

**计划包含函数**：
- `route_attack_family(state)`
- `route_after_env_build(state)`
- `reflection_router(state)`

**输入/输出合同**：
- `route_attack_family`：输入 `attack_family`，输出 `generation_route`
- `route_after_env_build`：输入 `env_status`，输出下一节点名
- `reflection_router`：输入 `repair_action` 和 `reflection_round`，输出下一节点名

**状态**：待实现

---

### 5.17 `saads_wp12/nodes/validation.py`

**类型**：普通节点函数文件  
**目标用途**：校验测试包是否合法、完整  

**计划包含节点**：
- `validate_test_package(state)`

**输入**：
- `test_package`

**输出**：
- `package_validation`，至少包含：
  - `valid`
  - `missing_fields`

**关键校验项**：
- `package_id`
- `attack_family`
- `target_surface`
- `objective`
- `success_criteria`
- `evidence_hooks`

**状态**：待实现

---

### 5.18 `saads_wp12/nodes/env_build.py`

**类型**：普通节点函数文件（连接主图与 env skill）  
**目标用途**：
1. 把主图 state 适配为环境构建 skill 的输入
2. 调用 `aibom_env_build_skill`

**计划包含节点**：
- `prepare_env_build_request(state)`
- `run_aibom_env_build_skill(state)`

**`prepare_env_build_request` 输入**：
- `tenant_id`
- `scenario_id`
- `attack_id`
- `aibom_components`
- `seed_asset_ids`
- `test_package`

**`prepare_env_build_request` 输出**：
- `env_build_request`

**`run_aibom_env_build_skill` 输入**：
- `env_build_request`

**`run_aibom_env_build_skill` 输出**：
- `env_build_result`
- `environment_id`
- `workspace_path`
- `entry_command`
- `resolved_components`
- `env_artifacts`
- `env_status`
- `env_warnings`
- `env_errors`
- `env_version`

**状态**：待实现

---

### 5.19 `saads_wp12/nodes/runtime_assets.py`

**类型**：普通节点函数文件  
**目标用途**：把抽象测试包落成运行时文件  

**计划包含节点**：
- `materialize_runtime_attack_assets(state)`

**输入**：
- `test_package`
- `workspace_path`
- `entry_command`
- `env_build_result`

**输出**：
- `runtime_assets_manifest`
- `execution_contract`

**典型落盘内容**：
- `assets/payloads.json`
- `scripts/run_attack.py`
- `configs/*.yaml`
- dialogue / tool 配置文件

**状态**：待实现

---

### 5.20 `saads_wp12/nodes/execution.py`

**类型**：普通节点函数文件  
**目标用途**：执行攻击、收集证据、生成评分  

**计划包含节点**：
- `execute_test(state)`
- `collect_evidence(state)`
- `score_result(state)`

**`execute_test` 输入**：
- `workspace_path`
- `execution_contract`

**`execute_test` 输出**：
- `execution_result`
- `traces`
- `artifacts`

**`collect_evidence` 输入**：
- `execution_result`
- `traces`
- `artifacts`
- `test_package`

**`collect_evidence` 输出**：
- `evidence_bundle`

**`score_result` 输入**：
- `test_package`
- `evidence_bundle`

**`score_result` 输出**：
- `score_result`
- `verdict`

**状态**：待实现

---

### 5.21 `saads_wp12/nodes/persistence.py`

**类型**：普通节点函数文件  
**目标用途**：把本轮运行结果保存到 `artifacts/` 或数据库  

**计划包含节点**：
- `persist_knowledge(state)`

**输入**：
- `run_id`
- `threat_id`
- `attack_family`
- `verdict`
- `score_result`
- `reflection_result`

**输出**：
- 更新后的 `audit_log`
- 本地 JSON 文件或未来数据库写入结果

**状态**：待实现

---

### 5.22 `saads_wp12/skills/aibom_env_build_skill/__init__.py`

**类型**：skill 包初始化文件  
**目标用途**：标记该目录为 skill 包  
**输入**：无  
**输出**：供后续 skill 内模块导入  
**状态**：待实现/可为空

---

### 5.23 `saads_wp12/skills/aibom_env_build_skill/README.md`

**类型**：skill 说明文档  
**目标用途**：描述该 skill 的职责边界  
**应说明内容**：
- 输入 schema
- 输出 schema
- 与 `env_build.py` 的关系
- 只负责环境构建，不负责整体编排
- 不做多智能体推理

**状态**：待完善

---

### 5.24 `tests/test_smoke.py`

**类型**：自动化测试文件  
**目标用途**：验证主图最小流程是否能跑通  
**输入**：最小 demo state  
**输出**：断言结果，例如：
- `verdict == pass`
- `env_status == ready`
- `package_validation['valid'] is True`

**状态**：待实现

---

## 6. 当前已经完成了哪些工作

### 已完成
- 环境路线已定：项目使用 Python 3.11 虚拟环境，不直接用系统 Python 3.14。
- 团队依赖环境已根据 `requirements-team.txt` 作为基线进行准备。
- 工程目录树已创建完毕。
- 基础文档和模板文件已建立：
  - `.gitignore`
  - `.env.example`
  - `README.md`
- 所有后续要实现的 `.py` 文件都已经建好位置，工程骨架清晰。

### 尚未完成
- 尚未编写任何主图代码。
- 尚未编写任何子图代码。
- 尚未编写任何节点函数。
- 尚未实现 `State`。
- 尚未写冒烟测试。
- 尚未跑通本地 demo。
- 尚未接入真实的 AIBOM 环境构建 skill。

---

## 7. 下一步应该完成哪些工作

建议按下面顺序继续推进：

### 第 1 批：写最小可运行骨架
优先实现：
1. `state.py`
2. `graphs/main_graph.py`
3. `agent.py`
4. `run_local.py`

目标：让主图对象能被创建出来。

### 第 2 批：写普通节点
优先实现：
1. `nodes/intel.py`
2. `nodes/routing.py`
3. `nodes/validation.py`
4. `nodes/env_build.py`
5. `nodes/runtime_assets.py`
6. `nodes/execution.py`
7. `nodes/persistence.py`

目标：先写“假逻辑/占位逻辑”，让主流程跑通一次。

### 第 3 批：写三个子图
1. `graphs/subgraphs/threat_understanding.py`
2. `graphs/subgraphs/test_package_generation.py`
3. `graphs/subgraphs/reflection.py`

目标：把多智能体子图先以“占位逻辑子图”形式跑起来。

### 第 4 批：写冒烟测试
实现 `tests/test_smoke.py`，验证：
- 主图能执行
- demo 能跑通
- 输出字段完整

### 第 5 批：替换为真实能力
逐步替换掉：
- 假威胁理解
- 假测试包生成
- 假环境构建
- 假执行/评分

---

## 8. 对 Codex / 自动化工具的附加说明

下面这段可以直接提供给自动化代码工具：

### 工程意图摘要
- 这是一个基于 LangGraph 的多阶段安全评测编排项目。
- 外层是固定主图，负责生命周期推进。
- 内层有 3 个子图：
  - threat understanding
  - test package generation
  - reflection
- AIBOM 环境构建是独立 skill，不是多智能体子图。
- 测试包与运行时资产必须分离。
- 所有节点都围绕统一的 `SecurityEvalState` 读写。

### 编码优先级
1. 先实现最小可运行 demo
2. 所有文件先写最小实现，不要一次写复杂逻辑
3. 所有节点函数都返回 `dict`
4. 所有图最后都要 `compile()`
5. 子图可以先是顺序固定的占位逻辑
6. 环境构建节点先返回模拟成功结果，后面再接真实 skill

### 风格要求
- 文件职责单一
- 节点函数命名清晰
- 每个节点只做一件事
- 返回字段名称必须与 `SecurityEvalState` 保持一致
- 所有新增字段都先写入 `state.py`

---

## 9. 当前阶段的结论

你现在已经完成了最容易被忽视但非常重要的一步：

**把“想法”变成了“可施工的工程骨架”。**

这意味着：
- 环境有了
- 目录有了
- 文件位点有了
- 职责边界有了
- 后续实现顺序也有了

下一阶段的工作重点，将从“建架子”转为“往架子里逐步填代码”。
