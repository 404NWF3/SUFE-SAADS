# WP1-1 Phase 0 核心定义与设计基线

本文档只覆盖 WP1-1 正式开发前的 Phase 0 准备项，目标是冻结边界、统一术语、明确 Phase 1 首批启用范围与验收口径，并区分“必须一次设计到位的基础结构”和“允许先弱实现的能力”，为后续阶段提供稳定输入。

## 0. Phase 0 的总原则

WP1-1 不采用狭义 MVP 思路。

- 可以分阶段启用功能，但不能把系统边界做窄
- 可以先做弱实现，但不能把 schema、state、接口和 handoff contract 做死
- Phase 1 是“首批启用能力”，不是“临时拼装版系统”
- 后续阶段应建立在同一套可扩展骨架上迭代，而不是依赖大规模返工

## 1. 冻结 WP1-1 术语与边界

### 1.1 系统定位

WP1-1 是一个长期运行的情报采集与弱信号发现系统，不是单次问答式 Agent。它面向公开安全源持续执行采集、标准化、归并、BOM 解析、覆盖率分析、补采和告警。

### 1.2 本阶段统一术语

#### `raw record`
- 含义：从某个 source 原样抓取并完成最小清洗后的原始记录
- 最小字段：`source_name`、`source_uri`、`external_id`、`title`、`content/payload_ref`、`published_at`、`fetched_at`、`content_hash`
- 作用：作为后续标准化、去重、审计的原始证据输入

#### `attack`
- 含义：完成标准化后的攻击情报对象，是 WP1-1 的核心知识单元
- 典型字段：`attack_code`、`canonical_name`、`attack_family`、`summary`、`description`、`taxonomy_items`、`bom_mentions`、`stix_payload`
- 注意：`attack` 不是某条网页、帖子或论文本身，而是从多个证据中归并出的规范化对象

#### `query run`
- 含义：某一 source 在某一轮执行的一个具体检索任务实例
- 典型字段：`query_text`、`query_intent`、`source_name`、`rewrite_round`、`rewrite_reason`、`time_window_days`
- 作用：为 search reflection、coverage gap fill、source 调度提供 telemetry 基础

#### `coverage gap`
- 含义：当前情报库在某一维度上的覆盖缺口，不局限于 OWASP taxonomy 数量不足
- 最小分析维度：`taxonomy gap`、`source diversity gap`、`component family gap`
- 扩展维度：`corroboration gap`、`novelty gap`

#### `artifact_ref`
- 含义：指向正文、PDF、HTML、截图、对象存储或持久化记录的引用句柄
- 目标：LangGraph 节点间尽量传 `artifact_ref`、`raw_id`、`attack_id`、摘要和统计，而不是传大文本 payload

### 1.3 系统边界

#### 本期纳入
- 公开漏洞与公告源
- 公开论文与技术报告源
- 公开社区讨论源
- 结构化攻击情报生成
- AI BOM 组件映射
- 覆盖率分析与补采

#### 本期不纳入
- Telegram 私域采集
- 暗网论坛采集
- Tor 代理链路
- 付费情报 API 的大规模接入
- 人工研判后台的完整产品化界面

### 1.4 设计约束

- Agent 不直接写 SQL
- 节点间优先传 `id/ref/summary`，不长期传原始正文
- 自动决策必须保留 `reason` 或 `rationale`
- 每个 source 必须可追踪到 query、结果和失败原因

## 2. 明确 Phase 1 首批启用 source 范围

Phase 0 只定义完整系统边界下的首批启用范围，不展开实现细节。

### 2.1 完整边界下的 source 清单

#### 结构化安全源
- NVD
- CISA KEV
- MITRE ATT&CK

#### 代码与公告源
- GitHub Security Advisories
- GitHub Discussions / Issues
- 厂商安全公告

#### 研究与论文源
- arXiv
- HuggingFace papers / model cards / security-related items

#### 社区与弱信号源
- Reddit
- Hacker News

### 2.2 source 分层优先级

