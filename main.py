"""
SAADS - WP1-1 Intel Pipeline Debug Runner
==========================================
逐步调试入口：每个图节点执行完毕后打印状态差异，支持多种场景注入。

用法:
    python main.py                         # 标准 bootstrap stub 运行
    python main.py --mode incremental      # 增量模式
    python main.py --scenario low_yield    # 强制低收益（触发反思循环）
    python main.py --scenario gap_fill     # 强制覆盖缺口填补
    python main.py --scenario no_results   # 强制空结果
    python main.py --scenario fail_once    # 首次失败节点注入
    python main.py --scenario always_fail  # 永久失败节点注入
    python main.py --list-scenarios        # 列出所有预设场景
    python main.py --verbose               # 显示完整状态字段
    python main.py --mode gap_fill --scenario gap_fill --rounds 2
    python main.py --dry-run --live        # Print resolved config only
    python main.py --validate-suite wp11_bugfixes         # Run the bugfix suite
    python main.py --validate-suite wp11_persist_robustness  # Run the persistence suite
    python main.py --validate-suite wp11_llm_pool         # Run the LLM pool suite
    python main.py --mode bootstrap --scenario normal --verbose --live  # Full live run
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import textwrap
import time
from typing import Any

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# 加载 .env（必须在 backend 模块 import 之前）
from dotenv import load_dotenv
load_dotenv(dotenv_path=ROOT / ".env", override=False)

# Windows: 强制 stdout/stderr 使用 UTF-8，避免中文乱码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# 颜色/格式工具（无依赖）
# ---------------------------------------------------------------------------

_COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "cyan": "\033[36m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "white": "\033[37m",
}

_NO_COLOR = not sys.stdout.isatty()


def _c(text: str, *styles: str) -> str:
    if _NO_COLOR:
        return text
    codes = "".join(_COLORS.get(s, "") for s in styles)
    return f"{codes}{text}{_COLORS['reset']}"


def _sep(char: str = "-", width: int = 72) -> str:
    return _c(char * width, "dim")


def _header(title: str, width: int = 72) -> str:
    pad = max(0, (width - len(title) - 2) // 2)
    line = "=" * pad + f" {title} " + "=" * pad
    return _c(line, "bold", "cyan")


def _section(title: str) -> str:
    return _c(f"> {title}", "bold", "white")


# ---------------------------------------------------------------------------
# 场景定义
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, dict[str, Any]] = {
    "normal": {
        "description": "标准 stub 运行，全节点顺序执行",
        "fail_once_nodes": [],
        "always_fail_nodes": [],
        "force_low_yield": False,
        "force_gap_fill": False,
        "force_no_results": False,
    },
    "low_yield": {
        "description": "强制触发低收益 -> 反思循环 (reflect_search_strategy -> dispatch_collection)",
        "fail_once_nodes": [],
        "always_fail_nodes": [],
        "force_low_yield": True,
        "force_gap_fill": False,
        "force_no_results": False,
    },
    "gap_fill": {
        "description": "强制触发覆盖缺口填补 -> coverage_gap_analysis 路由回 supervisor_plan",
        "fail_once_nodes": [],
        "always_fail_nodes": [],
        "force_low_yield": False,
        "force_gap_fill": True,
        "force_no_results": False,
    },
    "no_results": {
        "description": "强制空采集结果，测试零结果路径",
        "fail_once_nodes": [],
        "always_fail_nodes": [],
        "force_low_yield": False,
        "force_gap_fill": False,
        "force_no_results": True,
    },
    "fail_once": {
        "description": "standardize + bom_resolve 首次失败（重试后成功）",
        "fail_once_nodes": ["parse_and_standardize", "resolve_ai_bom"],
        "always_fail_nodes": [],
        "force_low_yield": False,
        "force_gap_fill": False,
        "force_no_results": False,
    },
    "always_fail": {
        "description": "reflect_search_strategy 永久失败，测试错误聚合",
        "fail_once_nodes": [],
        "always_fail_nodes": ["reflect_search_strategy"],
        "force_low_yield": False,
        "force_gap_fill": False,
        "force_no_results": False,
    },
    "compound": {
        "description": "低收益 + gap_fill 同时触发，完整压力测试",
        "fail_once_nodes": ["store_raw_records"],
        "always_fail_nodes": [],
        "force_low_yield": True,
        "force_gap_fill": True,
        "force_no_results": False,
    },
}

# 与 state.py 中 Annotated[list, operator.add] 一致的字段 —— 合并时追加而非覆盖
_LIST_ADD_FIELDS: frozenset[str] = frozenset({
    "source_execution_stats", "source_health_dashboard", "source_drift_alerts",
    "fetch_audits", "stored_raw_records", "stored_raw_ids", "ingest_audits",
    "raw_items", "query_telemetry", "collection_yield_summary",
    "llm_planning_audits", "llm_reflection_audits", "llm_standardization_audits",
    "llm_bom_resolution_audits", "llm_dedup_judgments", "dedup_decisions",
    "merge_audits", "coverage_gaps",
    "gap_fill_dispatch_plans", "llm_coverage_analysis_audits", "alert_candidates",
    "node_results", "errors", "completed_nodes",
    "processed_subject_ids", "skipped_subject_ids",
})
# Annotated[dict, merge_dicts] 字段
_DICT_MERGE_FIELDS: frozenset[str] = frozenset({"node_attempts", "source_cursors"})


def _merge_state(prev: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Reducer-aware state merge，对 operator.add 字段追加而非覆盖。"""
    merged = dict(prev)
    for k, v in update.items():
        if k in _LIST_ADD_FIELDS and isinstance(merged.get(k), list) and isinstance(v, list):
            merged[k] = merged[k] + v
        elif k in _DICT_MERGE_FIELDS and isinstance(merged.get(k), dict) and isinstance(v, dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    return merged


# 节点执行顺序（用于进度条）
NODE_ORDER = [
    "load_runtime_context",
    "supervisor_plan",
    "dispatch_collection",
    "collect_structured_sources",
    "collect_code_sources",
    "collect_paper_sources",
    "collect_community_sources",
    "collect_advisory_sources",
    "store_raw_records",
    "assess_collection_yield",
    "reflect_search_strategy",
    "parse_and_standardize",
    "semantic_dedup_and_merge",
    "resolve_ai_bom",
    "review_ai_bom_resolution",
    "score_confidence_and_novelty",
    "refresh_coverage_view",
    "coverage_gap_analysis",
    "generate_alerts",
    "finalize_run",
]

# 每个节点关注的状态字段
NODE_FOCUS: dict[str, list[str]] = {
    "load_runtime_context":         ["run_mode", "run_status", "runtime_context"],
    "supervisor_plan":              ["collection_plan", "llm_planning_audits"],
    "dispatch_collection":          ["collector_plans", "collection_coordination"],
    "collect_structured_sources":   ["raw_items", "fetch_audits", "query_telemetry"],
    "collect_code_sources":         ["raw_items", "fetch_audits", "query_telemetry"],
    "collect_paper_sources":        ["raw_items", "fetch_audits"],
    "collect_community_sources":    ["raw_items", "fetch_audits"],
    "collect_advisory_sources":     ["raw_items", "fetch_audits"],
    "store_raw_records":            ["stored_raw_ids", "stored_raw_records", "ingest_audits"],
    "assess_collection_yield":      ["collection_yield_summary", "reflection_needed", "reflection_rationale"],
    "reflect_search_strategy":      ["llm_reflection_audits", "reflection_round", "reflection_needed"],
    "parse_and_standardize":        ["standardized_items", "llm_standardization_audits", "processed_count"],
    "semantic_dedup_and_merge":     ["dedup_decisions", "llm_dedup_judgments", "dedup_merged_count", "stable_attack_records", "dedup_persist_summary", "dedup_audit_summary"],
    "resolve_ai_bom":               ["llm_bom_resolution_audits", "bom_queue_count"],
    "review_ai_bom_resolution":     ["stable_attack_records"],
    "score_confidence_and_novelty": ["stable_attack_records", "new_attack_count"],
    "refresh_coverage_view":        ["source_health_dashboard", "coverage_gaps"],
    "coverage_gap_analysis":        ["coverage_gaps", "gap_fill_needed", "gap_fill_rationale", "gap_fill_round"],
    "generate_alerts":              ["alert_candidates"],
    "finalize_run":                 ["run_status", "finished_at", "errors"],
}

# ---------------------------------------------------------------------------
# 状态摘要工具
# ---------------------------------------------------------------------------

def _count_or_val(v: Any) -> str:
    """将列表/字典显示为计数，标量直接显示。"""
    if isinstance(v, list):
        return f"[{len(v)} items]"
    if isinstance(v, dict):
        return f"{{...{len(v)} keys}}"
    if isinstance(v, str) and len(v) > 80:
        return repr(v[:77] + "...")
    return repr(v)


def _summarise_state(state: dict[str, Any], keys: list[str], verbose: bool = False) -> list[str]:
    lines = []
    for k in keys:
        v = state.get(k)
        if v is None:
            continue
        if verbose:
            formatted = json.dumps(v, default=str, indent=2, ensure_ascii=False)
            wrapped = textwrap.indent(formatted, "    ")
            lines.append(f"  {_c(k, 'yellow')}: {wrapped}")
        else:
            lines.append(f"  {_c(k, 'yellow')}: {_count_or_val(v)}")
    return lines


def _diff_state(before: dict[str, Any], after: dict[str, Any]) -> dict[str, tuple[Any, Any]]:
    """返回在 before → after 中发生变化的字段。"""
    changed: dict[str, tuple[Any, Any]] = {}
    all_keys = set(before) | set(after)
    for k in all_keys:
        bv = before.get(k)
        av = after.get(k)
        # 对于列表：比较长度变化
        if isinstance(bv, list) and isinstance(av, list):
            if len(bv) != len(av):
                changed[k] = (bv, av)
        elif isinstance(bv, dict) and isinstance(av, dict):
            if bv != av:
                changed[k] = (bv, av)
        elif bv != av:
            changed[k] = (bv, av)
    return changed


# ---------------------------------------------------------------------------
# 流式调试器
# ---------------------------------------------------------------------------

class StepDebugger:
    """
    包装 Phase1GraphRuntime，通过 LangGraph stream() 逐节点打印调试信息。
    """

    def __init__(self, verbose: bool = False):
        from backend.agents.intel_agents.orchestrator.runtime import Phase1GraphRuntime
        from backend.agents.intel_agents.orchestrator.state import build_initial_state
        from backend.agents.intel_agents.schemas.runtime import RuntimeContextDTO

        self._runtime_cls = Phase1GraphRuntime
        self._build_initial_state = build_initial_state
        self._RuntimeContextDTO = RuntimeContextDTO
        self.verbose = verbose
        self.runtime = Phase1GraphRuntime()

    # ------------------------------------------------------------------
    def run(
        self,
        run_mode: str = "bootstrap",
        scenario: str = "normal",
        gap_fill_rounds: int = 1,
        live: bool = False,
    ) -> dict[str, Any]:
        cfg = SCENARIOS[scenario]

        print(_header("SAADS WP1-1 Intel Pipeline - Step Debugger"))
        print()
        print(_section("运行配置"))
        print(f"  run_mode  : {_c(run_mode, 'green')}")
        print(f"  mode      : {_c('LIVE' if live else 'stub', 'green' if live else 'yellow')}")
        print(f"  scenario  : {_c(scenario, 'green')} - {cfg['description']}")
        print(f"  gap_rounds: {gap_fill_rounds}")
        if cfg["fail_once_nodes"]:
            print(f"  fail_once : {cfg['fail_once_nodes']}")
        if cfg["always_fail_nodes"]:
            print(f"  always_fail: {cfg['always_fail_nodes']}")
        print()

        import os as _os
        if live:
            # 生产模式：真实 API 采集，所有策略 llm_required
            runtime_ctx = self._RuntimeContextDTO.default_live(
                run_mode=run_mode,
                coverage_max_gap_fill_rounds=gap_fill_rounds,
            )
        else:
            # Stub 模式：注入调试场景，LLM 根据 OPENAI_API_KEY 自动降级
            _base_ctx = self._RuntimeContextDTO.default_stub(
                run_mode=run_mode,
                fail_once_nodes=cfg["fail_once_nodes"],
                always_fail_nodes=cfg["always_fail_nodes"],
                force_low_yield=cfg["force_low_yield"],
                force_gap_fill=cfg["force_gap_fill"],
                force_no_results=cfg["force_no_results"],
                coverage_max_gap_fill_rounds=gap_fill_rounds,
            )
            _llm_model = _os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            _use_llm = bool(_os.getenv("OPENAI_API_KEY"))
            _llm_strategy = "llm_optional" if _use_llm else "rules_only"
            _ctx_dict = _base_ctx.model_dump(mode="python")
            _ctx_dict.update({
                "planning_strategy":        _llm_strategy,
                "reflection_strategy":      _llm_strategy,
                "standardization_strategy": _llm_strategy,
                "dedup_merge_strategy":     _llm_strategy,
                "bom_resolution_strategy":  _llm_strategy,
                "coverage_strategy":        _llm_strategy,
                "llm_model":                _llm_model,
            })
            runtime_ctx = self._RuntimeContextDTO.model_validate(_ctx_dict)
        initial_state = self._build_initial_state(
            run_mode=run_mode,
            runtime_context=runtime_ctx.model_dump(mode="python"),
        )

        run_id = initial_state["run_id"]
        trace_id = initial_state["trace_id"]
        print(f"  run_id  : {_c(run_id, 'cyan')}")
        print(f"  trace_id: {_c(trace_id, 'cyan')}")
        print()
        print(_sep())

        # 流式执行
        config: Any = {"configurable": {"thread_id": run_id}}
        node_times: dict[str, float] = {}
        prev_state: dict[str, Any] = dict(initial_state)
        node_seq: list[str] = []
        t_total = time.perf_counter()

        for chunk in self.runtime.app.stream(initial_state, config=config):
            for node_name, state_update in chunk.items():
                t_node = time.perf_counter()
                node_seq.append(node_name)
                idx = len(node_seq)

                # 合并状态（用于 diff）—— 对 operator.add 字段追加而非覆盖
                merged = _merge_state(prev_state, state_update)

                # 计算变化
                changed = _diff_state(prev_state, merged)
                focus_keys = NODE_FOCUS.get(node_name, [])

                # 节点标题
                errors_in_node = [
                    e for e in merged.get("errors", [])
                    if isinstance(e, dict) and e.get("node") == node_name
                ]
                status_icon = (
                    _c("[OK]", "green")
                    if not errors_in_node
                    else _c("[FAIL]", "red")
                )
                print(f"\n{status_icon} [{idx:02d}] {_c(node_name, 'bold', 'white')}")

                # 关注字段
                if focus_keys:
                    focus_lines = _summarise_state(merged, focus_keys, self.verbose)
                    for line in focus_lines:
                        print(line)

                # 状态变化 diff
                diff_keys = [k for k in changed if k not in focus_keys and k != "runtime_context"]
                if diff_keys and not self.verbose:
                    print(f"  {_c('changed', 'dim')}: ", end="")
                    parts = []
                    for k in sorted(diff_keys)[:8]:
                        bv, av = changed[k]
                        if isinstance(av, list):
                            delta = len(av) - (len(bv) if isinstance(bv, list) else 0)
                            parts.append(f"{k}(+{delta})" if delta >= 0 else f"{k}({delta})")
                        else:
                            parts.append(f"{k}={_count_or_val(av)}")
                    print(_c(", ".join(parts), "dim"))

                # 节点错误
                if errors_in_node:
                    for err in errors_in_node:
                        print(f"  {_c('ERROR', 'red', 'bold')}: {err.get('message', err)}")

                elapsed = time.perf_counter() - t_node
                node_times[node_name] = elapsed
                print(f"  {_c(f'{elapsed*1000:.1f}ms', 'dim')}")
                print(_sep("."))

                prev_state = merged

        final_state = prev_state
        total_elapsed = time.perf_counter() - t_total

        self._print_summary(final_state, node_seq, node_times, total_elapsed)
        return final_state

    # ------------------------------------------------------------------
    def _print_summary(
        self,
        state: dict[str, Any],
        node_seq: list[str],
        node_times: dict[str, float],
        total_elapsed: float,
    ) -> None:
        print()
        print(_header("运行摘要"))
        print()

        # 运行状态
        status = state.get("run_status", "unknown")
        status_color = "green" if status == "succeeded" else "red" if status == "failed" else "yellow"
        print(_section("状态"))
        print(f"  run_status   : {_c(status, status_color, 'bold')}")
        print(f"  finished_at  : {state.get('finished_at', 'N/A')}")
        print(f"  total_elapsed: {_c(f'{total_elapsed:.2f}s', 'cyan')}")
        print()

        # 数据指标
        print(_section("数据指标"))
        metrics = [
            ("raw_items",            len(state.get("raw_items", []))),
            ("stored_raw_ids",       len(state.get("stored_raw_ids", []))),
            ("standardized_items",   len(state.get("standardized_items", []))),
            ("stable_attack_records",len(state.get("stable_attack_records", []))),
            ("dedup_decisions",      len(state.get("dedup_decisions", []))),
            ("coverage_gaps",        len(state.get("coverage_gaps", []))),
            ("alert_candidates",     len(state.get("alert_candidates", []))),
        ]
        for name, val in metrics:
            bar = "#" * min(val, 20)
            print(f"  {name:<28}: {_c(str(val).rjust(4), 'green')}  {_c(bar, 'blue')}")
        print()

        # 计数器
        print(_section("计数器"))
        for k in ("processed_count", "dedup_merged_count", "new_attack_count",
                  "bom_queue_count", "reflection_round", "gap_fill_round"):
            v = state.get(k, 0)
            print(f"  {k:<28}: {_c(str(v), 'cyan')}")
        print()

        # 节点执行序列
        print(_section("节点执行序列"))
        completed = set(state.get("completed_nodes", []))
        for i, node in enumerate(node_seq, 1):
            elapsed_ms = node_times.get(node, 0) * 1000
            tick = _c("[OK]", "green") if node in completed else _c("[PEND]", "dim")
            print(f"  {tick} [{i:02d}] {node:<36} {_c(f'{elapsed_ms:.1f}ms', 'dim')}")
        print()

        # 错误列表
        errors = state.get("errors", [])
        if errors:
            print(_section(f"错误 ({len(errors)})"))
            for err in errors:
                if isinstance(err, dict):
                    node = err.get("node", "?")
                    msg  = err.get("message", str(err))
                    print(f"  {_c(node, 'red')}: {msg}")
                else:
                    print(f"  {_c(str(err), 'red')}")
            print()
        else:
            print(_section("错误: 无"))
            print()

        # 慢节点 Top-3
        if node_times:
            slow = sorted(node_times.items(), key=lambda x: x[1], reverse=True)[:3]
            print(_section("最慢节点 (Top 3)"))
            for rank, (node, t) in enumerate(slow, 1):
                print(f"  #{rank} {node:<36} {_c(f'{t*1000:.1f}ms', 'yellow')}")
            print()


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="SAADS WP1-1 后端逐步调试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            [f"  {k:<14}: {v['description']}" for k, v in SCENARIOS.items()]
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["bootstrap", "incremental", "gap_fill", "mixed"],
        default="bootstrap",
        help="LangGraph run_mode (default: bootstrap)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="使用 default_live() 模式：真实 API 采集 + 全链路 LLM（需配置 OPENAI_API_KEY）",
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="normal",
        help="调试注入场景 (default: normal)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        metavar="N",
        help="coverage_max_gap_fill_rounds (default: 1)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示完整状态字段 JSON",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="列出所有预设调试场景并退出",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印配置，不实际运行",
    )
    parser.add_argument(
        "--validate-suite",
        choices=["wp11_bugfixes", "wp11_persist_robustness", "wp11_llm_pool"],
        help="运行内置验证套件并退出",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.list_scenarios:
        print(_header("预设调试场景"))
        print()
        for name, cfg in SCENARIOS.items():
            print(f"  {_c(name, 'green', 'bold')}")
            print(f"    {cfg['description']}")
            flags = {k: v for k, v in cfg.items() if k != "description" and v}
            if flags:
                print(f"    flags: {flags}")
            print()
        return

    if args.dry_run:
        print(_section("Dry-run 配置"))
        print(f"  mode    : {args.mode}")
        print(f"  scenario: {args.scenario}")
        print(f"  rounds  : {args.rounds}")
        print(f"  verbose : {args.verbose}")
        print(f"  validate: {args.validate_suite}")
        return

    if args.validate_suite == "wp11_bugfixes":
        from backend.wp11_bugfix_validator import run_wp11_bugfix_suite

        sys.exit(run_wp11_bugfix_suite(verbose=args.verbose))
    if args.validate_suite == "wp11_persist_robustness":
        from backend.wp11_bugfix_validator import run_wp11_persist_robustness_suite

        sys.exit(run_wp11_persist_robustness_suite(verbose=args.verbose))
    if args.validate_suite == "wp11_llm_pool":
        from backend.wp11_bugfix_validator import run_wp11_llm_pool_suite

        sys.exit(run_wp11_llm_pool_suite(verbose=args.verbose))

    debugger = StepDebugger(verbose=args.verbose)
    try:
        final_state = debugger.run(
            run_mode=args.mode,
            scenario=args.scenario,
            gap_fill_rounds=args.rounds,
            live=args.live,
        )
    except KeyboardInterrupt:
        print(f"\n{_c('中断', 'yellow')} - 运行被用户终止")
        sys.exit(1)
    except Exception as exc:
        print(f"\n{_c('FATAL', 'red', 'bold')}: {exc}")
        raise

    # 非零退出码如果有未处理错误
    errors = final_state.get("errors", [])
    status = final_state.get("run_status", "unknown")
    if status == "failed" or (errors and status != "succeeded"):
        sys.exit(1)


if __name__ == "__main__":
    main()
