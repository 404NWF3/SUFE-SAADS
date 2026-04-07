# WP1-2 子图 LLM 接入设计文档

## 1. 文档目的

本文档说明 `WP1-2` 中 3 个高不确定性子图在未来接入 LLM 时的设计边界，重点包括：

- 每个子图解决什么问题
- 每个子图接收什么输入
- 每个子图必须输出什么结构
- 每个子图的提示词目标是什么
- 当前没有真实 LLM 时，哪些工作可以先做

本文档关注 `WP1-2` 内部的 LLM 接入设计，不涉及数据库实现细节。

---

## 2. 总体原则

### 2.1 不是全流程都接 LLM

`WP1-2` 不应该把所有节点都改成 LLM 驱动。未来接入 LLM 的重点是 3 个高不确定性子图：

1. `threat_understanding`
2. `test_package_generation`
3. `reflection`

普通节点仍应尽量保持为确定性逻辑，例如：

- `normalize_intel`
- `validate_test_package`
- `prepare_env_build_request`
- `materialize_runtime_attack_assets`
- `persist_knowledge`

### 2.2 子图是受控的推理子流程

这 3 个模块在当前架构中首先是 **子图**，不是独立系统。未来它们可以演化成：

- 单个 LLM 驱动的子图
- 或多个 LLM 节点协作的子图

但它们仍然属于 `WP1-2` 主图内部的受控推理模块。

### 2.3 先固定输入输出，再写提示词

在真正接入 LLM 前，最重要的事情不是立刻调 prompt，而是先固定：

1. 输入上下文边界
2. 输出结构 schema
3. 失败时的最小返回规则

只有 schema 稳定，后续提示词工程才可控。

---

## 3. 子图一：Threat Understanding

### 3.1 子图职责

`threat_understanding` 子图的职责不是重复上游数据库已经完成的结构化工作。它真正做的是：

**把数据库中已经结构化的威胁情报，进一步加工成面向测试包生成与执行评测的高参考性结构化威胁理解对象。**

换句话说，它负责把“情报结构化对象”提升成“测试导向结构化对象”。

### 3.2 当前输入来源

当前主流程里，该子图主要消费以下 state 字段：

- `intel_normalized`
- `risk_flags`

未来真正接入 LLM 时，建议输入上下文最少包括：

```python
{
  "attack_id": "...",
  "attack_code": "...",
  "canonical_name": "...",
  "summary": "...",
  "taxonomy": {
    "type": "...",
    "code": "...",
    "name": "..."
  },
  "component": {
    "id": "...",
    "name": "...",
    "version_constraint": "..."
  },
  "seed_asset": {
    "asset_type": "...",
    "asset_name": "...",
    "artifact_uri": "...",
    "qa_status": "..."
  },
  "primary_cvss_base_score": 8.1,
  "primary_cvss_vector": "...",
  "attack_family": "...",
  "risk_flags": [...]
}
```

### 3.3 推荐输出 schema

未来该子图至少应稳定输出以下字段：

```python
{
  "threat_understanding": {
    "threat_summary": "...",
    "attack_mechanism": "...",
    "taxonomy": {...},
    "target_surface": "...",
    "exploit_preconditions": [...],
    "test_focus": [...],
    "expected_failure_modes": [...],
    "recommended_test_strategy": "...",
    "usable_seed_assets": [...]
  },
  "attack_family": "...",
  "target_surface": "...",
  "confidence": 0.0,
  "candidate_families": [
    {"family": "...", "confidence": 0.0}
  ],
  "classification_rationale": {
    "taxonomy_signal": "...",
    "summary_signal": "...",
    "asset_signal": "...",
    "decision_basis": "..."
  },
  "missing_knowledge": [...]
}
```

这里最重要的一点是：

- `threat_understanding` 必须是 **结构体**
- 它是给机器看的，不是给人看的自由文本
- 它必须对后续 `test_package_generation` 具有直接参考价值

### 3.4 输出字段的业务含义

- `threat_summary`
  - 对当前威胁的测试导向总结
- `attack_mechanism`
  - 攻击利用机制，后续生成攻击路径时会直接参考
- `taxonomy`
  - 保留与上游知识层的映射关系
- `target_surface`
  - 明确后续测试要打哪一层
- `exploit_preconditions`
  - 后续测试包中的前置条件
- `test_focus`
  - 后续测试包中的重点验证目标
- `expected_failure_modes`
  - 后续评分、反思阶段的参考失败模式
- `recommended_test_strategy`
  - 对测试包生成的高层策略建议
- `usable_seed_assets`
  - 后续生成和落盘可优先使用的种子资产
- `missing_knowledge`
  - 当前测试设计仍缺少的关键信息
- `confidence`
  - 当前主判断的整体确定程度
- `candidate_families`
  - 备选攻击家族及其相对置信度
- `classification_rationale`
  - 当前分类判断的主要依据，供调试、反思和后续修正使用

### 3.5 提示词目标

该子图的提示词目标应当是：

1. 识别攻击属于哪类攻击家族
2. 判断更适合攻击哪个目标面
3. 提炼出后续测试设计最需要的攻击机制
4. 给出前置条件、测试重点、预期失败模式
5. 指出当前仍缺失哪些关键信息

### 3.6 提示词输出要求

提示词中应强约束模型：

- 必须输出结构化 JSON
- `threat_understanding` 必须是对象，不能是字符串
- 不允许输出长篇自由散文
- 信息不足时必须填写 `missing_knowledge`
- 不允许虚构组件信息和外部事实

### 3.7 当前阶段能做的准备

