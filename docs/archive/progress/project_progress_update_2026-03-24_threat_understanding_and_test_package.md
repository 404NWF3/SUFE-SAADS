# WP1-2 项目进度总说明（2026-03-24）

## 1. 文档目的

本文档用于完整记录 `WP1-2` 截至 `2026-03-24` 的项目状态，重点覆盖以下内容：

1. 当前项目整体结构已经发展到什么程度
2. 真实数据库接入目前做到哪里
3. `ThreatUnderstanding` 子图的输入、输出、判断逻辑已经完成了什么
4. `TestPackageGeneration` 子图已经完成了什么、还缺什么
5. 当前系统可以跑通哪些链路
6. 当前系统还存在什么结构性问题
7. 后续最值得优先推进的工作是什么

本文档不是早期“方向性 contract”，而是**面向当前代码现状的阶段性技术说明**。

---

## 2. 当前项目的一句话定位

截至当前阶段，`WP1-2` 已经不再只是一个“mock 驱动的图结构原型”，而是：

**一个能够从真实数据库读取威胁情报、完成威胁理解、生成结构化测试包，并支持最小调度执行的安全评测 worker 原型系统。**

但必须强调：

- 前半段：数据库读取、威胁理解、路由判断、测试包结构化输出，已经明显成型
- 后半段：环境搭建、真实执行、证据采集、评分、反思迭代，还没有完全真实化

因此当前项目更准确的定位是：

**“真实情报驱动的安全评测 worker + 最小调度器原型”，而不是完整生产级自动化评测系统。**

---

## 3. 当前系统结构

当前项目已经形成了两层结构。

### 3.1 内层：Worker 主图

主图负责处理**单条情报**，主要流程如下：

```text
ingest_intel
-> normalize_intel
-> understand_threat
-> generate_test_package
-> validate_test_package
-> prepare_env_build_request
-> run_aibom_env_build_skill
-> materialize_runtime_attack_assets
-> execute_test
-> collect_evidence
-> score_result
-> reflect
-> persist_knowledge
```

对应主要文件：

- [main_graph.py](/c:/Users/Administrator/Desktop/WP1-2/saads_wp12/graphs/main_graph.py)
- [run_local.py](/c:/Users/Administrator/Desktop/WP1-2/saads_wp12/run_local.py)

### 3.2 外层：Scheduler 调度层

调度层负责从数据库 feed 中发现待处理情报、登记 job、领取 pending job、调用 worker 主图并写回状态。

对应主要文件：

- [run_scheduler.py](/c:/Users/Administrator/Desktop/WP1-2/saads_wp12/scheduler/run_scheduler.py)
- [job_store.py](/c:/Users/Administrator/Desktop/WP1-2/saads_wp12/scheduler/job_store.py)

### 3.3 当前架构图

```text
database feed / read models
    -> db_feed_provider
        -> worker graph (single-item)
            -> threat understanding
            -> test package generation
            -> env build / execution / reflection

database feed
    -> scheduler
        -> wp12_eval_jobs
        -> invoke worker graph
        -> update job status
```

---

## 4. 已完成的核心能力

## 4.1 真实数据库接入已完成

项目已经实现：

- `mock` 模式
- `db` 模式

`db` 模式下，`WP1-2` 已经能够：

- 从主仓库数据库能力读取真实 feed
- 将真实 feed 映射为本地 `Wp12AttackFeedItem`
- 驱动 `run_local`
- 驱动 `scheduler`

这意味着当前系统已经不再依赖纯手写 mock 数据运行。

### 4.1.1 已接入的主路径

当前真实数据读取主路径是：

```text
WP1-2
-> DbAttackFeedProvider
-> main repo db.UnitOfWork(read_only=True)
-> read models / repositories / services
-> wp11.v_wp12_attack_feed
```

### 4.1.2 读取的不仅仅是 feed 主视图

