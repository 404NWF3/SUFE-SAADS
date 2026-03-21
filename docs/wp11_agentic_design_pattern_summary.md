# WP1-1 中符合 Agentic Design Pattern 的设计总结

本文面向 PPT 展示场景，不再按 pattern 清单逐项罗列，而是按照“业务需求 -> 总体设计 -> Agentic Design 思想与代码落地 -> 总结”的方式重组，方便向老师和同学讲清楚：**为什么 WP1-1 需要做成智能体工作流，以及它具体是怎样落地的。**

## 1. WP1-1 应有的功能与实战需求

WP1-1 的目标，不是做一个通用聊天机器人，而是做一个面向 AI 安全情报采集与整理的运行系统。站在真实业务场景看，它至少要解决四类问题：

### 1.1 多源情报采集不是单一步骤，而是连续流程

我们需要从结构化漏洞源、代码安全源、论文源、社区讨论源、公告源等多个渠道采集 AI 安全相关情报。这意味着系统不能只做一次搜索，而要完成：

- 先决定采什么、采哪些源、每个源用什么查询策略；
- 再按不同 source 的特点执行采集；
- 最后把结果汇总、去重、标准化并生成后续分析结果。

因此，WP1-1 天然更适合被设计成一个**多阶段工作流系统**，而不是一次性问答式 Agent。

### 1.2 真实情报源存在噪声、重复、覆盖不均和失败风险

实际运行中会遇到很多问题：

- 某些 query 没有结果，或者噪声很高；
- 同一个攻击事件可能在多个源里重复出现；
- 某些 taxonomy 方向覆盖不足，需要补采；
- 外部 source 可能限流、失败、延迟，数据库也可能暂时不可用。

这要求系统具备**反思、重试、恢复、回退、监控**等能力，否则很难稳定运行。

### 1.3 情报处理不仅要“拿到结果”，还要“得到可信结果”

对 AI 安全情报来说，仅仅采到文本还不够，系统还要进一步完成：

- 标准化字段抽取；
- 语义去重与合并；
- AI BOM 组件映射；
- 置信度与新颖性评估；
- coverage gap 与 alert 候选生成。

这说明 WP1-1 的核心任务不是闲聊，而是**围绕目标任务逐步生产结构化结果**。

### 1.4 面向工程落地，必须可追踪、可恢复、可审计

如果系统要进入真实项目环境，就必须回答几个工程问题：

- 这次运行做到哪一步了？
- 哪个节点失败了？能否从中间恢复？
- 某个字段是规则抽取出来的，还是 LLM 补全的？
- 某个去重或 BOM 决策为什么成立？

这也是为什么 WP1-1 必须采用一种**状态显式、节点明确、审计可回放**的 agentic workflow 设计。

## 2. WP1-1 的总体设计

### 2.1 总体定位

如果用 `docs/Agent_Dev_Templates_template.ipynb` 的语言来概括，WP1-1 不是一个“开放式聊天 Agent”，而是一个：

> **以 LangGraph StateGraph 为主控制平面、以 typed state 为核心载体、以规划-执行-反思-恢复为骨架的 agentic workflow system。**

它的主线流程可以概括为：

`Runtime Load -> Planning -> Dispatch -> Parallel Collection -> Store -> Yield Assessment -> Reflection -> Standardize -> Dedup -> BOM Review -> Score -> Coverage Gap -> Alert -> Finalize`

### 2.2 总图如何落地在代码中

在代码层面，这一总设计主要由三部分构成：

1. **图结构**：`backend/agents/intel_agents/orchestrator/graph.py`
   - 用 `StateGraph(WP11GraphState)` 定义完整工作流；
   - 把每个阶段都建成独立节点；
   - 用 `add_edge` 和 `add_conditional_edges` 定义顺序流与条件流。

2. **统一状态**：`backend/agents/intel_agents/orchestrator/state.py`
   - `WP11GraphState` 把 `collection_plan`、`raw_items`、`query_telemetry`、`dedup_decisions`、`errors`、`completed_nodes` 等都显式纳入状态；
   - 多个字段通过 `Annotated[..., operator.add]` 或 `merge_dicts` 实现 merge-safe 聚合，适配并行分支。