#### P0：Phase 1 必须先接通
- NVD
- GitHub Security Advisories
- arXiv

#### P1：Phase 1 闭环需要
- Reddit
- Hacker News
- CISA KEV
- MITRE ATT&CK

#### P2：后续阶段优先扩展
- GitHub Discussions / Issues
- 厂商安全公告
- HuggingFace

### 2.3 source 接入要求

- 必须支持基础游标或时间窗口增量抓取
- 必须记录 source-specific 速率限制与失败策略
- 必须输出最小统一 raw record 结构
- 必须能关联到 `query run`

## 3. 明确 3 类输出

### 3.1 结构化攻击情报

输出目标：形成可供 WP1-2 / WP1-3 消费的标准攻击知识对象。

最小输出字段建议：
- `attack_id`
- `attack_code`
- `canonical_name`
- `attack_family`
- `summary`
- `description`
- `severity_level`
- `taxonomy_items`
- `bom_mentions` / `resolved_components`
- `evidence_refs`
- `confidence_score`
- `novelty_score`

### 3.2 coverage / gap 分析结果

输出目标：驱动后续 gap fill 和 source 调度，而不是只做展示。

最小输出字段建议：
- `taxonomy_code`
- `taxonomy_name`
- `gap_score`
- `source_diversity_gap`
- `component_coverage_gap`
- `recommended_sources`
- `recommended_queries`
- `expected_evidence_type`
- `estimated_gap_fill_roi`

### 3.3 告警与待人工复核项

输出目标：把高价值风险和不确定项分流出去。

告警类最小字段建议：
- `alert_type`
- `severity`
- `title`
- `summary`
- `related_attack_id` / `related_cluster_id`
- `evidence_refs`
- `trigger_reason`

待人工复核类最小字段建议：
- `queue_type`
- `subject_id`
- `reason_code`
- `ambiguity_summary`
- `candidate_options`
- `submitted_at`

## 4. 明确成功指标

Phase 0 只定义指标，不定义具体阈值实现方式。阈值应在进入 Phase 1/2 后根据真实数据校准。

### 4.1 运行稳定性指标

- 每轮采集成功率
- 单 source 任务成功率
- 平均采集延迟
- 失败重试后恢复率

### 4.2 数据处理质量指标

- 原始记录 parse 成功率
- 标准化成功率
- `new / merge / review` 分布
- BOM 解析成功率
- unresolved queue 占比

### 4.3 搜索与反思效果指标

- query result count
- parsed count
- novelty yield
- duplicate-heavy ratio
- rewrite 后增益
- source-specific 噪声率

### 4.4 覆盖率与补采效果指标

- taxonomy 覆盖增长
- source diversity 增长
- component family 覆盖增长
- gap fill ROI
- corroboration density 增长

### 4.5 告警与弱信号指标

- 高价值告警 precision
- alert reviewer 过滤率
- source drift 检出率

## 5. 区分一次到位的设计和弱实现的设计

本节是 Phase 0 的核心约束：哪些东西必须从第一天就按完整系统设计，哪些东西可以在保持接口稳定的前提下先用弱实现。

### 5.1 必须一次设计到位的基础结构

#### `State Schema` 与节点 handoff contract
- 必须一次设计到位
- 原因：后续要支持 query reflection、coverage 回流、A2A 协作，如果 state 先按简化场景设计，后面会大面积返工
- 约束：从一开始就支持 `run_id`、`trace_id`、`query_run_id`、`raw_id`、`attack_id`、`artifact_ref`、`confidence`、`reason`

#### `Query Telemetry` 模型
- 必须一次设计到位
- 原因：search reflection 和 source 调度都依赖历史 query outcome，后补数据会导致系统无法学习
- 约束：从第一批 source 起就记录 query、rewrite、结果数量、噪声、novelty 等摘要

#### `Coverage Gap` 数据模型
- 必须一次设计到位
- 原因：不能只按单一 taxonomy 临时建模，否则后续扩展到 source diversity、component family、corroboration 会重做
- 约束：至少预留 `taxonomy`、`source`、`component family` 三个维度