后续为了增强 threat understanding，上游输入已经不再仅限于 `v_wp12_attack_feed` 的基本字段，还补查了：

- `attack_taxonomy_map`
- `attack_entry` 中的额外字段
- AI BOM / component 相关上下文
- seed asset 相关上下文
- component risk overview

当前已经进入 `WP1-2` 的输入类别包括：

1. `feed + taxonomy`
2. `BOM / component`
3. `STIX`

需要说明的是：

- 输入通道已经接好
- 但真实数据库中的某条样本不一定三层都有内容

这意味着当前系统已经具备“接收三层输入”的能力，但必须接受“真实数据经常稀疏”的现实。

---

## 4.2 ThreatUnderstanding 子图已经完成 v1 contract 落地

这是当前阶段最关键的成果之一。

### 4.2.1 为什么要重构 ThreatUnderstanding

早期版本的 `ThreatUnderstanding` 更像一个：

- 基于 taxonomy / 文本规则的轻量分类器

它的问题是：

1. 容易把非 LLM 情报硬塞进现有三类
2. 无法明确表达“这条情报其实不属于当前 WP1-2 处理范围”
3. 无法明确表达“虽然理解了，但现在不能执行”

为解决这个问题，当前版本将 `ThreatUnderstanding` 正式设计成：

**真实情报与测试包生成之间的桥梁。**

### 4.2.2 当前 ThreatUnderstanding 输入 Contract

当前输入被正式分为三层：

#### 第一层：feed_and_taxonomy_context

主要包括：

- attack 基本信息
- summary
- feed_attack_family
- severity / entry_status / CVSS
- primary taxonomy
- all taxonomies
- attack entry 语义补充

#### 第二层：bom_component_context

主要包括：

- component 基本信息
- component impacts
- published seed assets
- component risk overview

#### 第三层：stix_context

当前第一版主要接收：

- `stix_type`
- `stix_payload`

当前阶段约定：

- STIX 参与 threat understanding
- STIX 不作为执行门槛
- AI BOM 才是执行门槛

### 4.2.3 当前 ThreatUnderstanding 输出 Contract

当前已经落地的输出结构为五组：

#### 1. `threat_profile`

表达：

- 攻击家族
- 候选家族
- 置信度
- target surface
- threat summary
- attack mechanism
- test focus
- expected failure modes
- recommended strategy

#### 2. `scope_assessment`

表达：

- `in_scope`
- `scope_reason`
- `supported_family`
- `scope_evidence`

#### 3. `execution_assessment`

表达：

- 是否有 AI BOM
- 是否有 component context
- 是否有 seed assets
- `execution_eligibility`
- `execution_blockers`
- `test_readiness`

#### 4. `evidence_and_context`

表达：

- classification rationale
- component summary
- seed asset summary
- stix summary
- candidate families

#### 5. `uncertainty_report`

表达：

- missing knowledge
- risk flags
- known gaps

### 4.2.4 当前 ThreatUnderstanding 已经修正的重要问题

在本阶段中，ThreatUnderstanding 还做了两次关键修复：

#### 修复 1：统一 out-of-scope 语义

之前存在的问题是：

- 外层判断已经说 `in_scope = false`
- 内层仍然继续输出 `prompt_injection` 风格描述

这会造成自相矛盾。

现在已经修正为：

- `in_scope = false` 时
- 统一走 `unsupported` / `unsupported_target` / `out-of-scope` 理解分支

#### 修复 2：区分“没有 seed asset”和“有 seed asset 但质量不好”

之前系统会把：

- “没有资产”

错误描述成：

- “有资产，但质量不够”

当前已修复为：

- 没有资产 -> `seed_asset_detail`
- 有资产但 `qa_status` 不满足 -> `asset_quality`
- `usable_seed_assets` 在无资产时返回空列表，而不是空对象

### 4.2.5 当前 ThreatUnderstanding 的现状判断

#### 已经完成的