3. **运行时包装**：`backend/agents/intel_agents/orchestrator/runtime.py`
   - `Phase1GraphRuntime` 使用 `MemorySaver` 作为 checkpoint；
   - 提供 `invoke()`、`get_state()`、`recover()`，把“运行、查看、恢复”做成一个完整 runtime。

所以，WP1-1 的总设计并不是“把 LLM 塞进流程里”，而是先把**任务分解、状态管理、节点协作、失败恢复**这些 agentic workflow 的基础设施搭好，再在局部节点中引入可选智能能力。

下面这段代码最能体现 WP1-1 的总体骨架：它不是单个 Agent 在自由对话，而是一个显式定义节点、边和条件路由的 StateGraph。

```python
def build_phase1_graph(*, checkpointer=None):
    graph = StateGraph(WP11GraphState)

    graph.add_node("load_runtime_context", load_runtime_context_node)
    graph.add_node("supervisor_plan", supervisor_plan_node)
    graph.add_node("dispatch_collection", dispatch_collection_node)
    graph.add_node("collect_structured_sources", collect_structured_sources_node)
    graph.add_node("collect_code_sources", collect_code_sources_node)
    graph.add_node("collect_paper_sources", collect_paper_sources_node)
    graph.add_node("collect_community_sources", collect_community_sources_node)
    graph.add_node("collect_advisory_sources", collect_advisory_sources_node)

    graph.set_entry_point("load_runtime_context")
    graph.add_conditional_edges("load_runtime_context", route_after_runtime_load, {...})
    graph.add_edge("supervisor_plan", "dispatch_collection")
    graph.add_conditional_edges("reflect_search_strategy", route_after_reflection, {...})

    return graph.compile(checkpointer=checkpointer)
```

## 3. 哪些地方体现了 Agentic Design Pattern

这一部分按“需求 + Agentic Design 思想 + 代码实现”来讲，形成闭环。

### 3.1 先规划再执行：符合 Planning / Goal Setting Pattern

#### 需求

多源情报采集不能直接“开抓”。系统必须先回答：本轮运行目标是什么、重点 taxonomy 是什么、各 source 用什么 query、并行度开多大、允许反思几轮。

#### Agentic Design 思想

这正对应模板里的 **Planning** 和 **Goal Setting**：先让系统形成一个明确、结构化、可执行的计划，再由后续执行节点按计划推进，而不是让每一步都临时决定。

#### 代码实现

- `backend/agents/intel_agents/agents/supervisor_agent.py` 中，`SupervisorAgent.plan_run()` 会根据 runtime context、coverage snapshot、source quality 等信息生成 `CollectionPlanDTO`；
- `backend/agents/intel_agents/schemas/plan.py` 把 plan 明确定义为 typed DTO，其中包含 `target_taxonomies`、`source_plans`、`max_parallel_sources`、`max_reflection_rounds`、`reflection_enabled` 等关键控制项；
- `backend/agents/intel_agents/orchestrator/nodes.py` 中，`supervisor_plan_node()` 在图执行早期就调用 `SupervisorAgent().plan_run(...)`，把“先规划”固定为主流程的一部分。

这说明 WP1-1 不是先有采集、后补控制，而是一开始就把“目标”和“执行约束”编码进系统状态里，这非常符合 agentic system 中的 plan-and-execute 思路。

对应的代表性源码如下。这里可以直接向老师同学展示：系统不是“临场发挥”，而是先产出一个结构化执行计划。

```python
class SupervisorAgent:
    def plan_run(
        self,
        runtime_context: dict[str, Any],
        coverage_snapshot: list[dict[str, Any]],
        source_quality_rows: list[dict[str, Any]],
        query_feedback_rows: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        ...
        plan = CollectionPlanDTO(
            run_mode=context.run_mode,
            rationale="Phase 1 baseline plan generated from runtime context and source registry.",
            target_taxonomies=target_taxonomies,
            source_plans=source_plans,
            max_parallel_sources=min(4, max(1, len(source_plans))),
            max_reflection_rounds=1,
            reflection_enabled=True,
        )
        return plan.model_dump(mode="python")
```

