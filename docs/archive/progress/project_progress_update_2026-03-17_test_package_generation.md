# WP1-2 阶段进展同步：Test Package Generation 升级（2026-03-17）

## 1. 本次更新目的

本文档用于记录 `WP1-2` 在 `test_package_generation` 子图上的最新阶段性进展。

本次更新重点不是“又能跑一条链路”，而是把该子图从：

- 单一规则模板生成

升级为：

- 单子图
- 多攻击类型 generator
- 基于不确定性信息的模式切换

也就是说，当前 `test_package_generation` 已经开始具备真正可扩展的内部结构，而不再只是一个大函数里拼一个包。

## 2. 更新前的问题

在本次更新之前，`test_package_generation` 存在两个明显局限：

1. 所有攻击类型共用同一套生成逻辑。
2. 虽然前面的 `threat_understanding` 已经产出：
   - `confidence`
   - `candidate_families`
   - `missing_knowledge`

   但这些信息还没有真正影响到测试包设计。

这会导致一个问题：

- 上游已经知道“当前理解不够稳”
- 但测试包生成仍然一律按高确定性方案输出

这与前面已经完成的不确定性表达能力是不一致的。

## 3. 本次更新后的架构

本次更新后，`test_package_generation` 已正式收敛为三层结构：

### 3.1 Family Generator 层

按攻击家族拆分 family-specific 生成器：

- `PromptInjectionGenerator`
- `LongHorizonDialogueGenerator`
- `ToolHijackGenerator`

这些 generator 的职责是：

- 为不同攻击类型提供更贴合该类型的测试目标
- 生成更符合该类型的 `success_criteria`
- 生成更符合该类型的 `evidence_hooks`

### 3.2 Generation Mode 层

在 family-specific 方案之上，再根据上游不确定性信息叠加生成模式：

- `standard`
- `conservative`

其中：

- `standard`
  - 适用于高置信度、信息较完整场景
- `conservative`
  - 适用于低置信度、信息不足、分类冲突等场景

### 3.3 Final Package Assembly 层

最后由统一的组装层输出标准化 `test_package`，确保：

- 下游 `validation`
- `runtime_assets`
- `execution`

都能继续消费统一 schema，而不需要关心内部到底用了哪个 generator。

## 4. 当前 generator 划分

当前已实现的 family generator 如下：

### 4.1 PromptInjectionGenerator

适用于：

- `prompt_injection`

特点：

- 默认关注检索上下文或外部内容注入
- `evidence_hooks` 包含 `retrieval_trace`

### 4.2 LongHorizonDialogueGenerator

适用于：

- `long_horizon_dialogue`

特点：

- 更强调多轮对话状态变化
- `success_criteria` 会显式加入对对话状态逐步偏移的观测
- `evidence_hooks` 包含 `dialogue_transcript`

### 4.3 ToolHijackGenerator

适用于：

- `tool_hijack`

特点：

- 更强调工具调用是否被操控
- `success_criteria` 会显式关注 tool invocation 结果
- `evidence_hooks` 包含 `tool_call_trace`

## 5. 当前保守生成逻辑

本次更新已使 `test_package_generation` 真正开始利用：

- `confidence`
- `candidate_families`
- `missing_knowledge`

来决定是否走保守生成。

### 5.1 当前进入 conservative 的条件

当满足以下任一条件时，会进入 `generation_mode = conservative`：

1. `confidence < 0.75`
2. `missing_knowledge` 中出现以下关键缺口之一：
   - `seed_asset_detail`
   - `component_context`
   - `classification_conflict`
   - `confidence_gap`
3. 前两名候选攻击家族的置信度差距过小

### 5.2 conservative 模式下的行为

当前 conservative 模式会执行以下调整：

1. `objective`
   - 不再直接进入高特异性攻击设计
   - 改为优先验证当前威胁理解假设是否成立

2. `payload_plan`
   - 标记为更保守的使用方式
   - 避免默认直接按高风险路径执行

3. `success_criteria`
   - 除原始测试重点外，还会增加：
     - 验证 target surface 是否与当前理解一致
     - 收集能够区分候选攻击家族的证据

4. `failure_signals`
   - 增加“实际行为更像其它候选家族”的失败信号

5. `safety_constraints`
   - 明确要求先采用低风险 payload
   - 避免不可逆动作与过强假设

## 6. 当前 test_package 输出结构

当前 `test_package` 结构至少包含：

```python
{
  "package_id": "...",
  "attack_family": "...",
  "target_surface": "...",
  "objective": "...",
  "preconditions": [...],
  "payload_plan": [...],
  "success_criteria": [...],
  "failure_signals": [...],
  "evidence_hooks": [...],
  "safety_constraints": [...],
  "generation_mode": "...",
  "metadata": {...}
}
```

### 6.1 metadata 当前已记录

`metadata` 当前已保留以下关键上下文：

- `threat_summary`
- `attack_mechanism`
- `confidence`
- `candidate_families`
- `missing_knowledge`
- `classification_rationale`
- `generation_mode`
- `generator_name`

这意味着后续如果测试失败，可以回头分析：

- 当前包到底是哪个 generator 生成的
- 是不是本来就处于 conservative 模式
- 失败是否与 threat understanding 的不稳定有关

## 7. 这次更新的核心意义

这次更新最重要的，不是“多加了几个类”，而是把 `test_package_generation` 的复杂性来源区分清楚了：

### 7.1 按攻击类型拆

用 **多 generator** 解决：

- prompt injection
- long-horizon dialogue
- tool hijack

之间测试设计逻辑不同的问题。

### 7.2 按理解可靠性调强弱

用 **generation mode** 解决：

- 高置信度时可以直接设计更明确的测试方案
- 低置信度时应该更保守、更重视证据区分

这说明当前系统已经开始具备：

**根据上游认知可靠性调整下游测试设计强度**

这一关键能力。

## 8. 当前自动化验证

本次更新后，已完成以下验证：

### 8.1 最小主流程 smoke test

仍然通过，说明本次结构升级没有打坏既有闭环。

### 8.2 低置信度 conservative 生成测试

已验证：

- `atk-005` 这类低置信度、分类冲突场景
- 会生成 `generation_mode = conservative`

### 8.3 tool_hijack family generator 测试

已验证：

- `atk-003` 会走 `tool_system_generator`
- `evidence_hooks` 中会包含 `tool_call_trace`

这说明 family-specific generator 已开始真实发挥作用。

## 9. 当前阶段结论

可以将这次更新的结果概括为：

**`test_package_generation` 已从单一规则模板升级为“单子图 + 多 generator + 不确定性驱动模式切换”的结构。**

这一步非常关键，因为它为后续两件事打下了基础：

1. 以后继续支持更多攻击类型时，可以直接新增 family generator。
2. 以后如果某一类 generator 需要接入 LLM，也可以只替换该 generator，而不必重写整个子图。

## 10. 下一步建议

本次更新之后，最自然的下一个推进方向有两个：

1. 继续往下推进 `runtime_assets`
   - 让其开始识别 `generator_name / generation_mode`
   - 生成更贴近不同攻击类型和不同风险等级的运行时文件

2. 继续收紧 `test_package` schema
   - 增加更多字段约束
   - 进一步明确各 generator 的输出契约

当前更推荐优先推进第一条，因为它能把“设计层差异”进一步传递到“执行层差异”。