即使现在没有真实 LLM，也可以先做：

1. 固定该子图的输入 schema
2. 固定输出 schema
3. 编写 system prompt 草稿
4. 编写 user prompt 模板
5. 准备 2 到 3 个 few-shot 样例

---

## 4. 子图二：Test Package Generation

### 4.1 子图职责

`test_package_generation` 子图负责：

- 根据测试导向威胁理解结果生成抽象测试包
- 明确测试目标、攻击计划、证据钩子和成功标准
- 产出后续 runtime assets 落盘所需的结构化设计对象

它的输出不是最终脚本，而是 **脚本生成和执行的设计蓝图**。

### 4.2 当前输入来源

当前主流程里，该子图主要消费：

- `threat_understanding`
- `attack_family`
- `target_surface`
- `generation_route`
- `intel_normalized`

未来 LLM 接入时，建议最少输入：

```python
{
  "attack_id": "...",
  "attack_family": "...",
  "target_surface": "...",
  "generation_route": "...",
  "threat_understanding": {...},
  "seed_asset": {
    "asset_type": "...",
    "asset_name": "...",
    "artifact_uri": "..."
  },
  "risk_flags": [...]
}
```

### 4.3 推荐输出 schema

未来该子图至少应稳定输出：

```python
{
  "test_package": {
    "package_id": "...",
    "attack_family": "...",
    "target_surface": "...",
    "objective": "...",
    "preconditions": [...],
    "payload_plan": [...],
    "dialogue_plan": [...],
    "tool_sequence": [...],
    "success_criteria": [...],
    "failure_signals": [...],
    "evidence_hooks": [...],
    "safety_constraints": [...],
    "retry_strategy": {...},
    "metadata": {...}
  },
  "package_version": 1
}
```

第一版不一定要全部填满，但字段结构应尽量稳定。

### 4.4 提示词目标

该子图的提示词目标应当是：

1. 生成一份可执行测试设计方案
2. 让攻击目标、攻击步骤、成功标准清晰可检验
3. 明确证据收集点
4. 给出必要的安全限制和失败信号
5. 保证输出适合后续 runtime assets 节点落盘

---

## 5. 子图三：Reflection

### 5.1 子图职责

`reflection` 子图负责：

- 读取执行结果、证据和评分
- 判断失败原因
- 给出修复方向
- 决定主图后续是修包、修环境、补知识，还是结束

它不是简单写一句“失败了”，而是要给主图提供 **可执行的修复决策**。

### 5.2 当前输入来源

当前主流程里，该子图主要消费：

- `package_validation`
- `env_status`
- `runtime_assets_manifest`
- `execution_result`
- `evidence_bundle`
- `score_result`
- `verdict`

未来真正接入 LLM 时，建议最少输入：

```python
{
  "package_validation": {...},
  "env_status": "...",
  "runtime_assets_manifest": {...},
  "execution_contract": {...},
  "execution_result": {...},
  "traces": [...],
  "artifacts": [...],
  "evidence_bundle": {...},
  "score_result": {...},
  "verdict": "...",
  "reflection_round": 0,
  "max_reflection_rounds": 1
}
```

### 5.3 推荐输出 schema

未来该子图至少应稳定输出：

```python
{
  "reflection_result": {
    "failure_summary": "...",
    "root_cause": "...",
    "repair_plan": "...",
    "repair_action": "...",
    "confidence": 0.0,
    "engine": "llm"
  },
  "repair_action": "..."
}
```

其中 `repair_action` 建议至少支持：

- `fix_package`
- `fix_env`
- `fix_runtime_assets`
- `retrieve_knowledge`
- `done`

---

## 6. 提示词工程当前能做什么

虽然当前还没有真实 LLM，但并不意味着提示词工程要完全暂停。

现在能做的是提示词工程的前半部分：

1. 固定任务目标
2. 固定输入边界
3. 固定输出 schema
4. 编写 prompt 草稿
5. 准备 few-shot 样例
6. 设计 prompt 文件结构

现在还不适合重度投入的是：

1. prompt wording 微调
2. 不同模型对比实验
3. 温度和采样参数对比
4. token 成本优化
5. 长上下文拼接优化

---

## 7. 建议的 Prompt 文件组织方式

建议未来在项目中采用如下结构：

```text
saads_wp12/
  prompts/
    threat_understanding/
      system.txt
      user_template.txt
      examples/
        prompt_injection.json
        tool_hijack.json
    test_package_generation/
      system.txt
      user_template.txt
      examples/
        prompt_injection.json
        long_dialogue.json
    reflection/
      system.txt
      user_template.txt
      examples/
        low_pass_rate.json
        env_failed.json
```

这样未来接入 LLM 时，不会把提示词散落在代码里。

---

## 8. 建议的近期推进顺序

在真实 LLM 尚未完全稳定接入时，建议按以下顺序推进：

1. 固定 3 个子图的输入 schema
2. 固定 3 个子图的输出 schema
3. 整理 `repair_action`、`attack_family`、`target_surface` 等关键枚举
4. 编写 prompt 草稿
5. 准备 few-shot 样例
6. 后续再接真实 LLM 并调优

---

## 9. 当前结论

当前项目已经具备未来接入 LLM 的基本结构条件：

- 主图已存在
- 子图已存在
- 子图已抽象成可替换 engine

因此，下一阶段的重点不是重写主图，而是：

1. 继续完善子图输入输出契约
2. 准备 prompt 资产
3. 等真实 LLM 接入后，将规则版 engine 替换为 LLM 版 engine

本文档可作为后续提示词设计、LLM 接入和团队沟通的基础说明。