### 3.2 用状态图驱动流程推进：符合 Routing / Typed State Machine Pattern

#### 需求

WP1-1 不是线性的脚本。系统需要支持：

- 从不同节点恢复运行；
- 在 reflection 后决定是回到采集还是继续后处理；
- 在并行节点之间安全汇总中间结果。

如果没有显式工作流和状态路由，这种复杂控制会很快失控。

#### Agentic Design 思想

这对应模板中的 **Routing** 与 **LangGraph StateGraph** 思想：

- 让状态决定下一步去哪；
- 让图来承载控制流，而不是把所有逻辑揉进一个大函数；
- 让工作流本身成为 agentic intelligence 的一部分。

#### 代码实现

- `backend/agents/intel_agents/orchestrator/graph.py` 用 `StateGraph(WP11GraphState)` 定义整张图，并把 `load_runtime_context`、`supervisor_plan`、`dispatch_collection`、`parse_and_standardize`、`semantic_dedup_and_merge` 等都做成显式节点；
- 同文件中，`add_conditional_edges(...)` 负责两个关键条件分流：一是 runtime load 之后按照 `resume_target_node` 决定从哪里继续，二是 reflection 之后决定回到 `dispatch_collection` 还是进入 `parse_and_standardize`；
- `backend/agents/intel_agents/orchestrator/router.py` 中，`route_after_runtime_load()` 和 `route_after_reflection()` 把路由逻辑单独抽离出来；
- `backend/agents/intel_agents/orchestrator/state.py` 中，`WP11GraphState` 把运行期状态做成 merge-safe typed state，保证并行采集后的 `raw_items`、`fetch_audits`、`errors`、`node_results` 等都能安全累积。

因此，WP1-1 的 agentic 特征不只是“有很多节点”，更重要的是：**系统通过显式状态和显式路由来控制决策与推进。**

这里最适合展示的代码，是条件路由本身。它能非常直观地说明：流程的下一步由状态决定，而不是写死在单条脚本里。

```python
def route_after_runtime_load(
    state: WP11GraphState,
) -> Literal[
    "supervisor_plan",
    "dispatch_collection",
    "collect_structured_sources",
    "collect_code_sources",
    "parse_and_standardize",
    "finalize_run",
]:
    target = state.get("resume_target_node") or "supervisor_plan"
    return cast(..., target)


def route_after_reflection(
    state: WP11GraphState,
) -> Literal["dispatch_collection", "parse_and_standardize"]:
    if state.get("reflection_needed", False):
        return "dispatch_collection"
    return "parse_and_standardize"
```

### 3.3 多源并行 + 角色分工：符合 Parallelization / Multi-Agent Collaboration Pattern

#### 需求

不同情报源类型差异很大：论文、社区讨论、结构化漏洞源、代码安全源、公告源的采集方式并不相同。如果统一串行抓取，既慢，也难以体现 source specialization。

#### Agentic Design 思想

这对应两类模板思想：

- **Parallelization**：把可并行的任务拆开同时执行，提高吞吐；
- **Multi-Agent Collaboration**：给不同子任务配置不同角色，让系统体现 coordinator-worker 或 specialist 协作结构。

#### 代码实现

- `backend/agents/intel_agents/orchestrator/graph.py` 中，`dispatch_collection` 后直接 fan-out 到五类 collector 节点：`collect_structured_sources`、`collect_code_sources`、`collect_paper_sources`、`collect_community_sources`、`collect_advisory_sources`；
- `backend/agents/intel_agents/orchestrator/nodes.py` 中，`dispatch_collection_node()` 会把计划拆成 `collector_plans`，按不同 `collector_role` 分配给不同采集角色；
- 同文件中的 `_collector_node()` 会基于 `collector_role` 调用 `SourceCollectionCrew().collect(...)` 执行具体采集；
- `backend/agents/intel_agents/crews/crew_collaboration.py` 中，`CrewCollaborationService.coordinate()` 提供了 coordinator + specialist 的协作入口；当 CrewAI 可用时，会创建 coordinator 和多个 specialist agent；当 CrewAI 不可用时，又会退回 deterministic fallback，保证流程稳定；
- `backend/agents/intel_agents/services/source_scheduler.py` 中，`SourceScheduler.run()` 使用 `ThreadPoolExecutor` 对 source query 执行进一步并发调度。

