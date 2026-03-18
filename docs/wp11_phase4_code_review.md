# WP1-1 Phase 4 Code Review Notes

本文档记录当前对 WP1-1 Phase 4「多级去重、攻击归并与审计」实现的代码审查结论，重点覆盖：
- 已完成部分
- 当前风险与待完善部分
- 后续可持续优化方向

审查视角基于高级大模型应用工程实践，强调：语义召回与结构化裁决分层、BOM-aware 安全性、审计可追踪性、与数据库/向量记忆的一致性。

## 1. 总体结论

当前 Phase 4 已经从“规则占位去重”升级为“多级相似度 + 向量召回 + 二次审查 + DB 对齐”的完整工程实现。

当前已具备的核心能力：
- `content hash` exact dedup
- `SimHash / MinHash` 近重复过滤
- `Qdrant` 本地嵌入式 attack signature memory 语义召回
- rerank 与 taxonomy / CVE / BOM 结构化约束检查
- `DedupMergeAgent` 一轮系统裁决
- `DedupAdjudicatorAgent` 二次审查
- `new / merge / review` 决策输出
- `merge audit` 审计记录
- stable attack memory 与 DB/read-model 对齐

一句话判断：
- Phase 4 已经具备可运行、可审计、可扩展的高质量 dedup 主链路
- 但距离“高吞吐生产级 dedup platform”仍有若干可继续优化点，主要集中在召回质量、阈值校准、DB 写入策略和评测闭环

---

## 2. 已完成部分

## 2.1 多级去重链路

当前 Phase 4 已按分层思路完成：

### Level 1：精确去重
- `content hash` 精确去重已实现
- 适合完全重复或 artifact 一致的记录快速判重

### Level 2：近重复过滤
- 已实现 `SimHash`
- 已实现 `MinHash`
- 能对相似叙事但非完全相同文本做近重复检测

### Level 3：向量数据库语义召回
- 已实现 `Qdrant` 本地嵌入式 `attack signature memory`
- 用于对 stable attack records 做 top-k semantic recall
- 已明确“向量数据库只负责召回，不负责最终合并裁决”

### Level 4：重排
- 已实现基于：
  - embedding cosine
  - canonical_name 相似度
  - narrative 文本相似度
  的 rerank 近似层

### Level 5：结构化约束裁决
- 已接入：
  - taxonomy overlap
  - CVE overlap
  - BOM overlap
  - BOM delta 检查

### Level 6：二次审查
- 已实现 `DedupAdjudicatorAgent`
- 已支持：
  - `rules_only`
  - `llm_optional`
  - `llm_required`

---

## 2.2 核心 Agent / Service

### `DedupMergeAgent`
- 已实现主 dedup 决策链
- 能输出 `new / merge / review`
- 能生成 stable attack record 和 merge audit

### `DedupAdjudicatorAgent`
- 已实现 system decision 二次审查
- 已能在规则层和可选 LLM 层对 dedup 决策进行修正

### `AttackSignatureMemory`
- 已实现本地嵌入式 Qdrant 语义索引
- 已支持重建索引与 semantic recall

### `DedupMemoryService`
- 已由本地文件方案升级为 DB/read-model 对齐方案
- 能从 DB 聚合：
  - `attack feed`
  - `attack evidence`
  - `taxonomy`
  - `component impact`
- 并重建 stable attack memory

---

## 2.3 Schema 与审计

### 决策结构
- `DedupDecisionDTO` 已包含：
  - `decision`
  - `similarity_score`
  - `content_hash_match`
  - `simhash_score`
  - `minhash_score`
  - `embedding_score`
  - `rerank_score`
  - `taxonomy_overlap_score`
  - `cve_overlap_score`
  - `bom_overlap_score`
  - `bom_delta_detected`
  - `matched_candidate_ids`
  - `merge_audit_ref`
  - `adjudicator_summary`

### 稳定攻击单元
- `StableAttackRecordDTO` 已引入：
  - `stable_attack_id`
  - `stable_attack_code`
  - `source_coverage`
  - `related_raw_ids`
  - `member_attack_codes`

### 审计记录
- `MergeAuditRecordDTO` 已包含：
  - `candidate_raw_id`
  - `incoming_attack_code`
  - `matched_attack_id`
  - `similarity_score`
  - `reasons`
  - `bom_delta_detected`
  - `evidence_refs`
  - `source_coverage`

---

## 2.4 与 DB / Runtime 的集成

