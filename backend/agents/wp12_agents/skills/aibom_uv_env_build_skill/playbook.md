# Playbook

## 协作边界

- 智能体一提供已标准化的攻击与 AIBOM 结构化数据。
- 智能体二负责选择任务，并组装 `AIBOMEnvBuildRequest`。
- 本 skill 只负责局部补查、环境蓝图生成、uv 环境构建、基础健康检查与结构化结果返回。

## 输入输出约束

- 输入必须是 `AIBOMEnvBuildRequest` 兼容对象。
- 输出必须严格符合 `AIBOMEnvBuildResult`。
- `target_mode=uv_build_and_seed` 且缺少 seed 时，优先降级到 `uv_build` 并返回 `partial`。
- 组件解析允许 `exact` / `alias` / `fuzzy` / `unresolved` 四种结果。

## 推荐执行顺序

1. 校验输入并拒绝空组件列表。
2. 解析组件，优先使用外部解析器，其次使用本地 alias / fuzzy 兜底。
3. 生成环境蓝图，确定 `environment_id`、`workspace_path`、依赖清单与工件列表。
4. 写入 `pyproject.toml`、`run_attack.py`、`healthcheck.py` 和可选 seed 清单。
5. 非 `blueprint_only` 模式下执行 `uv venv`、`uv sync`、`uv run python healthcheck.py`。
6. 汇总 warning / error，返回 `ready` / `partial` / `failed`。

## 外部协作接口

skill 支持通过构造参数或函数参数注入以下能力：

- `component_candidate_provider(component) -> list[dict]`
- `bom_resolution_resolver(component) -> dict | ResolvedComponent | None`
- `seed_asset_loader(seed_asset_ids) -> list[dict]`
- `command_runner(command, cwd) -> CompletedProcess compatible`

这些接口只用于辅助补查或环境命令执行，不改变统一入口契约。
