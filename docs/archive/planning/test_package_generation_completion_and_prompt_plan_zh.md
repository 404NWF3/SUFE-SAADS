# WP1-2 测试包生成模块完成标准与提示词工程待办

## 1. 文档目的

这份文档只解决一个问题：

**如何判断 `TestPackageGeneration` 这一层什么时候算“基本完成”，以及在当前阶段应该如何推进提示词工程。**

这里刻意不讨论：

- 扩展更多攻击 family
- 真实执行环境的全部落地细节
- 真实 LLM 接入

因为这些都不属于当前阶段要先解决的核心问题。

当前阶段需要先把 `TestPackageGeneration` 自己这一层做扎实，做成一个：

- 输入边界清晰
- 输出 contract 稳定
- 路由逻辑可解释
- 可被下游模块消费
- 未来可切换到 LLM 驱动

的成熟中间层。

---

## 2. 模块定位

`TestPackageGeneration` 的职责只有一句话：

**决定怎么测。**

它不负责：

- 判断情报值不值得测
- 判断是否允许进入实测
- 真正搭建环境
- 真正执行攻击脚本
- 最终评分

它的上游是：

- `ThreatUnderstanding`
- `ExecutionAssessment`
- `EvidenceAndContext`

它的下游是：

- `Validation`
- `EnvBuild`
- `RuntimeAssets`
- `Execution`

因此，`TestPackageGeneration` 必须被理解成：

**威胁理解结果和执行层之间的“执行蓝图生成器”。**

---

## 3. 当前阶段的正确目标

当前阶段“完善测试包生成”不等于：

- 覆盖所有攻击类型
- 生成最终比赛级攻击脚本
- 接通真实执行系统

当前阶段的正确目标是：

**让系统可以稳定地把结构化威胁理解结果，转换成高质量、可验证、可落盘、可被下游消费的测试执行蓝图。**

也就是说，当前阶段要完成的是：

1. 稳定输入
2. 稳定输出
3. 稳定路由
4. 稳定 family 模板
5. 稳定 validation
6. 为未来提示词工程和真实数据接入做好准备

---

## 4. 测试包生成模块完成标准

## 4.1 输入 contract 稳定

`TestPackageGeneration` 只能依赖明确规定的一组输入字段。

建议固定为：

- `attack_family`
- `target_surface`
- `threat_profile`
- `scope_assessment`
- `execution_assessment`
- `component_context_summary`
- `seed_asset_summary`
- `stix_summary`
- `classification_rationale`
- `known_gaps`

完成标准：

1. 输入字段集合固定，不再临时追加无定义字段。
2. 每个字段的含义明确，不同样本语义一致。
3. 当某些字段缺失时，有清晰的降级逻辑，而不是生成器自由发挥。
4. 生成器不依赖“图里恰好有这个状态”这种隐式前提。

---

## 4.2 输出 contract 稳定

输出必须稳定落到统一 schema。

最小输出字段建议固定为：

- `package_id`
- `package_kind`
- `generation_mode`
- `attack_family`
- `target_surface`
- `objective`
- `attack_hypothesis`
- `payload_plan`
- `execution_plan`
- `success_criteria`
- `failure_signals`
- `evidence_collection_plan`
- `script_blueprint`
- `target_artifacts`
- `family_specific_strategy`
- `recommended_follow_up`
- `metadata`

完成标准：

1. 不同样本的输出结构一致。
2. `triage / conservative / standard` 的差异主要体现在内容和强度，而不是结构乱变。
3. 输出可以被 `validation` 稳定检查。
4. 输出可以被 `runtime_assets` 消费。

---

## 4.3 路由逻辑稳定

当前测试包必须稳定地区分三类 package：

- `triage`
- `conservative`
- `standard`

同时必须稳定地区分攻击 family：

- `prompt_injection`
- `long_horizon_dialogue`
- `tool_hijack`
- `unsupported`

完成标准：