- 能读取真实数据库稀疏情报
- 能整合多源上下文
- 能判断是否属于当前支持范围
- 能判断是否具备进入执行链的条件
- 能把 out-of-scope 样本正确标记为 `unsupported`

#### 还没完全做好的

- 内部 `candidate_families`、`classification_rationale.top_candidate` 仍可能保留旧世界的推断痕迹
- 真正的语义推理还偏规则型，不是成熟的深理解智能体

---

## 4.3 TestPackageGeneration 子图已经完成“最小可跑通版”

这是本阶段的另一个核心成果。

### 4.3.1 当前设计目标

当前并没有试图一步到位生成“高质量比赛级攻击脚本”。

当前测试包生成子图的目标是：

**先让它能真正消费 ThreatUnderstanding Contract，并且正确地区分不同类型的包。**

也就是说，当前是：

- 先打通
- 再迭代优化质量

### 4.3.2 当前子图结构

当前测试包生成逻辑可概括为：

```text
ThreatUnderstanding Contract
    -> Contract Interpreter
    -> Package Kind Selector
    -> Family / Triage Generator
    -> Package Enricher
    -> Package Validator
    -> test_package
```

### 4.3.3 当前三类包

当前已经支持三种包：

#### 1. `standard`

适用于：

- `in_scope = true`
- `execution_eligibility = ready`
- 整体 readiness 较高

#### 2. `conservative`

适用于：

- `in_scope = true`
- 但 execution 尚未 ready
- 或 confidence 偏低
- 或缺口较多

#### 3. `triage`

适用于：

- `in_scope = false`
- 或 `supported_family = unsupported`

这类包不应该进入执行链，而是用于：

- 解释为什么当前不应执行
- 标记当前缺口
- 指出后续应补什么

### 4.3.4 当前测试包结构

当前测试包至少包含：

- `package_id`
- `package_kind`
- `attack_family`
- `target_surface`
- `objective`
- `attack_hypothesis`
- `payload_plan`
- `execution_plan`
- `success_criteria`
- `failure_signals`
- `evidence_hooks`
- `safety_constraints`
- `assumptions`
- `known_gaps`
- `recommended_follow_up`
- `metadata`

### 4.3.5 当前测试包生成已经完成的关键修复

#### 修复 1：triage 不再伪装成 conservative

之前：

- `triage` 包仍然使用 `generation_mode = conservative`

这会导致：

- triage 和 conservative 语义混淆

当前已修复：

- `triage -> generation_mode = "triage"`
- `conservative -> generation_mode = "conservative"`
- `standard -> generation_mode = "standard"`

#### 修复 2：validation 节点已开始检查新 contract

当前 [validation.py](/c:/Users/Administrator/Desktop/WP1-2/saads_wp12/nodes/validation.py) 不再只检查最早期那几个字段，而是已经开始检查：

- `package_kind`
- `attack_hypothesis`
- `payload_plan`
- `execution_plan`
- `failure_signals`
- `assumptions`
- `known_gaps`
- `recommended_follow_up`
- `metadata`

同时对不同包类型做了分支约束：

- `triage` 必须 `do_not_execute + analysis_only`
- 非 `triage` 不能再走 `do_not_execute`

### 4.3.6 当前测试包生成调试入口

当前已新增：

- [inspect_test_package.py](/c:/Users/Administrator/Desktop/WP1-2/saads_wp12/debug/inspect_test_package.py)

它可以直接跑：

```text
ingest_intel
-> normalize_intel
-> understand_threat
-> generate_test_package
```

并打印当前生成的测试包结果。

这意味着现在你可以直接检查：

- 真实样本最终会生成什么类型的包
- 包里具体有哪些字段
- 是否符合当前设计

---

## 5. 当前已经验证通过的链路

截至当前阶段，下列链路已经被验证过。

## 5.1 `intel` 层

已验证：

- 能读取真实数据库样本
- 能标准化 feed + taxonomy + attack entry + component/STIX 通道
- 能处理稀疏输入

