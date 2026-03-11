# WP1-1 LangGraph 状态图与 State Schema

## 1. 目标

WP1-1 是一个长期运行的情报采集与弱信号发现系统。它不是单次问答 Agent，而是一个带有调度、采集、标准化、去重、BOM 解析、覆盖率补采、事件告警的持续运行图。

Phase 1 仅覆盖公开源：
- NVD
- GitHub Security Advisories / Issues / Discussions
- arXiv
- HuggingFace
- Reddit
- Hacker News
- CISA KEV
- MITRE ATT&CK
- 厂商安全公告

不纳入：
- Telegram
- 暗网论坛
- Tor 代理链路

## 2. LangGraph 设计模式

WP1-1 采用以下 Agentic Design Pattern：

- Supervisor Pattern
  - `IntelSupervisorNode` 统一做策略判断与分派
- Planner-Executor Pattern
  - 先生成 `CollectionPlan`，再执行采集
- Reflection Pattern
  - 标准化与去重后增加质量复核
- Memory Pattern
  - PostgreSQL 保存事实与审计
  - ChromaDB 保存语义记忆与弱信号聚类
- Human-in-the-loop Pattern
  - BOM 无法唯一定位时进入 `bom_resolution_queue`

## 3. LangGraph 节点

### 3.1 主节点列表

1. `load_runtime_context`
2. `supervisor_plan`
3. `dispatch_collection`
4. `collect_from_sources`
5. `store_raw_records`
6. `parse_and_standardize`
7. `semantic_dedup_and_merge`
8. `resolve_ai_bom`
9. `score_confidence_and_novelty`
10. `refresh_coverage_view`
11. `coverage_gap_analysis`
12. `weak_signal_mining`
13. `generate_alerts`
14. `finalize_run`

### 3.2 节点职责

#### `load_runtime_context`
加载：
- 上次游标
- 来源配置
- 覆盖率快照
- source quality dashboard
- 未处理原始记录数
- 弱信号缓存状态

#### `supervisor_plan`
决定本轮模式：
- bootstrap
- incremental
- gap_fill
- weak_signal_focus
- mixed

输出：
- `CollectionPlan`
- `SourceExecutionPlan[]`
- `QueryExpansionPlan[]`

#### `dispatch_collection`
把 plan 分发到不同 collector agent。

#### `collect_from_sources`
执行 source-specific 抓取：
- NVD / GitHub / arXiv / Reddit / HuggingFace / HN / KEV / ATT&CK

#### `store_raw_records`
调用 `IngestionService` 入库原始记录，执行 hash 幂等。

#### `parse_and_standardize`
抽取：
- attack summary
- attack family
- evidence
- taxonomy guess
- CVSS hint
- AI BOM mentions
- STIX payload

#### `semantic_dedup_and_merge`
执行：
- Chroma 相似检索
- rerank
- 结构化字段校验
- merge/new/review 决策

#### `resolve_ai_bom`
对组件名、vendor、version 做匹配；失败则入 queue。

#### `score_confidence_and_novelty`
计算：
- confidence score
- source trust adjusted score
- novelty score
- weak-signal emergence score

#### `refresh_coverage_view`
批处理结束后刷新 `mv_owasp_coverage`。

#### `coverage_gap_analysis`
找低覆盖 OWASP LLM 类别，生成补采任务。

#### `weak_signal_mining`
对社区帖做：
- clustering
- burst detection
- attack precursor inference

#### `generate_alerts`
高危新攻击或高置信弱信号触发告警。

#### `finalize_run`
更新 run metadata、统计、cursor、失败清单。

## 4. 状态转移

```text
START
  -> load_runtime_context
  -> supervisor_plan
  -> dispatch_collection
  -> collect_from_sources
  -> store_raw_records
  -> parse_and_standardize
  -> semantic_dedup_and_merge
  -> resolve_ai_bom
  -> score_confidence_and_novelty
  -> refresh_coverage_view
  -> coverage_gap_analysis
  -> weak_signal_mining
  -> generate_alerts
  -> finalize_run
  -> END
```

### 条件分支

- `supervisor_plan`
  - 若 `mode=bootstrap`：扩大 source coverage、放宽时间窗口
  - 若 `mode=incremental`：按 cursor 增量抓取
  - 若 `mode=gap_fill`：优先追低覆盖 taxonomy
  - 若 `mode=weak_signal_focus`：优先社区与讨论源

- `semantic_dedup_and_merge`
  - `new_attack` -> `resolve_ai_bom`
  - `merge_existing` -> `resolve_ai_bom`
  - `needs_review` -> `resolve_ai_bom` + governance audit

- `coverage_gap_analysis`
  - 若 gap 很大，可回到 `dispatch_collection` 追加补采
  - 否则进入 `weak_signal_mining`

## 5. State Schema

建议用 `TypedDict + Pydantic DTO` 组合：
- LangGraph state 用 `TypedDict`
- 节点边界输入输出用 `Pydantic`

## 5.1 State TypedDict

