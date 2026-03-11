# WP1-1 架构、目录结构与接口签名

## 1. 推荐目录结构

```text
backend/
  agents/
    intel_agents/
      __init__.py

      orchestrator/
        graph.py
        state.py
        nodes.py
        router.py
        runtime.py

      crews/
        source_collection_crew.py
        standardization_crew.py
        weak_signal_crew.py

      agents/
        supervisor_agent.py
        cve_collector_agent.py
        code_security_collector_agent.py
        paper_collector_agent.py
        community_signal_collector_agent.py
        standardizer_agent.py
        dedup_merge_agent.py
        bom_mapper_agent.py
        coverage_analyst_agent.py
        weak_signal_miner_agent.py
        alert_reviewer_agent.py

      tools/
        source_fetch_tools.py
        parsing_tools.py
        taxonomy_tools.py
        cvss_tools.py
        chroma_tools.py
        bom_tools.py
        coverage_tools.py
        weak_signal_tools.py
        db_bridge_tools.py

      skills/
        source_query_expansion.md
        attack_standardization_playbook.md
        dedup_adjudication_playbook.md
        ai_bom_resolution_playbook.md
        weak_signal_triage.md
        high_risk_alert_review.md

      memory/
        chroma_store.py
        embedding_provider.py
        collections.py

      schemas/
        plan.py
        intel.py
        dedup.py
        alert.py

      services/
        source_registry.py
        source_scheduler.py
        novelty_service.py
        burst_service.py
        quality_scoring_service.py
        rerank_service.py

      prompts/
        standardization_prompts.py
        weak_signal_prompts.py
        review_prompts.py

      runners/
        bootstrap_runner.py
        incremental_runner.py
        scheduler_runner.py
```

## 2. 模块职责

### `orchestrator/`
- LangGraph 状态机
- 节点路由
- checkpoint 恢复
- runtime context 加载

### `agents/`
- 真正有自主性的业务 Agent

### `tools/`
- LangChain tools
- 供 Agent 调用的稳定能力

### `skills/`
- 可复用工作流说明
- 适合用 OpenCode / Claude Code 风格封装

### `memory/`
- Chroma collection 管理
- embedding 生成
- 语义检索

### `services/`
- 纯 Python 算法与调度逻辑
- 不一定暴露成 LangChain tool

## 3. Agent 接口签名

### 3.1 SupervisorAgent

```python
class SupervisorAgent:
    def plan_run(
        self,
        runtime_context: dict,
        coverage_snapshot: list[dict],
        source_quality_rows: list[dict],
        weak_signal_summary: list[dict] | None = None,
    ) -> dict:
        """Return CollectionPlan."""
```

### 3.2 CveCollectorAgent

```python
class CveCollectorAgent:
    def collect(self, plan: dict) -> list[dict]:
        """Collect from NVD / KEV / ATT&CK-like structured sources."""
```

### 3.3 CodeSecurityCollectorAgent

```python
class CodeSecurityCollectorAgent:
    def collect(self, plan: dict) -> list[dict]:
        """Collect advisories, PoC clues, issue/discussion evidence from GitHub-like sources."""
```

### 3.4 PaperCollectorAgent

```python
class PaperCollectorAgent:
    def collect(self, plan: dict) -> list[dict]:
        """Collect papers, reports, model cards, and technical analyses."""
```

### 3.5 CommunitySignalCollectorAgent

```python
class CommunitySignalCollectorAgent:
    def collect(self, plan: dict) -> list[dict]:
        """Collect Reddit / HN / public discussion weak signals."""
```

### 3.6 StandardizerAgent

```python
class StandardizerAgent:
    def standardize_batch(self, raw_items: list[dict]) -> list[dict]:
        """Normalize raw items into StandardizedIntel objects."""
```

### 3.7 DedupMergeAgent

```python
class DedupMergeAgent:
    def dedup_and_merge(self, items: list[dict]) -> list[dict]:
        """Return DedupDecision for each item and execute merge policy."""
```

### 3.8 BomMapperAgent

```python
class BomMapperAgent:
    def map_bom(self, attack_records: list[dict]) -> list[dict]:
        """Resolve or enqueue AI BOM mentions."""
```

### 3.9 CoverageAnalystAgent

```python
class CoverageAnalystAgent:
    def analyze(self, coverage_rows: list[dict], recent_attacks: list[dict]) -> list[dict]:
        """Return coverage gaps and source/query recommendations."""
```

### 3.10 WeakSignalMinerAgent

```python
class WeakSignalMinerAgent:
    def mine(self, community_posts: list[dict]) -> list[dict]:
        """Return weak signal clusters and precursor scores."""
```

