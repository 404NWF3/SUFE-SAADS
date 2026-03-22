# 发现与证据：10 个问题现状复核

## 任务说明
本文件记录对 10 个问题的只读核查证据。每条结论都应尽量指向当前仓库中的具体文件、函数或配置。

## 当前发现
- 旧规划文件来自上一轮“修复任务”，不适合作为本轮复核上下文，已重置。
- 技能脚本可正常使用，但默认示例路径与当前环境不一致，需要改用 `.agents` 下的实际路径。

## 逐项结论
### Bug 1
- 结论：`已修复`
- 证据：
  - `StandardizerAgent.standardize_batch()` 已使用 `ThreadPoolExecutor` 并按 `standardization_max_concurrency` 控制并发，不再是串行 `for` 循环。
  - `RuntimeContextDTO.default_live()` 已通过 `recommended_task_concurrency()` 计算 live 默认并发。

### Bug 2
- 结论：`仍存在（被上层部分绕开）`
- 证据：
  - 多个 LLM 工具类构造器仍硬编码 `model: str = "gpt-5-mini"`。
  - agent 层虽然已改为 `resolve_default_model()`，但工具类默认值并未彻底收口，直接实例化或旁路调用仍会落回旧模型。
  - 测试中也仍显式断言或使用 `gpt-5-mini`，说明仓库基线仍承认该旧默认值。

### Bug 3
- 结论：`已修复`
- 证据：
  - `SupervisorAgent._fuse_llm_plan()` 已按 `source_name` 做每源唯一化，只保留最高优先级 plan。
  - `llm_supervisor_planning_tools.py` 的系统提示已加入规则 8：“每个 source_name 只能出现一次”。

### Bug 4
- 结论：`已修复`
- 证据：
  - `StandardizerAgent` 在 LLM 调用后显式检查 `if llm_result is None`，`llm_optional` 下会降级为 `rules_only_degraded`，`llm_required` 下抛出明确异常，不再把 `None` 传给后续校验。

### Bug 5
- 结论：`部分存在`
- 证据：
  - `RuntimeContextDTO.default_live()` 中 `persist_raw_records_to_db` 已改为 `True`。
  - 但 `DedupMemoryService.persist_records()` 仍通过 `AttackMergeService.merge_parsed_attack()` 间接写 evidence，未改成直接 `upsert_attack_entry_by_code()`。
  - `persist_records()` 外层仍是 `except Exception: return`，整批静默吞错问题仍在。

### Bug 6
- 结论：`已修复`
- 证据：
  - `AttackSignatureMemory` 现有 `upsert_record()` 增量写入接口。
  - `DedupMergeAgent` 只在循环前 `rebuild_index(stable_records)` 一次，循环内改为 `upsert_record(stable_record)`，避免每条记录全量重建索引。

### Bug 7
- 结论：`仍存在`
- 证据：
  - `DedupMemoryService.persist_records()` 仍把整个批次包在单个 `with UnitOfWork(...)` 中。
  - 如果其中一条写入触发数据库异常，后续记录仍有事务 aborted 级联失败风险。

### Bug 8
- 结论：`仍存在`
- 证据：
  - `load_records()` 读回的 CVSS 仍写成 `score_origin: "db_primary"`。
  - DB 层 DTO 仍要求 `score_origin` 只能是 `supplied|calculated|estimated|manual`。
  - `persist_records()` 仍直接 `source_raw_id=raw_id`，没有先做 UUID 归一化或置空。

### Bug 9
- 结论：`已修复`
- 证据：
  - `wp11_postgresql_schema.sql` 已包含 `component_layer` 列定义。
  - 同一文件还包含 `ADD COLUMN IF NOT EXISTS component_layer` 与 `ck_ai_component_layer` 约束迁移语句。

### Bug 10
- 结论：`部分存在`
- 证据：
  - `main.py` 已在 Windows 下把 stdout/stderr 包装为 UTF-8 `errors="replace"`。
  - 但 `main.py`、`backend/api/routers/wp11.py` 以及若干验证脚本仍直接输出 `✓/✗/○` 或 emoji，未统一改成 ASCII。
  - 仓库中未见这些验证脚本的 `sys.stdout.reconfigure(...)` 防护，因此 Windows 控制台风险未彻底清理。

## 汇总
- 已修复：Bug 1、3、4、6、9
- 仍存在：Bug 2、7、8
- 部分存在：Bug 5、10
