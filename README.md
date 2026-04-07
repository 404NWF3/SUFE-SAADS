# saads-wp12

WP1-2 当前定位是“大模型安全测试方案生成”模块，不再承担 job 调度或自动轮询职责。

当前稳定主线：

`ingest_intel -> normalize_intel -> understand_threat_subgraph -> generate_test_package_subgraph -> validate_test_package -> finalize_plan_result -> persist_plan_artifacts`

主线定义文件：

- `saads_wp12/agent.py`
- `saads_wp12/graphs/main_graph.py`

## Current Runtime Entry

当前推荐运行入口是：

`python -m saads_wp12.run_feed_once`

这个入口会：

- 从当前 feed provider 拉取情报
- 用 `artifacts/processed_attack_ids.json` 做本地去重
- 只处理还没跑过的 `attack_id`
- 直接把完整 feed 项送进主线
- 在 `artifacts/<run_id>/` 下落三层产物

常用环境变量：

- `WP12_FEED_SOURCE`
- `WP12_PROCESS_LIMIT`
- `WP12_DEDUP_REGISTRY_PATH`

产物目录：

- `artifacts/<run_id>/*_state_raw.json`
- `artifacts/<run_id>/*_state_presentation.json`
- `artifacts/<run_id>/*_plan.md`

建议优先阅读：

- [docs/wp12_operations_guide_zh.md](docs/wp12_operations_guide_zh.md)
- [docs/wp12_handover_guide_zh.md](docs/wp12_handover_guide_zh.md)
