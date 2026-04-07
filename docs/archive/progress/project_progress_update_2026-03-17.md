# WP1-2 阶段进展同步（2026-03-17）

## 1. 文档定位

本文档用于同步 `WP1-2` 当前阶段已经完成的关键能力，重点记录：

- 主流程现在已经做到哪一步
- `threat_understanding` 子图已经增强到什么程度
- `reflection` 子图已经如何利用不确定性信息做回环判断
- 当前自动化验证已经覆盖了哪些行为

这份文档是对既有项目总结文档的补充更新，避免阶段信息只散落在聊天记录中。

## 2. 当前总体状态

截至当前，`WP1-2` 已经从“工程骨架搭建阶段”进入 **最小可运行原型 + 关键子图质量增强阶段**。

当前系统已经具备：

1. 可运行的 LangGraph 主流程。
2. mock 输入层与本地 artifact 持久化。
3. 多次执行与通过率判定机制。
4. 第一个可切换的 LLM 子图入口。
5. `threat_understanding` 的结构化测试导向输出。
6. `reflection` 对威胁理解不确定性的回溯判断。

## 3. 主流程已完成的能力

当前主图已经可以完整运行以下链路：

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
14. `persist_knowledge`

这意味着当前项目已经不是“只有文档和目录”，而是一个能从输入跑到结果落盘的原型系统。

## 4. threat_understanding 子图的最新进展

### 4.1 角色定位

`threat_understanding` 不再被当作“重复数据库已有结构化情报”的步骤，而是被正式定位为：

**把上游结构化威胁情报加工成后续测试包生成可直接消费的测试导向威胁理解对象。**

### 4.2 当前输出结构

当前已稳定输出：

- `threat_understanding`
  - `threat_summary`
  - `attack_mechanism`
  - `taxonomy`
  - `target_surface`
  - `exploit_preconditions`
  - `test_focus`
  - `expected_failure_modes`
  - `recommended_test_strategy`
  - `usable_seed_assets`
- 顶层辅助字段
  - `attack_family`
  - `target_surface`
  - `confidence`
  - `candidate_families`
  - `classification_rationale`
  - `missing_knowledge`

### 4.3 已完成的增强

当前已经完成以下增强：

1. 分类不再只依赖 taxonomy，而会综合：
   - taxonomy
   - summary
   - `asset_type`
   - seed asset 特征

2. 已支持候选攻击家族：
   - `candidate_families`

3. 已支持整体可信度：
   - `confidence`

4. 已支持分类依据输出：
   - `classification_rationale`

5. 已支持结构化知识缺口表达：
   - `seed_asset_detail`
   - `component_context`
   - `asset_quality`
   - `classification_conflict`
   - `confidence_gap`

6. 已实现 `missing_knowledge` 对 `confidence` 的联动修正。

### 4.4 已完成的样例验证

当前已验证的代表性样例包括：

- `atk-001`
  - 标准 prompt injection
  - 分类与测试导向内容合理

- `atk-002`
  - 多轮对话操纵
  - 已从早期误判修正为 `long_horizon_dialogue`
  - 且测试导向内容已随最终分类同步切换

- `atk-003`
  - tool hijack
  - 分类与测试导向内容合理

- `atk-004`
  - 信息不足 + draft 资产
  - 能显式产出 `missing_knowledge`
  - `confidence` 已被明显压低

- `atk-005`
  - taxonomy 与语义冲突
  - 能表达候选家族接近、分类冲突和低置信度

- `atk-006`
  - 工具攻击方向较稳但资产质量不足
  - 能区分“分类较稳”和“输入资产质量不足”是两类不同问题

## 5. reflection 子图的最新进展

### 5.1 新增能力

`reflection` 已从“执行失败后统一 fix_package”的简单版本，升级为会利用威胁理解不确定性信息做根因判断的版本。

当前它已经会读取：

- `confidence`
- `candidate_families`
- `missing_knowledge`
- `package_validation`
- `env_status`
- `verdict`

### 5.2 当前回环判断逻辑

当前规则版反思逻辑已支持：

1. 测试包无效：
   - `repair_action = fix_package`

2. 环境未 ready：
   - `repair_action = fix_env`

3. 执行失败，且威胁理解不稳：
   - `confidence < 0.6`
   - 或存在 `classification_conflict`
   - 或存在 `confidence_gap`
   - 或候选家族差距过小

   则输出：
   - `repair_action = revisit_threat_understanding`
   - `root_cause = threat_understanding_uncertain`

4. 已接入反思轮数控制：
   - `reflection_round`
   - `max_reflection_rounds`
   - 上限耗尽时写入 `stop_reason = max_reflection_rounds_exhausted`

### 5.3 当前主图回跳路由

当前主图已接通以下反思回跳：

- `revisit_threat_understanding -> understand_threat_subgraph`
- `fix_package -> generate_test_package_subgraph`
- `fix_env -> prepare_env_build_request`
- 达到轮数上限或 `done -> persist_knowledge`

这意味着系统已经开始具备“如果后续测试效果不佳，不只修测试包，也会回头怀疑威胁理解”的能力。

## 6. 当前自动化验证情况

当前已通过的自动化验证包括：

### 6.1 最小主流程 smoke test

验证内容：

- 主图能完整跑通
- `env_status == ready`
- `verdict == pass`
- 通过率统计正确
- 结果可落盘

### 6.2 低置信度失败回跳测试

验证内容：

- 低置信度场景下执行失败
- `reflection` 会优先输出 `revisit_threat_understanding`
- 达到最大反思轮数后优雅结束

## 7. 当前仍未完成的部分

截至当前，仍未完成或尚处于占位/模拟状态的部分包括：

1. 真实数据库接入。
2. `test_package_generation` 基于 `confidence / missing_knowledge` 的保守生成策略。
3. 更深度的 LLM 接入与 prompt 调优。
4. 真实 `aibom_env_build_skill` 集成。
5. 真实执行器、真实证据收集和更真实的评分逻辑。

## 8. 当前阶段结论

可以将当前阶段准确表述为：

**WP1-2 已经成为一个可运行的 LangGraph 编排型安全评测原型；其中 `threat_understanding` 与 `reflection` 两个关键高不确定性模块，已经开始具备“结构化推理、不确定性表达与回环修正”的能力。**