1. `unsupported` 或 out-of-scope 样本稳定生成 `triage`。
2. in-scope 但执行条件不足的样本稳定生成 `conservative`。
3. in-scope 且执行条件充分的样本稳定生成 `standard`。
4. 不允许 `triage` 伪装成可执行包。
5. 不允许信息严重不足的样本直接生成高强度 `standard` 包。

---

## 4.4 family 模板成熟

每个 family 不是只换一个标签，而是必须拥有自己独立的蓝图模板。

### 4.4.1 prompt_injection

至少要稳定定义：

- payload 的主形态
- 注入位置或上下文槽位
- 执行步骤
- 成功信号
- 失败信号
- 证据采集方式
- blueprint 文件结构

### 4.4.2 long_horizon_dialogue

至少要稳定定义：

- turn schedule
- 多轮推进结构
- transcript 采集
- 状态变化证据
- blueprint 文件结构

### 4.4.3 tool_hijack

至少要稳定定义：

- tool plan
- argument map
- 工具调用证据
- tool trace
- blueprint 文件结构

完成标准：

1. 三个 family 的 package 一眼能看出不是同一套模板换名字。
2. 三个 family 都有自己的 `payload_plan / execution_plan / evidence / blueprint` 形态。
3. 同一个 family 在不同上下文下，package 会发生合理变化。

---

## 4.5 package 必须能驱动下游

这是测试包生成是否“真正完成”的关键标准。

如果生成出来的 package 很漂亮，但下游消费不了，它就不算完成。

完成标准：

1. package 能稳定通过 `validation`。
2. package 能驱动 `runtime_assets` 生成文件。
3. package 产出的 `script_blueprint` 可以转化为实际运行资产。
4. package 对后续 `execution` 是有意义的，而不是只供阅读。

---

## 5. 当前项目在完成标准中的位置

截至当前阶段，`TestPackageGeneration` 已经明显超过“原型阶段”，但还没达到“成熟完成”。

### 5.1 已经具备的能力

当前已经完成：

1. `triage / conservative / standard` 基本路由成型。
2. 三个 family 已经开始分化。
3. package schema 已经不再是早期占位版。
4. `validation` 已接入。
5. `runtime_assets` 已经能够开始消费 `script_blueprint` 并生成文件。

### 5.2 当前还欠缺的部分

当前仍需要加强：

1. family 内部模板还不够深。
2. `standard` 和 `conservative` 的策略差异还不够大。
3. package 仍然偏“结构化蓝图”，还不够像高质量攻击方案。
4. LLM 驱动下的提示词与 few-shot 体系尚未建立。

因此，当前判断应为：

**测试包生成模块已经进入可用阶段，但尚未进入成熟完成阶段。**

---

## 6. 当前阶段的推进原则

当前阶段推进 `TestPackageGeneration` 时，必须遵守以下原则：

1. 先稳住 contract，再做花哨优化。
2. 先稳住 family 模板，再做更多 family 扩展。
3. 先稳住路由和输出质量，再引入 LLM。
4. 先把生成器做成稳定机器，再等更多真实数据喂进来。

这也是“先把提示词工程都做好，等着数据就行了”这句话成立的前提。

这句话的正确理解是：

**先把生成器的输入、输出、规则、模板、few-shot、校验机制都设计好，等数据来了再做调优。**

而不是：

**先写很多 prompt 文案，其他边界都不管。**

---

## 7. 提示词工程待办清单

当前如果要系统推进提示词工程，建议按以下顺序进行。

## 7.1 明确 prompt 输入边界

先定义模型到底会收到什么输入。

建议输入固定为：

- `attack_family`
- `target_surface`
- `threat_summary`
- `attack_mechanism`
- `component_context_summary`
- `seed_asset_summary`
- `stix_summary`
- `execution_assessment`
- `known_gaps`
- `classification_rationale`

目标：

1. 不让 prompt 输入漂。
2. 不让模型依赖偶然存在的额外字段。
3. 让规则版与 LLM 版共享同一输入 contract。

---

## 7.2 明确 prompt 输出边界

模型输出必须被严格限制在 package schema 内。

建议要求模型只输出：