因此，WP1-1 的并行不是单层并发，而是：

- 上层图结构负责“任务分派并行”；
- 下层调度器负责“source 请求并发”；
- 协调层负责“不同角色的职责分工”。

这正是一个比较典型的 agentic coordinator-worker 体系。

如果想在 PPT 里给出一个非常短的“并行证据”，下面这段代码就足够说明 WP1-1 确实在做 source 级并发调度：

```python
with ThreadPoolExecutor(max_workers=max(1, max_parallel_sources)) as executor:
    future_map = {
        executor.submit(
            self._execute_with_retry,
            source,
            query_run,
            runtime_mode=runtime_mode,
            timeout=request_timeout_seconds,
            retry_attempts=retry_attempts,
            cursor_state=cursor_state,
        ): (source, query_run)
        for source, query_run, cursor_state in work_items
    }
    for future in as_completed(future_map):
        source, query_run = future_map[future]
        batch = future.result()
```

### 3.4 低产出时会反思并回流：符合 Reflection Pattern

#### 需求

实际采集中，经常会出现 query 无结果、结果太少、噪声太高、source 不匹配等问题。如果系统只会“一次采完就结束”，那么采集质量会很不稳定。

#### Agentic Design 思想

这正对应模板中的 **Reflection**：

- 系统先评估当前结果；
- 再判断当前策略是否有效；
- 如果效果不好，就修正 query 或执行策略，再回到前面的节点重跑。

这本质上是一种 closed-loop，而不是一次性流水线。

#### 代码实现

- `backend/agents/intel_agents/orchestrator/nodes.py` 中，`assess_collection_yield_node()` 会先生成 `QueryTelemetryDTO` 和 `CollectionYieldSummaryDTO`，记录 `result_count`、`novelty_yield`、`noise_ratio`、`source_mismatch` 等信号，作为 LLM reflection 的观察窗口；
- 同文件中，`reflect_search_strategy_node()` 应调用 `SearchReflectionAgent().reflect(...)`，由大模型基于 telemetry、query intent、历史反馈和 source summary 决定是否 `should_retry`；
- `backend/agents/intel_agents/agents/search_reflection_agent.py` 不应长期停留在规则阈值触发器，而应升级为 LLM-primary reflection agent；规则只保留为 budget、source 语法和降级护栏；
- `backend/agents/intel_agents/orchestrator/router.py` 中，`route_after_reflection()` 根据 `reflection_needed` 把流程路由回 `dispatch_collection` 或继续后续节点；
- `backend/agents/intel_agents/orchestrator/state.py` 中的 `reflection_round` 则保证这一过程可被计数和限制。

所以，WP1-1 符合 Agentic Design 的地方，不只是“能改 query”，而是它把“评估结果 -> 反思策略 -> 回流执行”做成了图中的正式闭环。

更准确地说，真正体现 Agentic Design 的不是几个 if/else 规则，而是：系统把 telemetry 当成 observation，把 LLM reflection 当成 strategy policy，把预算/停止条件当成 safety guard。

```python
class SearchReflectionAgent:
    def reflect(
        self,
        source_runs: list[dict[str, Any]],
        query_telemetry: list[dict[str, Any]],
        collection_goals: dict[str, Any],
    ) -> dict[str, Any]:
        ...
        # LLM-first:
        # observe telemetry -> diagnose failure mode -> decide whether to retry
        # -> generate structured rewritten queries -> emit confidence/audit
```

