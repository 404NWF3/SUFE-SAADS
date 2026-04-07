# WP1-2 操作手册

## 1. 当前口径

当前项目的正式运行入口是：

`python -m saads_wp12.run_feed_once`

它不是旧的 `scheduler` 轮询模式，而是一个更轻量的单次批处理入口：

- 先从当前 feed provider 拉取情报引用
- 用 `attack_id` 在本地 registry 中去重
- 只对未处理情报调用主线
- 成功后把结果记入 `artifacts/processed_attack_ids.json`

真正的业务主线定义在：

- `saads_wp12/agent.py`
- `saads_wp12/graphs/main_graph.py`

主线流程为：

`ingest_intel -> normalize_intel -> understand_threat_subgraph -> generate_test_package_subgraph -> validate_test_package -> finalize_plan_result -> persist_plan_artifacts`

## 2. 启动前确认

常见关键配置：

- `WP12_FEED_SOURCE=db` 或 `mock` 或 `local_json`
- `WP12_LLM_MODE=llm`
- `WP12_DB_FEED_TAXONOMY_CODES=OWASP-LLM-01,...,OWASP-LLM-10`
- `WP12_PROCESS_LIMIT`
- `WP12_DEDUP_REGISTRY_PATH`

如果使用数据库模式，还需要：

- `.env` 中数据库连接有效
- `SAADS_MAIN_BACKEND_PATH` 指向主项目 backend

## 3. 常用命令

### 3.1 单次处理新情报

```powershell
cd c:\Users\Administrator\Desktop\WP1-2
$env:WP12_PROCESS_LIMIT='1'
.\.venv\Scripts\python.exe -m saads_wp12.run_feed_once
```

### 3.2 指定 registry 路径

```powershell
$env:WP12_DEDUP_REGISTRY_PATH='artifacts\processed_attack_ids.json'
.\.venv\Scripts\python.exe -m saads_wp12.run_feed_once
```

### 3.3 数据库连通性最小检查

```powershell
@'
from saads_wp12.data.feed_provider import get_attack_feed_provider

provider = get_attack_feed_provider()
print(type(provider).__name__)
refs = provider.list_attack_feed_refs()
print("refs_count", len(refs))
print("first_refs", refs[:3])
'@ | .\.venv\Scripts\python.exe -
```

### 3.4 本地单次主线验证

```powershell
.\.venv\Scripts\python.exe -m saads_wp12.run_local
```

## 4. 三层产物

主线产物落在：

- `artifacts/<run_id>/`

包含：

- `*_state_raw.json`
- `*_state_presentation.json`
- `*_plan.md`

## 5. 本地去重

默认 registry 文件：

- `artifacts/processed_attack_ids.json`

规则：

- 已存在于 registry 的 `attack_id` 会被跳过
- 跑失败的情报不会写入 registry，因此后续还能重试

如果想重新处理某条情报，直接从 registry 中删掉它对应的 `attack_id` 即可。

## 6. 推荐入口

推荐：

- 正式跑新情报：`python -m saads_wp12.run_feed_once`
- 调试单次主线：`python -m saads_wp12.run_local`
- 批量实验：`saads_wp12.debug.run_batch_test_package_generation`

不再推荐：

- `saads_wp12.scheduler.run_scheduler`
- `saads_wp12.scheduler.reset_job_states`