### 3.11 AlertReviewerAgent

```python
class AlertReviewerAgent:
    def review(self, attack_candidates: list[dict], weak_signal_clusters: list[dict]) -> list[dict]:
        """Return final alert candidates."""
```

## 4. LangGraph 节点接口签名

```python
def load_runtime_context_node(state: dict) -> dict: ...
def supervisor_plan_node(state: dict) -> dict: ...
def dispatch_collection_node(state: dict) -> dict: ...
def collect_from_sources_node(state: dict) -> dict: ...
def store_raw_records_node(state: dict) -> dict: ...
def parse_and_standardize_node(state: dict) -> dict: ...
def semantic_dedup_and_merge_node(state: dict) -> dict: ...
def resolve_ai_bom_node(state: dict) -> dict: ...
def score_confidence_and_novelty_node(state: dict) -> dict: ...
def refresh_coverage_view_node(state: dict) -> dict: ...
def coverage_gap_analysis_node(state: dict) -> dict: ...
def weak_signal_mining_node(state: dict) -> dict: ...
def generate_alerts_node(state: dict) -> dict: ...
def finalize_run_node(state: dict) -> dict: ...
```

## 5. ChromaDB 设计

建议 3 个 collections：

### `raw_intel_fingerprint`
用途：
- 原始文本近重复检测

metadata：
- `source_name`
- `source_uri`
- `published_at`
- `content_hash`
- `taxonomy_guess`
- `component_names`

### `attack_signature_memory`
用途：
- 标准化攻击对象相似检索
- merge/new/review 决策支持

metadata：
- `attack_id`
- `attack_code`
- `attack_family`
- `taxonomy_primary`
- `component_ids`
- `last_seen_at`

### `weak_signal_memory`
用途：
- 社区讨论聚类
- novelty / burst / precursor inference

metadata：
- `cluster_hint`
- `source_name`
- `community_type`
- `published_at`
- `suspected_attack_family`

## 6. 高质量算法设计建议

## 6.1 去重算法

### 目标
既要强去重，又不能错删“相似描述但不同 AI BOM”的真实情报。

### 方案
- Level 1: `content_hash`
- Level 2: `SimHash / MinHash`
- Level 3: `embedding cosine similarity`
- Level 4: `cross-encoder rerank`
- Level 5: 结构化约束比对
  - taxonomy overlap
  - CVE / GHSA / paper overlap
  - BOM overlap
  - version overlap

### 合并规则
- narrative 相似 + BOM 相同 -> `merge`
- narrative 相似 + BOM 新增 -> `merge + update attack_component_impact`
- narrative 相似 + BOM 冲突大 -> `review`
- narrative 不相似 -> `new`

## 6.2 BOM 实体解析算法

- alias normalization
- exact match
- alias match
- trigram retrieval
- embedding retrieval
- vendor-aware rerank
- version constraint normalization
- confidence thresholding
- unresolved queue fallback

## 6.3 弱信号发现算法

### 输入
- Reddit / HN / GitHub Discussions / Issues

### 方法
- 时间窗口嵌入聚类
- topic signature extraction
- burst detection
- novelty score
- precursor scoring

### 推荐指标
- `burst_score`
- `source_diversity`
- `semantic_cohesion`
- `attackability_score`
- `bom_relevance_score`

## 6.4 覆盖率补采算法

- 从 `mv_owasp_coverage` 读当前覆盖
- 为每个 taxonomy 计算：
  - attack count gap
  - source diversity gap
  - component coverage gap
- 再做 query expansion：
  - taxonomy term
  - synonym
  - framework name
  - attack family phrase
  - exploit symptom phrase

## 6.5 来源调度算法

Phase 1 推荐：
- priority score = source_trust * freshness_gain * gap_relevance * novelty_potential / expected_cost

Phase 2 可升级：
- contextual bandit
- Thompson sampling
- per-source ROI online learning

## 6.6 置信度校准

建议把最终置信度拆成：
- source trust
- extraction confidence
- dedup certainty
- bom resolution confidence
- evidence density
- source diversity bonus

## 7. Phase 1 MVP 顺序

1. LangGraph state + nodes
2. NVD / GitHub / arXiv / Reddit / HF / HN collectors
3. Ingestion + Standardization
4. Chroma 去重
5. BOM resolution
6. Coverage gap fill
7. Weak signal mining
8. Alert review

## 8. 与现有 db 层的集成原则

- Agent 不直接写 SQL
- Tool 层调用 `backend/db/services/*`
- 批量处理优先在事务外完成推理，在事务内只做确定写入
- `mv_owasp_coverage` 只在批次结束后刷新