### 3.5 用记忆支持去重和持续决策：符合 Memory Management Pattern

#### 需求

AI 安全情报会不断重复出现、持续演化。系统不能每次运行都把所有候选事件当成全新的，它必须知道：

- 历史上已经见过哪些稳定攻击记录；
- 当前候选是否与已有记录语义相似；
- 上一次运行保存了哪些中间状态，可以从哪里恢复。

#### Agentic Design 思想

这对应模板里的 **Memory Management**，但 WP1-1 的记忆比“对话记忆”更工程化：

- 运行态记忆：图状态和 checkpoint；
- 语义记忆：向量召回历史攻击签名；
- 事实记忆：DB 中持久化的 stable attack records。

#### 代码实现

- `backend/agents/intel_agents/orchestrator/runtime.py` 中，`Phase1GraphRuntime` 默认使用 `MemorySaver` 保存 checkpoint，并暴露 `get_state()` 和 `recover()`；
- `backend/agents/intel_agents/orchestrator/state.py` 中，`WP11GraphState` 把 `completed_nodes`、`node_attempts`、`stored_raw_records`、`source_cursors` 等恢复所需信息都纳入状态；
- `backend/agents/intel_agents/services/attack_signature_memory.py` 中，`AttackSignatureMemory` 使用本地 Qdrant 建立稳定攻击签名索引，`semantic_recall()` 可对候选攻击做向量检索；
- `backend/agents/intel_agents/services/dedup_memory_service.py` 中，`DedupMemoryService.load_records()` 会从 DB read model 读取既有 stable attack records，`save_records()` 和 `append_audits()` 又会把新的合并结果和审计结果写回数据库；
- `backend/agents/intel_agents/orchestrator/nodes.py` 中，`semantic_dedup_and_merge_node()` 同时调用 DB memory 和 vector memory，再交给 `DedupMergeAgent` 做决策。

这说明 WP1-1 不是“这轮运行结束后大脑清空”的系统，而是一个具备长期记忆与运行记忆的 agentic workflow。

下面这段 `semantic_recall()` 很适合用来说明：WP1-1 的“记忆”不是聊天上下文，而是可以被检索、参与决策的长期语义记忆。

```python
def semantic_recall(
    self,
    candidate: dict[str, Any],
    *,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    query_vector = generate_embedding(build_dedup_text(candidate))
    response = self.client.query_points(
        collection_name=self.collection_name,
        query=query_vector,
        limit=max(1, top_k),
        with_payload=True,
    )
    recalled = []
    for row in response.points:
        payload = row.payload or {}
        recalled.append(
            {
                "stable_attack_id": payload.get("stable_attack_id"),
                "canonical_name": payload.get("canonical_name"),
                "semantic_score": float(row.score),
            }
        )
    return recalled
```

### 3.6 结构化输出、保守复核与人工边界：符合 Guardrails / HITL Boundary Pattern

#### 需求

WP1-1 的后处理阶段涉及标准化、去重、BOM 组件解析等高风险决策。如果这些步骤完全自由生成、没有约束，很容易导致错误合并、错误组件映射，最终影响后续分析结果。

#### Agentic Design 思想

这对应模板中的 **Guardrails** 与部分 **Human-in-the-Loop** 思想：

- 重要输出必须结构化、可校验；
- 不确定决策不能强行自动通过，而应升级到 review queue；
- 智能体不是永远“替人拍板”，而是在有把握时自动化、没把握时显式暴露不确定性。

#### 代码实现

- `backend/agents/intel_agents/orchestrator/nodes.py` 中，所有节点返回 patch 前都会经过 `validate_patch(...)` 校验，确保图状态更新符合 schema；
- `backend/agents/intel_agents/schemas/plan.py` 以及其他 DTO schema，把运行计划、标准化结果、去重决策等关键对象都做成 typed DTO，而不是随意 dict；
- `backend/agents/intel_agents/orchestrator/nodes.py` 中，`parse_and_standardize_node()`、`semantic_dedup_and_merge_node()`、`resolve_ai_bom_node()` 都会把结果再用 DTO 进行验证后写回状态；
- `backend/agents/intel_agents/agents/bom_resolution_reviewer_agent.py` 中，`review_resolution()` 会对 vendor 冲突、版本约束不清、候选分数太接近、模糊匹配置信度不足等情况升级为 `review_queue`；
- 同文件还会把审查结论写入 `review` 字段，并汇总 `bom_queue_count`，使“不确定”本身成为系统显式输出，而不是被隐藏掉。

