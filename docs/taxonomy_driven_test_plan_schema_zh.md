# 面向 OWASP-LLM-01~10 的优质测试方案 Schema 与完成标准

这份文档定义 WP1-2 当前阶段的核心目标：

**优先生成高质量测试方案；只有在信息充分时，才进一步生成测试脚本。**

因此，项目当前的主产物不再是“攻击脚本”或“运行蓝图”，而是：

**一份结构化、可评审、可执行思路清晰、风险边界明确的测试方案。**


## 1. 当前阶段的主线

当前系统主线如下：

1. 从数据库按 `OWASP-LLM-01` 到 `OWASP-LLM-10` 的 `taxonomy_code` 拉取情报
2. 基于 taxonomy + threat context 理解这条情报最值得验证的风险点
3. 生成高质量测试方案
4. 仅在执行条件充分时，再进一步生成测试脚本和运行资产

当前阶段的核心评估问题不是：

- 能不能立刻跑脚本

而是：

- 这条情报能不能被转换成一个**有价值的测试方案**


## 2. 设计原则

### 2.1 方案优先

测试方案是主产物，脚本是条件性附属产物。

这意味着：

- 即使没有足够 AIBOM / seed asset / runtime 条件
- 系统也应该能生成一份高质量的测试方案

### 2.2 taxonomy 驱动

当前数据库入口已经以 `OWASP-LLM-01~10` 为主线。

因此方案生成必须同时回答两个问题：

1. **这条情报在当前 taxonomy 下最值得验证的核心风险是什么**
2. **在当前 family 下，应该采取什么测试形态**

所以后续生成逻辑必须是：

- `taxonomy_code` 决定测试主题
- `attack_family` 决定测试形态
- `AIBOM` 决定是否允许从方案继续落地到脚本

### 2.3 降级优先于编造

如果信息不足，系统必须：

- 降级为 `conservative` 或 `triage`
- 明确记录 `known_gaps` 和 `recommended_follow_up`

而不是：

- 编造不存在的 AIBOM
- 编造不存在的 seed asset
- 强行输出一个看起来“很完整”的执行型包


## 3. 方案层级

### 3.1 `triage`

适用场景：

- out-of-scope
- taxonomy 虽命中，但当前情报不足以形成可信测试设计
- threat understanding 无法稳定聚焦测试目标

目标：

- 解释为什么当前不适合进入更强测试方案
- 明确需要补什么信息

### 3.2 `conservative`

适用场景：

- in-scope
- taxonomy 风险主题基本清楚
- 但 AIBOM / seed asset / component / confidence 仍不足

目标：

- 给出谨慎验证型测试方案
- 说明如何先用低风险方式验证核心假设
- 说明什么条件下才值得升级

### 3.3 `standard`

适用场景：

- in-scope
- taxonomy 风险主题清楚
- 攻击假设稳定
- AIBOM / component / asset 条件足够

目标：

- 给出完整测试方案
- 明确步骤、证据、判断点
- 若条件允许，可顺带提供脚本生成所需附属信息


## 4. 优质测试方案的核心字段

下面这些字段是当前阶段的**方案核心字段**。后续 `TestPackageGeneration` 应优先围绕这些字段设计。

### 4.1 `objective`

这条方案的核心测试目标。

要求：

- 必须具体
- 必须指向一个明确的验证目标
- 不能只是“测试该攻击”这种空泛表述

示例：

- 验证外部可控上下文是否会在 `OWASP-LLM-01` 风险场景下覆盖系统预期行为

### 4.2 `taxonomy_risk_statement`

说明当前方案是从哪个 `OWASP-LLM-0X` 风险主题出发，以及该主题在当前情报中的体现。

要求：

- 必须显式引用当前 taxonomy
- 必须把 taxonomy 风险和这条情报联系起来

### 4.3 `attack_hypothesis`

明确要验证的攻击假设。

要求：

- 必须可检验
- 必须和 taxonomy 风险主题一致
- 必须能导出测试步骤和证据计划

### 4.4 `test_strategy`

描述整体测试策略。

要求：

- 说明为什么选择当前策略
- 说明这是 prompt-like、dialogue-like 还是 tool-like 方案
- 说明为什么这种策略最适合当前 taxonomy 和情报

### 4.5 `preconditions`

列出测试成立所需前提。

要求：

- 必须明确
- 不允许把不存在的条件写成已满足
- 应区分“已满足”和“待补充”

### 4.6 `test_steps`

描述测试步骤。

要求：

- 应该是清晰的测试流程
- 重点是验证逻辑，而不是脚本细节
- 对 `conservative` 和 `standard` 应该有明显差异

