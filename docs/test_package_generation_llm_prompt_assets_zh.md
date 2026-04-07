# TestPackageGeneration 提示词资产说明

这份文档对应第 6 步的实际产物：把已经稳定下来的规则版 `TestPackageGeneration` 提炼成一套未来可交给 LLM 的生成协议。

## 1. 这一步的目的

目的不是立刻把规则版替换成 LLM，而是先固定：

- 模型吃什么输入
- 模型吐什么输出
- 三类 family 分别要强调什么
- triage / conservative / standard 如何被稳定约束

也就是说，这一步是在搭 **LLM 版测试包生成器的提示词地基**。

## 2. 当前代码资产

提示词资产代码位于：

- [test_package_generation_prompts.py](/mnt/c/Users/Administrator/Desktop/WP1-2/saads_wp12/llm/test_package_generation_prompts.py)

当前已提供：

1. `build_test_package_system_prompt()`
   作用：定义模型角色、输出边界、硬性规则。

2. `build_test_package_user_prompt(contract)`
   作用：把固定输入 contract 编码成 user prompt。

3. `build_test_package_few_shot_examples()`
   作用：提供最小 few-shot 样本骨架，覆盖：
   - prompt_injection / standard
   - long_horizon_dialogue / conservative
   - unsupported / triage

4. `build_test_package_prompt_bundle(contract)`
   作用：一次性返回 system prompt、user prompt、few-shot、schema required fields。

## 3. 输入来源

提示词工程不直接吃 orchestration 的大状态，而是只吃已经固定好的：

- `TestPackageGenerationInputContract`

对应代码位于：

- [test_package_generation.py](/mnt/c/Users/Administrator/Desktop/WP1-2/saads_wp12/engines/test_package_generation.py)

这样后面即使切换到 LLM 版，输入边界也不会漂移。

## 4. 输出目标

当前 prompt 资产要求模型输出一个严格的 test package JSON 对象，至少包含：

- `package_kind`
- `generation_mode`
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

## 5. family-specific 强调点

### prompt_injection

- 必须强调 context binding
- 必须体现 baseline vs injected 对比
- 必须收 `retrieval_trace` 和 `context_snapshot`

### long_horizon_dialogue

- 必须强调多轮 turn schedule
- 必须体现 dialogue state checkpoint
- 必须收 `dialogue_transcript` 和 `turn_state_snapshot`

### tool_hijack

- 必须强调 tool argument map
- 必须体现 planned vs observed tool usage comparison
- 必须收 `tool_call_trace` 和 `tool_argument_snapshot`

## 6. 当前阶段的意义

这一步做完之后，你已经拥有：

- 固定输入 contract
- 固定输出 schema
- family-specific prompt 补充
- few-shot 资产骨架

也就是说，未来如果要新增 `LlmTestPackageGenerationEngine`，就不需要从空白开始设计 prompt 了。
