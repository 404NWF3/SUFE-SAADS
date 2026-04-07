# saads-wp12

AIBOM-aware LLM Security Evaluation Orchestrator

---

## 项目简介

本项目旨在搭建一个 **面向大模型安全测试的智能体编排系统**。系统的核心目标不是单纯生成攻击脚本，而是构建一个完整的安全评测闭环：

1. 接收上游威胁情报
2. 理解威胁并识别攻击面
3. 生成抽象测试包（AttackTestPackage）
4. 基于 AIBOM 与 seed assets 构建可运行实验环境
5. 将抽象测试包落为运行时资产
6. 执行攻击测试
7. 收集证据并评分
8. 反思失败原因并决定是否回环修复
9. 将结果持久化沉淀

系统架构遵循以下原则：
- **外层用 LangGraph 主图固定流程**
- **高不确定性模块才使用子图/多智能体**
- **环境构建作为独立 skill，而不是多智能体**
- **测试包与运行时资产分离**
- **所有节点围绕统一 State 读写**

---

## 当前阶段状态

当前处于：**阶段 0：环境和工程骨架初始化**

### 已完成
- 已确认开发机具备：
  - VS Code
  - uv
  - 系统 Python
- 已决定项目使用 **Python 3.11 虚拟环境**，避免直接使用系统 Python 3.14 导致依赖兼容风险。
- 已采用团队提供的 `requirements-team.txt` 作为环境基线。
- 已创建项目目录结构。
- 已创建所有主文件、子图文件、节点文件、skill 目录和测试目录。
- 已填写基础配置文件：
  - `.gitignore`
  - `.env.example`
  - `README.md`

### 未完成
- 尚未实现 `state.py`
- 尚未实现 `main_graph.py`
- 尚未实现任何子图逻辑
- 尚未实现任何普通节点逻辑
- 尚未实现 smoke test
- 尚未跑通本地 demo

---

## 当前目录结构

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

## 架构概览

### 主图目标流程

```text
START
  ↓
ingest_intel
  ↓
normalize_intel
  ↓
understand_threat_subgraph
  ↓
route_attack_family
  ↓
generate_test_package_subgraph
  ↓
validate_test_package
  ↓
prepare_env_build_request
  ↓
run_aibom_env_build_skill
  ├─ ready   → materialize_runtime_attack_assets
  └─ failed  → reflect_subgraph

materialize_runtime_attack_assets
  ↓
execute_test
  ↓
collect_evidence
  ↓
score_result
  ↓
reflect_subgraph
  ↓
reflection_router
  ├─ fix_package        → generate_test_package_subgraph
  ├─ fix_env            → prepare_env_build_request
  ├─ fix_runtime_assets → materialize_runtime_attack_assets
  ├─ retrieve_knowledge → understand_threat_subgraph
  └─ done               → persist_knowledge
                              ↓
                             END
```

### 三个核心子图

1. **Threat Understanding Subgraph**
   - 负责把结构化情报翻译成可测试威胁对象
2. **Test Package Generation Subgraph**
   - 负责生成抽象测试包 `AttackTestPackage`
3. **Reflection Subgraph**
   - 负责分析失败原因并决定修复方向

### 独立 skill

- **AIBOM Env Build Skill**
  - 负责环境构建
  - 不负责整体编排
  - 不负责推理
  - 不做多智能体协商

---

## 各目录用途

### `saads_wp12/`
主 Python 包，所有核心逻辑都位于此。

### `saads_wp12/graphs/`
放 LangGraph 图定义。

### `saads_wp12/graphs/subgraphs/`
放三个子图定义。

### `saads_wp12/nodes/`
放普通节点函数。

### `saads_wp12/skills/`
放独立 skill。

### `tests/`
放自动化测试。

### `runtime_envs/`
放运行时生成的实验环境 workspace。

### `artifacts/`
放执行结果、证据、导出 JSON。

### `logs/`
放日志文件。

---

## 关键文件说明

### `state.py`
统一定义 `SecurityEvalState`，是整个 LangGraph 系统的共享状态。

### `main_graph.py`
定义总控主图，组织所有节点和条件边。

### `agent.py`
导出最终 graph 入口。

### `run_local.py`
用最小 demo state 在本地运行主图。

### `nodes/intel.py`
实现 `ingest_intel` 与 `normalize_intel`。

### `nodes/routing.py`
实现：
- 攻击家族路由
- 环境后路由
- 反思后路由

### `nodes/validation.py`
实现 `validate_test_package`。

### `nodes/env_build.py`
实现：
- `prepare_env_build_request`
- `run_aibom_env_build_skill`

### `nodes/runtime_assets.py`
实现：
- `materialize_runtime_attack_assets`

### `nodes/execution.py`
实现：
- `execute_test`
- `collect_evidence`
- `score_result`

### `nodes/persistence.py`
实现：
- `persist_knowledge`

### `graphs/subgraphs/threat_understanding.py`
实现威胁理解子图。

### `graphs/subgraphs/test_package_generation.py`
实现测试包生成子图。

### `graphs/subgraphs/reflection.py`
实现反思修复子图。

### `skills/aibom_env_build_skill/`
未来接入你队友负责的环境构建能力。

---

## 下一步工作计划

### 阶段 1：写最小可运行骨架
目标：让主图能被成功创建并导出

优先实现：
1. `state.py`
2. `main_graph.py`
3. `agent.py`
4. `run_local.py`

### 阶段 2：写普通节点的占位逻辑
目标：即使逻辑是假的，也先让整个闭环跑起来

实现：
1. `intel.py`
2. `routing.py`
3. `validation.py`
4. `env_build.py`
5. `runtime_assets.py`
6. `execution.py`
7. `persistence.py`

### 阶段 3：写三个子图的占位版本
目标：让主图 + 子图闭环完整可执行

实现：
1. `threat_understanding.py`
2. `test_package_generation.py`
3. `reflection.py`

### 阶段 4：写 smoke test
目标：确认最小 demo 可以自动化验证

实现：
- `tests/test_smoke.py`

### 阶段 5：替换为真实逻辑
逐步替换：
- 假威胁理解 → 真实威胁理解
- 假测试包生成 → 真实测试包生成
- 假环境构建 → 真实 AIBOM env skill
- 假执行 → 真实 runtime 与 evidence pipeline

---

## 当前阶段的验收标准

当前阶段的验收重点不是“代码是否跑通”，而是“工程骨架是否清晰、是否可继续施工”。

本阶段完成的标准：
- 有独立 Python 3.11 项目环境
- 有团队依赖基线
- 有完整目录树
- 有每个文件的落点
- 有清晰的下一阶段施工顺序

---

## 面向后续协作的说明

这个项目后续适合按模块并行推进：

- 一人负责主图与状态
- 一人负责三个子图
- 一人负责 AIBOM 环境 skill
- 一人负责执行、证据与评分

同时要求：
- 所有状态字段先写入 `state.py`
- 所有节点函数只返回字典
- 所有图都通过 `compile()` 导出
- 所有文件先做最小实现，再逐步替换为真实能力

---

## 结论

到目前为止，我们已经完成了最关键的基础工作：

**把项目从“只有想法”推进到了“可以继续施工的工程骨架阶段”。**

接下来就进入真正的代码落地阶段：

1. 先写 State
2. 再写主图
3. 再写普通节点
4. 再写三个子图
5. 最后跑通 demo 并逐步接入真实能力