### 4.7 `evidence_plan`

描述要收集什么证据来支持判断。

要求：

- 必须和 `attack_hypothesis` 对应
- 不能只是“收集日志”
- 应说明证据如何证明或反驳假设

### 4.8 `decision_points`

描述方案中的判断点。

要求：

- 明确什么条件下继续
- 明确什么条件下停止
- 明确什么条件下升级为更强方案

### 4.9 `risk_boundary`

描述测试边界和安全约束。

要求：

- 说明哪些动作不应执行
- 说明哪些前提缺失时必须停下
- 尤其对 `conservative` 和 `triage` 更重要

### 4.10 `recommended_follow_up`

描述下一步动作。

要求：

- 必须和 `known_gaps` 对应
- 必须具体
- 不能只是“继续分析”


## 5. 条件性附属字段

下面这些字段在当前阶段不应再作为主评价对象，而应视为**可选附属字段**。

只有在执行条件充分时，它们才需要完整生成。

- `payload_plan`
- `execution_plan.runner_command_template`
- `script_blueprint`
- `target_artifacts`
- runtime-specific `file_plan`

这些字段的定位应该是：

**当测试方案已经足够清楚且执行条件允许时，用于辅助后续脚本生成。**

而不是：

**先决定脚本怎么写，再倒推方案。**


## 6. taxonomy 与 family 的关系

后续方案生成必须采用“双锚点”思路。

### 6.1 taxonomy 决定“测试主题”

例如：

- 当前记录命中 `OWASP-LLM-01`
- 那么方案必须围绕 `Prompt Injection` 风险主题构建

### 6.2 family 决定“测试形态”

例如：

- `prompt_injection`
- `long_horizon_dialogue`
- `tool_hijack`

family 不应取代 taxonomy，而应补充 taxonomy。

### 6.3 AIBOM 决定“能否继续落地”

AIBOM 的作用不是决定是否值得生成方案，而是决定：

- 能否从方案继续下沉到脚本生成
- 能否进入 `env_build / runtime_assets / execution`


## 7. triage / conservative / standard 的完成标准

### 7.1 triage 方案完成标准

一个合格的 `triage` 方案必须：

- 清楚说明为什么当前不能进入更强方案
- 清楚说明当前 taxonomy 风险主题是什么
- 清楚说明缺失的信息是什么
- 给出明确的 follow-up

### 7.2 conservative 方案完成标准

一个合格的 `conservative` 方案必须：

- 明确攻击假设
- 明确低风险验证策略
- 明确证据采集方式
- 明确升级条件
- 明确不应该做什么

### 7.3 standard 方案完成标准

一个合格的 `standard` 方案必须：

- 明确 taxonomy 风险主题
- 明确核心攻击假设
- 明确测试步骤
- 明确证据与判断点
- 明确安全边界
- 在条件允许时，可附带脚本生成所需信息


## 8. 当前阶段建议保留的工程底座

以下模块仍然适合保持规则/工程护栏角色：

- `validation`
- `routing`
- `runtime_assets`
- `execution`
- AIBOM gate

以下模块应优先面向 LLM 与方案质量优化：

- `ThreatUnderstanding`
- `TestPackageGeneration`
- `LLM prompt assets`


## 9. 这份 schema 对后续改动的直接指导

### 9.1 对 `ThreatUnderstanding`

应逐步增强为更服务“测试方案生成”的输出，例如：

- `taxonomy_test_focus`
- `primary_test_question`
- `planning_constraints`
- `why_not_execute_yet`

### 9.2 对 `TestPackageGeneration`

应逐步把输出重心从：

- runtime blueprint
- runner command
- file plan

迁移到：

- test strategy
- test steps
- evidence plan
- decision points
- risk boundary

### 9.3 对 `validation`

应逐步从“检查 package 是否像执行包”转向：

- 检查方案是否具体
- 检查假设是否可检验
- 检查证据计划是否有效
- 检查 follow-up 是否对应 known gaps


## 10. 阶段 1 的验收标准

阶段 1 完成后，应满足下面这几点：

1. 系统内部对“测试方案优先、脚本附属”已经有统一定义
2. 已有一份明确 schema 可指导代码改造
3. 后续 prompt、generator、validation 都能对齐这份 schema
4. triage / conservative / standard 的目标区别已清楚
5. taxonomy / family / AIBOM 三者分工已清楚


## 11. 一句话总结

当前阶段，WP1-2 的核心不再是“尽快生成脚本”，而是：

**围绕 OWASP-LLM-01~10 的 taxonomy 风险主题，稳定生成高质量测试方案；脚本生成仅在条件充分时作为附属能力下沉。**