#### `Source Abstraction` 与 collector 接口
- 必须一次设计到位
- 原因：structured source、paper source、community source、advisory source 的抓取行为不同，但都要进入统一调度和 telemetry 体系
- 约束：统一输入输出协议，保留 source-specific 配置扩展位

#### 输出对象 schema
- 必须一次设计到位
- 原因：WP1-1 的输出会被 WP1-2/后续模块消费，不能先用临时 dict 再重构
- 约束：结构化攻击情报、coverage gap 结果、告警/复核对象都要提前定义稳定字段

#### `artifact_ref` 优先的状态传递原则
- 必须一次设计到位
- 原因：如果节点间从一开始就传大文本 payload，后面性能、checkpoint 和 A2A 质量都会出问题
- 约束：正文尽快持久化，图状态只保留引用与摘要

### 5.2 允许先弱实现、后续增强的能力

#### source 数量
- 允许先弱实现
- 做法：先启用首批 source，但 source registry 和 scheduler 结构按全量扩展设计

#### query rewrite 算法
- 允许先弱实现
- 做法：Phase 1 可以先用轻量 LLM reflection + 明确护栏，不建议把规则式 reflection 作为长期主路径；后续可升级为 bandit、学习排序或更强模型

#### rerank / dedup 精度
- 允许先弱实现
- 做法：先用 hash + embedding + 简单 rerank；后续再接 cross-encoder 或更复杂裁决器

#### coverage ROI 策略
- 允许先弱实现
- 做法：先用规则阈值和启发式分数；后续再升级为 contextual bandit 或在线学习

#### 人工审查界面
- 允许先弱实现
- 做法：先保证 queue 和审计结构存在；完整产品化界面后续再做

### 5.3 一条总的实现规则

- 设计层面按完整系统做
- 实现层面允许首阶段弱实现
- 任何弱实现都不能破坏后续扩展接口
- 任何临时方案都不能绕开 telemetry、reason 和 artifact_ref 原则

## 6. 调整后的 Phase 0 文档思路

为了避免后续返工，Phase 0 的文档不再使用“先做 MVP 再补”的表述，而采用“完整边界下的分阶段启用”思路。

### 6.1 文档表述调整原则

- 不再使用 `MVP source`，改为 `Phase 1 首批启用 source`
- 不再使用 `MVP 闭环`，改为 `Phase 1 可运行闭环`
- 不再使用“先凑合一版”，改为“接口一次定稳，能力逐步增强`
- 不再默认后续会大改 schema，而是默认 schema 从 Phase 0 起就是可扩展基线

### 6.2 Phase 0 之后文档应统一使用的说法

- `完整目标边界`
- `Phase 1 基线能力`
- `Phase 1 首批启用 source`
- `弱实现 / 强实现`
- `可扩展接口`
- `后续阶段增强项`

### 6.3 Phase 0 的真正产出

Phase 0 不是输出一个缩减版路线，而是输出一份不会让后续阶段反复返工的设计基线。其核心价值是：

- 统一术语
- 冻结边界
- 定稳 schema / state / contract
- 明确首批启用范围
- 明确哪些地方允许弱实现

## 7. Phase 0 完成标准

满足以下条件即可视为 Phase 0 完成：

- 术语与系统边界在团队内冻结
- Phase 1 首批启用 source 范围确定且有优先级
- 三类输出结构明确
- 成功指标定义完成并可用于后续评测设计
- 一次设计到位与弱实现的边界划分明确
- 后续 Phase 1 开发不再因概念模糊而频繁返工

## 8. 交付给 Phase 1 的输入清单

- 统一术语表
- Phase 1 首批启用 source 列表与优先级
- 输出对象定义草案
- 成功指标清单
- 一次设计到位清单
- 弱实现允许范围说明
- 运行约束与边界说明

本文件即为 WP1-1 Phase 0 的准备工作交付物。
