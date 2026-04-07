# WP1-2 交接说明

## 1. 当前状态

当前仓库已经收敛为“方案生成主线 + 轻量去重入口”。

正式入口不再是旧的 scheduler，而是：

`python -m saads_wp12.run_feed_once`

它负责：

- 从 feed provider 拉取情报引用
- 用本地 registry 做 `attack_id` 去重
- 把完整 feed 项直接送进主线
- 在 `artifacts/<run_id>/` 下落三层产物

## 2. 真正的业务主线

主线文件：

- `saads_wp12/agent.py`
- `saads_wp12/graphs/main_graph.py`

主线步骤：

`ingest_intel -> normalize_intel -> understand_threat_subgraph -> generate_test_package_subgraph -> validate_test_package -> finalize_plan_result -> persist_plan_artifacts`

## 3. 去重机制

当前去重不再依赖数据库 job 表。

现在使用：

- `artifacts/processed_attack_ids.json`

规则：

- 已处理成功的 `attack_id` 会登记进 registry
- 再次运行时会跳过这些 `attack_id`
- 跑失败的条目不会被登记，因此可以重试

## 4. 常用入口

正式入口：

```powershell
.\.venv\Scripts\python.exe -m saads_wp12.run_feed_once
```

本地单次验证：

```powershell
.\.venv\Scripts\python.exe -m saads_wp12.run_local
```

## 5. 产物说明

每次成功运行都会落：

- `*_state_raw.json`
- `*_state_presentation.json`
- `*_plan.md`

目录格式：

- `artifacts/<run_id>/`

## 6. 当前不再作为正式主线的内容

以下内容现在都属于历史方案或已废弃脚手架：

- `saads_wp12/scheduler/`
- `wp12_eval_jobs`
- job 状态回收 / reset 脚手架
- 执行脚本与环境构建链路