因此，WP1-1 虽然没有模板中那种真正的 `interrupt_before` 式人工中断点，但已经具备了很清晰的 HITL 边界：**高风险、不确定的结果进入人工复核队列。**

这一点可以直接用 BOM reviewer 的源码来证明：系统不会强行自动通过所有结果，而是会在不确定时主动升级人工复核。

```python
def review_resolution(self, resolution: dict[str, Any]) -> dict[str, Any]:
    checked = deepcopy(resolution)
    reasons: list[str] = []
    ambiguity_notes: list[str] = []
    decision = "accept"

    if checked.get("resolution_status") == "unresolved" or selected is None:
        decision = "review_queue"
        reasons.append("no confident component resolution available")
    else:
        ...
        if first - second < 0.05 and first < 0.9:
            decision = "review_queue"
            ambiguity_notes.append("multiple component candidates remain too close")
        if checked.get("match_mode") in {"trigram", "embedding"} and float(checked.get("match_confidence", 0.0)) < 0.85:
            decision = "review_queue"
            ambiguity_notes.append("fuzzy-only match needs manual confirmation")

    if decision == "review_queue":
        checked["resolution_status"] = "review_queue"
```

### 3.7 失败可重试、运行可恢复：符合 Exception Handling / Recovery-first Pattern

#### 需求

外部 source 抓取、数据库写入、下游处理都可能失败。如果系统一失败就整轮报废，不仅浪费资源，也很难支撑真实业务运行。

#### Agentic Design 思想

这对应模板中的 **Exception Handling & Recovery**。对于生产型 agentic system 来说，智能不只体现在“会推理”，还体现在：

- 失败时能否识别并控制影响范围；
- 能否重试、降级、回退；
- 能否从中间状态恢复，而不是每次从头开始。

#### 代码实现

- `backend/agents/intel_agents/orchestrator/nodes.py` 中，`_execute_with_retries()` 为所有节点提供统一重试包装，并在失败时把 `node_results` 和 `errors` 写回状态；
- 同文件中，`_should_skip_node()` 和 `completed_nodes` 配合使用，使恢复运行时可以跳过已经完成的节点；
- `backend/agents/intel_agents/orchestrator/runtime.py` 中，`recover()` 支持从指定节点恢复、部分 replay，并会把历史 `completed_nodes`、`raw_items`、`stored_raw_records`、`source_cursors` 等信息重新带入；
- `backend/agents/intel_agents/services/source_scheduler.py` 中，source 抓取具备 retry、backoff、throttle、circuit breaker 等机制；
- `backend/agents/intel_agents/crews/crew_collaboration.py` 中，即使 CrewAI 不可用，也会自动退回 deterministic fallback，避免协作层不可用导致主流程中断。

所以，WP1-1 的一个重要 agentic 特征是：它不是“理想条件下才成立”的 demo，而是把**失败后的行为**也设计进了系统。

最能说明这一点的，是 runtime 的 `recover()`。它不是简单重新运行，而是会带着旧状态从中间节点继续：

```python
def recover(
    self,
    run_id: str,
    *,
    reuse_run_id: bool = False,
    runtime_context_override: dict[str, Any] | None = None,
    resume_from_node: str | None = None,
    replay_query_run_ids: list[str] | None = None,
) -> dict[str, Any]:
    saved_state = self.get_state(run_id)
    ...
    recovered_state = build_initial_state(
        run_mode=saved_run_mode,
        runtime_context=merged_context,
        run_id=run_id if reuse_run_id else None,
        trace_id=saved_state.get("trace_id"),
        resume_target_node=resume_from_node,
    )
    if merged_context.get("skip_completed_nodes"):
        recovered_state["completed_nodes"] = completed_nodes
        recovered_state["stored_raw_records"] = list(saved_state.get("stored_raw_records", []))
        recovered_state["raw_items"] = list(saved_state.get("raw_items", []))
        recovered_state["source_cursors"] = dict(saved_state.get("source_cursors", {}))
    return self.invoke(recovered_state)
```