- `semantic_dedup_and_merge_node` 已接入 runtime 主链路
- dedup 结果已进入：
  - `dedup_decisions`
  - `stable_attack_records`
  - `merge_audits`
  - `standardized_items`（resolved version）
- DB 已完成：
  - source bootstrap
  - real remote PostgreSQL 连接验证
  - stable attack write-back
  - dedup audit write-back

---

## 3. 当前风险与待完善部分

## 3.1 相似度策略仍偏启发式

- 当前 `embedding` 仍是轻量规则向量，不是真实语义 embedding 模型
- `rerank` 也仍偏组合式启发打分，不是 cross-encoder / learned reranker
- 因此当前 Phase 4 在工程上是完整的，但在语义质量上仍有提升空间

影响：
- 对复杂同义叙事、跨 source 表达差异、弱结构化记录的召回质量可能仍有限

## 3.2 向量记忆重建策略较重

- 当前 `AttackSignatureMemory` 采用“运行时重建 collection”策略
- 这种方式简单稳定，但在 stable attack records 数量持续增大后，重建成本会上升

影响：
- 后续规模变大时，Phase 4 的 dedup 前置开销会明显增加

## 3.3 DB 对齐虽然已打通，但还偏同步型

- 当前 `DedupMemoryService` 直接在主链路中进行 DB 聚合读取与写回
- 对于当前规模是可接受的
- 但后续如果 batch size 和 source 数量继续扩大，读写时延会影响主图吞吐

影响：
- Phase 4 未来可能成为吞吐瓶颈之一

## 3.4 adjudicator 已接入 LLM，但还没有真实线上质量评测闭环

- 代码路径已具备
- 但目前更偏“能力存在”而不是“经过系统评测调优”

影响：
- 目前不能断言 LLM 审查一定优于规则审查
- 需要评测集和真实样本验证其收益

## 3.5 merge 策略还没有完全区分“事实合并”与“表示合并”

- 当前 stable attack record 重点是 dedup 后形成稳定知识单元
- 但未来可能需要更细地区分：
  - truly same attack
  - same attack family but different campaign
  - same narrative but different affected component/version

影响：
- 在高复杂真实数据下，`merge` 与 `review` 边界还需继续精炼

---

## 4. 后续可优化方向

## 4.1 检索质量增强

- 用真实 embedding 模型替换当前轻量 embedding
- 引入 cross-encoder 或更强 reranker
- 增强 source-specific semantic normalization，再做 recall

## 4.2 向量记忆层优化

- 将当前“全量重建”升级为增量 upsert
- 增加 collection version / index health 检查
- 增加 vector memory rebuild audit

## 4.3 adjudicator 评测闭环

- 建立 dedup gold set
- 分别评测：
  - rules only
  - llm optional
  - llm required
- 比较：
  - merge precision
  - review recall
  - false merge rate

## 4.4 BOM-aware 策略继续增强

- 继续提升 component alias 识别
- 将 vendor / version 约束进一步纳入 dedup 结构化裁决
- 对“语义相似但组件差异很大”的场景增加更强 guardrail

## 4.5 DB/read-model 聚合增强

- 为 stable attack memory 增加更明确的 read model 聚合层，而不是在 service 内部拼装全部字段
- 将 evidence / taxonomy / component impact 聚合成独立查询或物化视图

## 4.6 运行时可观测性增强

- 增加 dedup 阶段的指标：
  - recall candidate count
  - merge ratio
  - review ratio
  - bom-delta review ratio
  - adjudicator override ratio

---

## 5. 代码审查结论

### 已经达到的水平
- Phase 4 已经不是“基础去重占位逻辑”
- 已达到“完整 dedup pipeline”的工程实现标准
- 已经具备：
  - 多级信号
  - 语义召回
  - 二次审查
  - BOM-aware 决策
  - 审计闭环
  - DB/read-model 对齐

### 当前最强的部分
- 分层清晰：召回、打分、裁决、审查、审计职责分离
- BOM-aware 逻辑明确，没有粗暴 merge
- 与 runtime / DB 已真实打通

### 当前仍需继续加强的部分
- 语义质量仍可继续提升
- LLM adjudication 需要真实评测而不是只停留在能力路径
- 向量记忆层需要从“可用”进一步走向“高效稳定”

## 最终判断

- Phase 4 已经达到“高质量工程基线 + 可真实运行”的状态
- 可以安全支撑后续 Phase 5 / 6 开发
- 但若目标是研究级/生产级 dedup platform，后续仍应重点继续优化：
  - embedding / rerank 质量
  - vector memory 增量维护
  - adjudicator 评测闭环
  - DB 聚合查询性能