## 5.2 `threat_understanding` 层

已验证：

- 能基于真实样本做出结构化理解
- 能识别 out-of-scope 样本
- 能正确给出 `execution_eligibility`

## 5.3 `test_package_generation` 层

已验证：

- 能消费新的 ThreatUnderstanding Contract
- 能正确生成 `triage` 包
- triage 包能够：
  - `do_not_execute`
  - `analysis_only`
  - 列出 known gaps
  - 给出 follow-up 建议

## 5.4 调度层

已验证：

- scheduler 已能读取 feed
- 已能写入/更新 `wp12_eval_jobs`
- 已有真实任务从 `pending` 变为 `done`

但必须指出：

- 数据库连接仍然有明显不稳定问题
- 尤其在多次初始化连接池时容易超时

---

## 6. 当前仍然存在的关键问题

这一部分非常重要，因为当前项目虽然已经“跑通”，但离比赛级完成度还有明显距离。

## 6.1 ThreatUnderstanding 仍有旧痕迹残留

虽然当前主结论已经能正确输出：

- `attack_family = unsupported`
- `in_scope = false`

但在某些输出中，仍会保留：

- `candidate_families = prompt_injection / ...`
- `classification_rationale.top_candidate = prompt_injection`
- `family_inference_signals = fallback:prompt_injection`

这些不会再污染主结论，但仍会在元数据层制造“旧世界残影”。

## 6.2 TestPackageGeneration 目前仍然偏“结构化说明书”

这是当前最重要的不足。

具体说：

- `payload_plan` 仍然过于占位
- `execution_plan` 仍然比较空泛
- family generator 内部差异还不够深
- 它更像“结构化包生成器”
- 还不像“高质量攻击脚本生成器”

也就是说，当前测试包生成已经能输出**正确类型的包**，但还没有输出**足够强的脚本策略**。

## 6.3 `standard` 和 `conservative` 的差异还不够大

当前已经把：

- `triage`
- `conservative`

拆开了，这一步很关键。

但：

- `standard`
- `conservative`

目前更多是“同一个骨架 + 不同字段”，而不是“明确不同强度的包”。

## 6.4 `recommended_follow_up` 还不够操作化

当前 follow-up 仍比较粗粒度，比如：

- 等 AI BOM enrichment
- 去 triage

但它还没有做到真正可指导自动迭代修复，例如：

- 需要补哪类 seed asset
- 需要补 taxonomy 还是 AI BOM
- 是上游筛选问题还是执行前置条件问题

## 6.5 Validation 还没有和 debug 完全联动

当前虽然 `validation.py` 已增强，但 `inspect_test_package.py` 还没有直接显示校验结果。

这意味着：

- 你能看到包长什么样
- 但还不能在 debug 输出中直接看到它是否通过 validation

这会带来调试盲点。

## 6.6 数据库连接稳定性仍是系统性外部风险

从多次本机运行可以确认：

- 真实数据库并非完全不可用
- 但连接池初始化超时频繁出现
- 同一命令可能一次成功、一次失败

所以当前开发必须默认：

**数据库可用，但不稳定。**

---

## 7. 当前测试现状

当前已经补充并通过的本地测试包括：

- [test_intel_normalization.py](/c:/Users/Administrator/Desktop/WP1-2/tests/test_intel_normalization.py)
- [test_threat_understanding.py](/c:/Users/Administrator/Desktop/WP1-2/tests/test_threat_understanding.py)
- [test_test_package_generation.py](/c:/Users/Administrator/Desktop/WP1-2/tests/test_test_package_generation.py)
- [test_package_validation.py](/c:/Users/Administrator/Desktop/WP1-2/tests/test_package_validation.py)

这些测试当前主要覆盖：

1. 稀疏 intel 标准化
2. out-of-scope threat understanding 统一判断
3. seed asset 语义拆分
4. `standard / conservative / triage` 三种包生成
5. triage / non-triage validation 规则