### 3.8 持续监控运行效果：符合 Monitoring / Evaluation-aware Pattern

#### 需求

一个情报系统不能只在最终输出时告诉我们“跑完了”。更重要的是知道：

- 哪些 source 贡献高、哪些 source 漂移了；
- 哪些 query 低产出；
- 哪些结果置信度高，哪些结果只是弱信号；
- 本轮运行到底是成功、部分成功还是存在较大风险。

#### Agentic Design 思想

这对应模板中的 **Goal Setting & Monitoring** 和部分 **Evaluation & Monitoring**：

- agentic system 要能够观测自己的执行质量；
- 监控结果不仅是运维指标，也会反过来影响后续决策，如 reflection、alert、gap fill。

#### 代码实现

- `backend/agents/intel_agents/orchestrator/nodes.py` 中，`_record_node_result()` 会把每个节点的状态、尝试次数、摘要、失败原因记录为 `NodeResultDTO`；
- 同文件中，`assess_collection_yield_node()` 生成 query telemetry 与 collection yield summary；
- `backend/agents/intel_agents/services/source_health_service.py` 会生成 source health dashboard 与 drift alerts；
- `backend/agents/intel_agents/orchestrator/nodes.py` 中，`generate_alerts_node()` 会基于 coverage gap 和 source drift 生成 alert candidates；
- `score_confidence_and_novelty_node()` 则把 dedup、source quality 等信息继续汇总为结果级置信度。

这说明 WP1-1 不是“执行完就结束”的黑盒，而是一个带有自我观测能力的 agentic workflow。

## 4. 总结

### 4.1 一句话定位

WP1-1 最符合 `Agent_Dev_Templates_template.ipynb` 的地方，不是聊天式 Agent，也不是通用 Tool Agent，而是：

> **一个以 LangGraph 为骨架、以 typed state 为核心、以规划-路由-并行-反思-记忆-恢复为主线的生产型 agentic workflow system。**

### 4.2 最值得在 PPT 里强调的几点

如果做展示，最建议强调下面四个结论：

1. **WP1-1 的“智能”首先体现在工作流层，而不是对话层。**
   - 它会先规划，再分派，再并行执行，再根据结果反思回流。

2. **WP1-1 的设计是围绕真实情报需求倒推出来的。**
   - 多源、噪声、重复、失败、覆盖不足、人工复核，这些真实问题决定了它必须采用 agentic workflow。

3. **WP1-1 的 agentic 特征已经有明确代码落点。**
   - 不是停留在概念上，而是落实到 `StateGraph`、`CollectionPlanDTO`、reflection loop、memory service、recover runtime、review queue 等具体实现上。

4. **WP1-1 更像“工程化智能体系统”，而不是“演示型智能体玩具”。**
   - 它保留了可选 LLM 增强，但主控制平面仍然是可审计、可恢复、可追踪的 deterministic workflow。

### 4.3 最终结论

综合来看，WP1-1 已经高度符合模板中的核心 Agentic Design Pattern，尤其体现在：

- **Planning**：先形成结构化目标与执行计划；
- **Routing**：由状态决定流程走向；
- **Parallelization**：多角色、多 source 并发执行；
- **Reflection**：根据采集结果闭环修正策略；
- **Memory Management**：结合运行时状态、向量记忆和 DB 事实记忆；
- **Recovery / Guardrails / Monitoring**：确保系统可恢复、可校验、可审计。

因此，WP1-1 可以被准确地描述为：

> **一个偏 deterministic control plane、带可选智能增强、面向真实 AI 安全情报生产场景的 agentic workflow system。**