```python
from __future__ import annotations

from typing import Any, Literal, TypedDict

RunMode = Literal["bootstrap", "incremental", "gap_fill", "weak_signal_focus", "mixed"]
RunStatus = Literal["queued", "running", "partial_success", "succeeded", "failed"]


class SourceCursorState(TypedDict, total=False):
    source_name: str
    cursor: str | None
    last_seen_at: str | None
    etag: str | None
    checkpoint_meta: dict[str, Any]


class SourceExecutionPlan(TypedDict):
    source_name: str
    source_type: str
    priority: float
    queries: list[str]
    max_results: int
    fetch_mode: Literal["bootstrap", "incremental", "targeted_gap_fill", "weak_signal"]
    time_window_days: int | None


class CollectionPlan(TypedDict):
    run_mode: RunMode
    rationale: str
    target_taxonomies: list[str]
    source_plans: list[SourceExecutionPlan]
    weak_signal_focus_terms: list[str]
    max_parallel_sources: int
    max_items_per_source: int


class RawCollectedItem(TypedDict, total=False):
    source_name: str
    source_uri: str
    external_id: str | None
    title: str | None
    content: str
    summary: str | None
    author: str | None
    published_at: str | None
    fetched_at: str
    raw_format: str
    metadata: dict[str, Any]
    content_hash: str


class BomMention(TypedDict, total=False):
    mentioned_name: str
    mentioned_vendor: str | None
    mentioned_version: str | None
    confidence_score: float


class TaxonomyGuess(TypedDict, total=False):
    taxonomy_type: Literal["OWASP_LLM", "CWE", "CAPEC", "ATTACK"]
    taxonomy_code: str
    taxonomy_name: str
    confidence_score: float
    is_primary: bool


class StandardizedIntel(TypedDict, total=False):
    raw_id: str
    attack_code: str
    canonical_name: str
    attack_family: str
    severity_level: str
    summary: str
    description: str
    exploit_preconditions: str | None
    impact_scope: str | None
    first_seen_at: str | None
    last_seen_at: str | None
    stix_type: str | None
    stix_payload: dict[str, Any] | None
    evidence_snippet: str | None
    bom_mentions: list[BomMention]
    taxonomy_items: list[TaxonomyGuess]
    cvss_hint: dict[str, Any] | None
    source_confidence: float
    extraction_confidence: float


class DedupDecision(TypedDict, total=False):
    decision: Literal["new", "merge", "review"]
    matched_attack_id: str | None
    similarity_score: float
    reasons: list[str]
    bom_delta_detected: bool
    narrative_delta_detected: bool


class WeakSignalCluster(TypedDict, total=False):
    cluster_id: str
    representative_text: str
    source_count: int
    post_count: int
    first_seen_at: str
    last_seen_at: str
    burst_score: float
    novelty_score: float
    precursor_probability: float
    inferred_attack_family: str | None
    inferred_bom_mentions: list[BomMention]


class CoverageGap(TypedDict):
    taxonomy_code: str
    taxonomy_name: str
    current_attack_count: int
    target_attack_count: int
    gap_score: float
    recommended_queries: list[str]
    recommended_sources: list[str]


class AlertCandidate(TypedDict, total=False):
    alert_type: Literal["new_high_risk_attack", "emerging_threat", "coverage_gap", "source_drift"]
    severity: Literal["low", "medium", "high", "critical"]
    title: str
    summary: str
    related_attack_id: str | None
    related_cluster_id: str | None
    evidence_uris: list[str]


class WP11GraphState(TypedDict, total=False):
    run_id: str
    trace_id: str
    started_at: str
    finished_at: str | None
    run_mode: RunMode
    run_status: RunStatus

    source_cursors: dict[str, SourceCursorState]
    collection_plan: CollectionPlan | None

    raw_items: list[RawCollectedItem]
    stored_raw_ids: list[str]
    standardized_items: list[StandardizedIntel]
    dedup_decisions: list[DedupDecision]

    weak_signal_clusters: list[WeakSignalCluster]
    coverage_gaps: list[CoverageGap]
    alert_candidates: list[AlertCandidate]

    processed_count: int
    dedup_merged_count: int
    new_attack_count: int
    bom_queue_count: int
    errors: list[dict[str, Any]]
```

## 5.2 关键状态约束

- `raw_items` 不直接长时间保留全部正文；正文应尽快落盘并只保留摘要/引用
- `standardized_items` 只保留待处理批次
- `dedup_decisions` 必须包含 `reasons`
- 任何 BOM 未解析项都必须反映到 `bom_queue_count`
- `coverage_gaps` 应来自数据库读模型，不在内存中手工估算

## 6. 推荐持久化策略

- PostgreSQL
  - 原始记录
  - 攻击主表
  - CVSS
  - taxonomy
  - BOM impact
  - dedup audit
  - unresolved BOM queue
- ChromaDB
  - 语义去重索引
  - 攻击签名记忆
  - 弱信号聚类索引
- LangGraph checkpoint
  - 运行中状态
  - 失败恢复
  - cursor / plan / partial batch progress

## 7. 运行模式建议

### bootstrap
- 宽时间窗口
- 高覆盖优先
- 相似性阈值略高，避免历史数据误并

### incremental
- 按 source cursor 增量
- 优先 freshness
- 对已知 attack family 做增量 merge

### gap_fill
- 输入来自 `mv_owasp_coverage`
- 按 taxonomy 缺口生成 targeted queries

### weak_signal_focus
- 重点抓 Reddit / HN / GitHub Issues / Discussions
- 强调 novelty 与 burst，不强依赖 CVE

## 8. 与 db 模块的对应关系

- 原始记录入库：`IngestionService`
- 攻击归并：`AttackMergeService`
- BOM 解析：`BomResolutionService`
- 覆盖率：`ReadModelRepository.list_owasp_coverage()`
- feed 对 WP1-2 输出：后续经 `v_wp12_attack_feed`

## 9. Phase 1 的成功标准

- 能完成 bootstrap + incremental + gap_fill
- 能执行 hash + vector 双层去重
- 能处理“相似攻击但不同 AI BOM”的增量更新
- 能识别社区求助帖中的弱信号
- 能把高危结果落到数据库并可供 WP1-2 消费