- `package_kind`
- `generation_mode`
- `payload_plan`
- `execution_plan`
- `success_criteria`
- `failure_signals`
- `evidence_collection_plan`
- `script_blueprint`
- `target_artifacts`
- `recommended_follow_up`

目标：

1. 不让模型写成自然语言说明书。
2. 不让模型省略关键字段。
3. 不让输出脱离下游模块可消费的格式。

---

## 7.3 明确 triage / conservative / standard 规则

在 prompt 中必须明确写出三类 package 的区别。

至少要覆盖：

### triage

- 适用于 out-of-scope
- 或关键执行条件严重不足
- 不允许产生执行型蓝图

### conservative

- 适用于 in-scope 但信息不足
- 可生成谨慎验证型方案
- 不应生成高强度执行型步骤

### standard

- 适用于 in-scope 且条件较充分
- 允许完整 runtime blueprint

目标：

**让模型先做正确的包级路由，再做内容生成。**

---

## 7.4 分 family 设计提示模板

建议为每个 family 设计独立 prompt 模板，而不是共用一套大 prompt。

### prompt_injection prompt

重点约束：

- payload 形态
- 注入槽位
- retrieval/context 证据
- prompt runner blueprint

### long_horizon_dialogue prompt

重点约束：

- multi-turn plan
- turn progression
- transcript / turn-state 证据
- dialogue runner blueprint

### tool_hijack prompt

重点约束：

- tool selection / argument manipulation
- tool plan
- tool trace
- tool runner blueprint

目标：

**让模型输出天然带有 family-specific 风格。**

---

## 7.5 准备 few-shot 示例

这是当前阶段最值得提前做的工作之一。

建议每个 family 至少准备：

- 1 个 `standard` 示例
- 1 个 `conservative` 示例
- 1 个 `triage` 或 out-of-scope 示例

few-shot 的用途：

1. 帮模型学会 package 结构。
2. 帮模型学会 package 强度差异。
3. 帮模型学会 family 风格差异。
4. 帮模型学会信息不足时如何保守降级。

---

## 7.6 设计 JSON schema 约束

在正式接入 LLM 前，应该先写清楚：

1. 哪些字段必填
2. 哪些字段可选
3. 哪些字段必须是列表
4. 枚举值有哪些
5. 不同 package_kind 的结构约束是什么

目标：

**让 LLM 输出更稳定、更容易被校验与修正。**

---

## 7.7 设计 fallback 与纠偏规则

提示词工程不能只考虑“模型表现最好时”的情况，还必须考虑失败情况。

建议提前定义：

1. 如果输出 JSON 不合法怎么办
2. 如果 package_kind 判错怎么办
3. 如果 family 风格不对怎么办
4. 如果字段缺失怎么办
5. 如果模型生成了不可执行的 blueprint 怎么办

目标：

**让 LLM 版 `TestPackageGeneration` 具备工程可控性。**

---

## 8. 当前阶段最推荐的推进顺序

当前阶段不建议平均发力。

最推荐顺序如下：

1. 固定输入 contract
2. 固定输出 schema
3. 固定 `triage / conservative / standard` 规则
4. 固定三个 family 的模板
5. 编写 few-shot 示例
6. 编写 prompt 约束
7. 编写 schema 与 fallback 规则
8. 最后再引入更多真实数据调优

---

## 9. 当前阶段的判断标准

如果未来你要判断 `TestPackageGeneration` 是否已经“基本完成”，可以直接用以下五条：

1. 不同样本的输入输出 contract 稳定。
2. 不同 package_kind 的路由稳定。
3. 不同 family 的生成结果明显不同。
4. 生成结果能稳定通过 validation。
5. 生成结果能被 `runtime_assets` 稳定消费。

当这五条成立时，就可以认为：

**`TestPackageGeneration` 这一层已经基本成熟，可以进入更大规模的数据调优和执行联调阶段。**

---

## 10. 一句话总结

当前阶段不需要等待所有真实数据到位，完全可以先把 `TestPackageGeneration` 做成熟。

最重要的不是继续发散，而是：

**把它做成一台输入稳定、输出稳定、规则稳定、模板稳定、未来可切换到 LLM 的生成机器。**