需要强调的是：

当前这些测试主要是**规则层、结构层**测试，  
还不是**比赛级真实攻击脚本效果测试**。

---

## 8. 当前阶段最准确的项目状态判断

如果用一句非常准确的话总结当前阶段：

**项目已经完成了“真实情报 -> threat understanding -> test package 路由生成”的核心桥梁搭建，但测试包生成的真实攻击脚本能力仍然处于雏形阶段。**

更细一点：

### 已经完成

- 真实数据库接入
- 多源上下文接入
- ThreatUnderstanding Contract v1
- out-of-scope 与 execution gate 统一
- TestPackageGeneration Contract 最小落地
- triage 包正确路由
- package validation 开始收紧
- debug 入口可查看 intel / threat / package

### 部分完成

- conservative / standard 包
- family-specific generator
- execution plan 结构
- 反思闭环前置中间表示

### 尚未完成

- 高质量攻击脚本生成
- 真实环境搭建与强执行链
- 基于 100 次运行阈值的成熟迭代闭环
- 成熟的 reflection-driven package repair

---

## 9. 当前最值得优先做的下一步

如果按“比赛价值”和“当前基础”综合排序，下一步最值得做的是：

## 9.1 优先级一：把 `standard` 和 `conservative` 真正拉开

目标：

- `standard` 真正偏执行型
- `conservative` 真正偏验证型

这会直接提升测试包生成的真实性。

## 9.2 优先级二：让 `execution_plan` 更具体

目标：

- 不再只是占位
- 真正表达：
  - 怎么跑
  - 需要什么输入
  - 输出什么结果
  - 后面怎么进 100 次模拟运行

## 9.3 优先级三：让 family generator 真正消费新 contract

当前还需要让 generator 更深地使用：

- `component_context_summary`
- `seed_asset_summary`
- `test_readiness`
- `known_gaps`

从而使得脚本设计更像真实样本驱动，而不是只是换几个字段。

## 9.4 优先级四：把 validation 结果接入 debug 输出

这样你每次本机跑 `inspect_test_package.py` 时，就能直接看到：

- 当前包是否通过 validation
- 哪些字段缺失
- 哪些逻辑违规

这对比赛前快速调试很有帮助。

---

## 10. 当前可直接使用的调试命令

### 10.1 查看真实情报标准化结果

```powershell
.\.venv\Scripts\python.exe -m saads_wp12.debug.inspect_intel <attack_id>
```

### 10.2 查看真实情报经过 threat understanding 的结果

```powershell
.\.venv\Scripts\python.exe -m saads_wp12.debug.inspect_threat_understanding <attack_id>
```

### 10.3 查看真实情报最终生成的测试包

```powershell
.\.venv\Scripts\python.exe -m saads_wp12.debug.inspect_test_package <attack_id>
```

### 10.4 单次本地完整跑 worker

```powershell
.\.venv\Scripts\python.exe -m saads_wp12.run_local
```

### 10.5 单次 scheduler

```powershell
.\.venv\Scripts\python.exe -m saads_wp12.scheduler.run_scheduler
```

---

## 11. 最终总结

截至 `2026-03-24`，`WP1-2` 已经完成了一个很关键的阶段转变：

它不再只是：

- 靠 mock 数据跑图
- 靠硬编码路由
- 靠单一攻击模板生成占位包

而是已经开始具备：

- 真实数据库驱动
- ThreatUnderstanding Contract 化
- 执行资格门槛控制
- triage / conservative / standard 包路由
- package validation
- 调试入口可观测

但也必须清醒地认识到：

**当前项目最强的地方是“结构、路由、contract”，最弱的地方是“高质量攻击脚本生成与真实执行化”。**

因此当前阶段最准确的项目状态是：

**核心桥梁已经搭成，真正的比赛质量提升将主要取决于下一步如何增强 `standard / conservative` 测试包的真实脚本能力。**

