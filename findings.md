# 发现与决策

## 需求
- 用户希望将 `saads_wp12` 的功能模块完整接入 dashboard 的“渗透测试智能体”部分。
- 目标更偏向“完整接入方案设计”，需要覆盖前端页面、后端接口、状态流、产物展示和实施步骤。

## 研究发现
- `frontend/src/lib/wp-registry.ts` 已注册 `wp12`，名称为“渗透测试智能体”，`apiBase` 为 `/api/wp12`，SSE 路径为 `/api/wp12/logs/stream`。
- `frontend/src/app/dashboard/[wp]/page.tsx` 对 `sentinel` 有专门页面分支，说明 dashboard 已支持“某个 WP 使用定制内容页，其他 WP 使用通用面板”的模式。
- 后端当前已挂载的专用路由有 `wp11` 与 `sentinel`；`backend/api/server.py` 只 include 了这两个 router，`wp12` 在 registry 中已声明，但没有对应 FastAPI router。
- `backend/agents/saads_wp12` 已是完整可运行 agent，不是 stub：主线为 `ingest_intel -> normalize_intel -> threat_understanding -> test_package_generation -> validate -> finalize -> persist`。
- `saads_wp12` 当前通过 `graph.invoke(...)` 同步运行，没有现成的 dashboard run-store、SSE 日志流或异步任务控制层。
- `saads_wp12` 已具备适合前端消费的两类结果产物：
  - `presentation_state`：压缩后的结构化展示数据
  - `plan.md`：面向测试人员的 markdown 计划书
- `persist_plan_artifacts` 会把原始 state、presentation state、markdown plan 落到 `artifacts/<run_id>/` 目录，这天然适合做“结果详情页 / 历史记录”。
- `saads_wp12` 的 feed provider 已支持 `mock` / `local_json` / `db` 三种来源；数据库路径复用了 `wp11.v_wp12_attack_feed` 视图与 `Wp12FeedService`。
- 仓库文档仍把 `wp12` 标为 status stub（如 `docs/maintenance_backend.md`、`docs/frontend_deployment.md`），说明当前代码能力已经领先于文档约定。
- 数据库里已有 `v_wp12_attack_feed` 与 `v_wp12_attack_execution_feed` 视图，但尚未发现 `wp12_eval_job` 表定义；`backend/api/server.py` 对该表做了“可能不存在”的兼容查询。

## 技术决策
| 决策 | 理由 |
|------|------|
| 方案设计以“复用现有 dashboard 模式”为主 | 仓库里已经存在 `sentinel` 的完整前后端接入参考 |
| 重点关注 `saads_wp12` 的状态对象与持久化节点 | 它们将直接决定前端表单、结果页和历史记录的数据契约 |
| 结果展示优先围绕 `presentation_state` 和 markdown plan 设计 | 这是 `saads_wp12` 已经稳定产出的结果层 |
| `wp12` 应采用专用页面 + 专用 controller hook，而不是只靠通用 `MetricsPanel + LogViewer + AlertPanel` | 生成式测试方案需要输入表单、计划展示、详情切换与历史查看 |

## 遇到的问题
| 问题 | 解决方案 |
|------|---------|
| 宽泛搜索前端/后端关键字返回量过大并超时 | 缩小到 `wp12`、`sentinel`、dashboard 相关路径定向搜索 |

## 资源
- `backend/agents/saads_wp12`
- `frontend/src/lib/wp-registry.ts`
- `frontend/src/app/dashboard/[wp]/page.tsx`
- `backend/api/routers/sentinel.py`
- `backend/api/server.py`
- `backend/agents/saads_wp12/nodes/persistence.py`
- `backend/agents/saads_wp12/reporting/state_export.py`
- `backend/db/services/wp12_feed_service.py`
- `backend/db/wp11_postgresql_schema.sql`

## 视觉/浏览器发现
- 本轮主要在代码层面梳理，尚未使用浏览器或截图工具。
