"""Sentinel workspace bridge router for the dashboard."""
from __future__ import annotations


import asyncio
import contextlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import websockets
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/sentinel", tags=["sentinel"])

_DEFAULT_AGENT_ID = "llm-security-intel"
_DEFAULT_WORKSPACE = Path.home() / ".openclaw" / "workspace-llm-security-intel"
_DEFAULT_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
_GATEWAY_PROTOCOL = 3
_MAX_HISTORY = 1200
_MAX_RUNS = 20
_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}

_COLLECTOR_COMMANDS: dict[str, list[str]] = {
    "full": ["src/other/daily_run.py"],
    "nvd": ["src/collectors/nvd_collector.py", "--days", "1", "--max-results", "200"],
    "github": [
        "src/collectors/github_collector.py",
        "--days",
        "1",
        "--max-results",
        "100",
        "--ai-mode",
    ],
    "arxiv": ["src/collectors/arxiv_collector.py", "--days", "7", "--max-results", "20"],
    "community": [
        "src/collectors/community_collector.py",
        "--hours",
        "24",
        "--source",
        "hackernews,reddit",
    ],
}

_COLLECTOR_NODE_NAMES: dict[str, str] = {
    "full": "daily_run",
    "nvd": "nvd_collector",
    "github": "github_collector",
    "arxiv": "arxiv_collector",
    "community": "community_collector",
}

_COLLECT_MODE_DESCRIPTIONS: dict[str, str] = {
    "full": "全量采集 NVD、GitHub Advisory、arXiv 与社区情报",
    "nvd": "采集 NVD / CVE 最新安全数据",
    "github": "采集 GitHub Security Advisory 与相关情报",
    "arxiv": "采集 AI 安全相关 arXiv 论文与研究动态",
    "community": "采集 Hacker News / Reddit 等社区安全信号",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _ensure_offset(dt_str: str) -> str:
    if dt_str and "+" not in dt_str and not dt_str.endswith("Z"):
        return dt_str + "+00:00"
    return dt_str


def _ms_to_iso(value: Any) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc).isoformat()
    if isinstance(value, str) and value:
        return _ensure_offset(value)
    return _now_iso()


def _same_path(left: Path | None, right: Path | None) -> bool:
    if left is None or right is None:
        return False
    return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(
        os.path.normpath(str(right))
    )


def _parse_window_hours(window: str) -> int:
    if match := re.match(r"(\d+)h$", window):
        return int(match.group(1))
    if match := re.match(r"(\d+)d$", window):
        return int(match.group(1)) * 24
    return 48


def _latest_daily_file(workspace_root: Path) -> Path | None:
    files = sorted((workspace_root / "kb" / "daily").glob("ai-threat-*.json"))
    return files[-1] if files else None


def _latest_memory_file(workspace_root: Path) -> Path | None:
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
    files = sorted(
        f for f in (workspace_root / "memory").glob("*.md") if date_pattern.match(f.name)
    )
    return files[-1] if files else None


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _read_coverage_snapshot(workspace_root: Path) -> dict[str, Any]:
    return _read_json_file(workspace_root / "kb" / "output" / "coverage-snapshot.json")


def _read_daily_intel(path: Path) -> dict[str, Any]:
    return _read_json_file(path)


def _owasp_coverage_pct(snapshot: dict[str, Any]) -> float:
    taxonomy = snapshot.get("dimensions", {}).get("taxonomy_source", {})
    covered = sum(
        1
        for category in taxonomy.values()
        if isinstance(category, dict) and category.get("total", 0) > 0
    )
    return round(min(covered, 10) / 10.0 * 100, 1)


def _intel_count(daily: dict[str, Any]) -> int:
    return int(daily.get("ai_related_count", 0) or 0)


def _high_risk_count(daily: dict[str, Any]) -> int:
    return sum(1 for item in daily.get("top5", []) if (item.get("cvss_score") or 0) >= 7.0)


def _derive_gateway_http_url(config: dict[str, Any]) -> str:
    gateway = config.get("gateway") or {}
    port = gateway.get("port") or 18789
    bind = gateway.get("bind") or "loopback"
    if bind in {"loopback", "localhost", "0.0.0.0", "::"}:
        host = "127.0.0.1"
    else:
        host = str(bind)
    return f"http://{host}:{port}"


def _http_to_ws(url: str) -> str:
    parsed = urlparse(url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse(parsed._replace(scheme=scheme))


def _extract_gateway_token(config: dict[str, Any]) -> str | None:
    gateway = config.get("gateway") or {}
    auth = gateway.get("auth") or {}
    token = auth.get("token")
    return str(token) if token else None


@dataclass(slots=True)
class OpenClawSettings:
    config_path: Path
    config_exists: bool
    config_error: str | None
    workspace_root: Path
    workspace_exists: bool
    workspace_source: str
    agent_id: str
    agent_configured: bool
    agent_workspace: Path | None
    agent_workspace_matches: bool
    gateway_http_url: str
    gateway_ws_url: str
    gateway_token: str | None
    hooks_enabled: bool
    hook_mapping_present: bool


def _load_openclaw_settings() -> OpenClawSettings:
    config_path = Path(os.getenv("OPENCLAW_CONFIG_PATH", str(_DEFAULT_CONFIG)))
    config_exists = config_path.exists()
    config_error: str | None = None
    config: dict[str, Any] = {}

    if config_exists:
        try:
            config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            config_error = f"failed to parse {config_path.name}: {exc}"

    agent_id = os.getenv("OPENCLAW_AGENT_ID", _DEFAULT_AGENT_ID)
    agent_list = (config.get("agents") or {}).get("list") or []
    agent_entry = next(
        (
            item
            for item in agent_list
            if isinstance(item, dict) and str(item.get("id")) == agent_id
        ),
        None,
    )
    agent_workspace = Path(agent_entry["workspace"]) if agent_entry and agent_entry.get("workspace") else None
    workspace_env = os.getenv("SENTINEL_WORKSPACE_ROOT")
    workspace_root = Path(workspace_env) if workspace_env else (agent_workspace or _DEFAULT_WORKSPACE)
    workspace_source = "env" if workspace_env else "openclaw-config"
    hooks = config.get("hooks") or {}
    mappings = hooks.get("mappings") or []

    hook_mapping_present = any(
        isinstance(item, dict)
        and (
            item.get("agentId") == agent_id
            or item.get("id") == "sentinel-collect"
            or (item.get("match") or {}).get("path") == "sentinel-collect"
        )
        for item in mappings
    )

    gateway_http_url = os.getenv("OPENCLAW_GATEWAY_URL") or _derive_gateway_http_url(config)

    return OpenClawSettings(
        config_path=config_path,
        config_exists=config_exists,
        config_error=config_error,
        workspace_root=workspace_root,
        workspace_exists=workspace_root.exists(),
        workspace_source=workspace_source,
        agent_id=agent_id,
        agent_configured=agent_entry is not None,
        agent_workspace=agent_workspace,
        agent_workspace_matches=_same_path(workspace_root, agent_workspace),
        gateway_http_url=gateway_http_url,
        gateway_ws_url=_http_to_ws(gateway_http_url),
        gateway_token=(
            os.getenv("OPENCLAW_GATEWAY_TOKEN")
            or os.getenv("OPENCLAW_HOOKS_TOKEN")
            or _extract_gateway_token(config)
        ),
        hooks_enabled=bool(hooks.get("enabled")),
        hook_mapping_present=hook_mapping_present,
    )


class OpenClawGatewayError(RuntimeError):
    """Raised when the OpenClaw Gateway RPC layer is unavailable."""


class OpenClawGatewaySession:
    """Thin RPC client for the OpenClaw Gateway WebSocket protocol."""

    def __init__(self, settings: OpenClawSettings):
        self.settings = settings
        self.websocket: Any = None
        self.protocol: int | None = None
        self.server_info: dict[str, Any] = {}
        self._request_index = 1
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._reader_task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> OpenClawGatewaySession:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def connect(self) -> None:
        if not self.settings.gateway_token:
            raise OpenClawGatewayError("gateway token is missing")

        try:
            self.websocket = await websockets.connect(
                self.settings.gateway_ws_url,
                open_timeout=10,
                close_timeout=5,
                ping_interval=20,
                ping_timeout=20,
                max_size=20_000_000,
            )
        except Exception as exc:
            raise OpenClawGatewayError(
                f"failed to connect to {self.settings.gateway_ws_url}: {exc}"
            ) from exc

        challenge = json.loads(await asyncio.wait_for(self.websocket.recv(), timeout=10))
        if challenge.get("type") != "event" or challenge.get("event") != "connect.challenge":
            raise OpenClawGatewayError("gateway did not send connect.challenge")

        await self.websocket.send(
            json.dumps(
                {
                    "type": "req",
                    "id": "connect",
                    "method": "connect",
                    "params": {
                        "minProtocol": _GATEWAY_PROTOCOL,
                        "maxProtocol": _GATEWAY_PROTOCOL,
                        "client": {
                            "id": "gateway-client",
                            "version": "saads-backend",
                            "platform": "python",
                            "mode": "backend",
                        },
                        "auth": {"token": self.settings.gateway_token},
                        "role": "operator",
                        "scopes": ["operator.admin"],
                    },
                }
            )
        )
        hello = json.loads(await asyncio.wait_for(self.websocket.recv(), timeout=10))
        if not hello.get("ok"):
            detail = (hello.get("error") or {}).get("message") or hello.get("payload") or "connect rejected"
            raise OpenClawGatewayError(f"gateway connect failed: {detail}")

        payload = hello.get("payload") or {}
        self.protocol = payload.get("protocol")
        self.server_info = payload.get("server") or {}
        self._reader_task = asyncio.create_task(self._reader_loop())

    async def close(self) -> None:
        if self._reader_task is not None:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task
            self._reader_task = None

        if self.websocket is not None:
            with contextlib.suppress(Exception):
                await self.websocket.close()
            self.websocket = None

        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

    async def _reader_loop(self) -> None:
        try:
            async for raw in self.websocket:
                message = json.loads(raw)
                if message.get("type") == "res":
                    request_id = str(message.get("id"))
                    future = self._pending.pop(request_id, None)
                    if future is not None and not future.done():
                        future.set_result(message)
                else:
                    await self._events.put(message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(
                        OpenClawGatewayError(f"gateway connection dropped: {exc}")
                    )
            self._pending.clear()
        finally:
            await self._events.put({"type": "event", "event": "_connection_closed"})

    async def call(
        self,
        method: str,
        params: dict[str, Any],
        *,
        timeout: float | None = 15.0,
    ) -> dict[str, Any]:
        if self.websocket is None:
            raise OpenClawGatewayError("gateway session is not connected")

        request_id = str(self._request_index)
        self._request_index += 1
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future

        await self.websocket.send(
            json.dumps(
                {
                    "type": "req",
                    "id": request_id,
                    "method": method,
                    "params": params,
                }
            )
        )

        try:
            if timeout is None:
                response = await future
            else:
                response = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError as exc:
            self._pending.pop(request_id, None)
            raise OpenClawGatewayError(f"{method} timed out after {timeout:.0f}s") from exc

        if not response.get("ok"):
            detail = (response.get("error") or {}).get("message") or response.get("payload") or "rpc failed"
            raise OpenClawGatewayError(f"{method} failed: {detail}")
        return response.get("payload") or {}

    async def next_event(self, timeout: float | None = None) -> dict[str, Any]:
        if timeout is None:
            return await self._events.get()
        return await asyncio.wait_for(self._events.get(), timeout=timeout)


@dataclass(slots=True)
class SentinelEvent:
    index: int
    payload: dict[str, Any]


@dataclass(slots=True)
class SentinelRun:
    run_id: str
    mode: str
    transport: str
    status: str
    started_at: str
    use_gateway: bool
    process: asyncio.subprocess.Process | None = None
    task: asyncio.Task[None] | None = None
    ended_at: str | None = None
    error: str | None = None
    gateway_run_id: str | None = None
    session_key: str | None = None
    assistant_buffer: str = ""
    assistant_text: str = ""
    cancel_requested: bool = False
    event_index: int = 0
    history: list[SentinelEvent] = field(default_factory=list)
    updated: asyncio.Event = field(default_factory=asyncio.Event)
    finished: asyncio.Event = field(default_factory=asyncio.Event)

    def add_event(self, payload: dict[str, Any]) -> None:
        self.event_index += 1
        self.history.append(SentinelEvent(index=self.event_index, payload=payload))
        if len(self.history) > _MAX_HISTORY:
            self.history = self.history[-_MAX_HISTORY:]
        self.updated.set()


_runs: dict[str, SentinelRun] = {}
_run_order: list[str] = []
_active_run_id: str | None = None
_runs_lock = asyncio.Lock()


def _run_summary(run: SentinelRun) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "status": run.status,
        "mode": run.mode,
        "transport": run.transport,
        "use_gateway": run.use_gateway,
        "started_at": run.started_at,
        "ended_at": run.ended_at,
        "error": run.error,
        "gateway_run_id": run.gateway_run_id,
        "session_key": run.session_key,
        "assistant_markdown": run.assistant_text or None,
    }


def _get_run(run_id: str) -> SentinelRun | None:
    return _runs.get(run_id)


def _get_active_run() -> SentinelRun | None:
    return _runs.get(_active_run_id) if _active_run_id else None


def _get_latest_run() -> SentinelRun | None:
    while _run_order:
        run_id = _run_order[-1]
        run = _runs.get(run_id)
        if run is not None:
            return run
        _run_order.pop()
    return None


def _trim_runs_locked() -> None:
    while len(_run_order) > _MAX_RUNS:
        oldest_id = _run_order.pop(0)
        if oldest_id == _active_run_id:
            _run_order.insert(0, oldest_id)
            break
        _runs.pop(oldest_id, None)


async def _finish_run(run: SentinelRun, status: str, error: str | None = None) -> None:
    run.status = status
    run.error = error
    run.ended_at = _now_iso()

    if run.assistant_buffer.strip():
        _emit_assistant_line(run, run.assistant_buffer, run.ended_at)
        run.assistant_buffer = ""

    if error:
        run.add_event(
            {
                "type": "error",
                "node": "sentinel",
                "message": error,
                "ts": run.ended_at,
            }
        )

    run.add_event(
        {
            "type": "done",
            "status": "succeeded" if status == "succeeded" else ("cancelled" if status == "cancelled" else "failed"),
            "percent": 100,
        }
    )
    run.finished.set()
    run.updated.set()

    async with _runs_lock:
        global _active_run_id
        if _active_run_id == run.run_id:
            _active_run_id = None
        _trim_runs_locked()


async def _register_run(mode: str, transport: str) -> SentinelRun:
    async with _runs_lock:
        global _active_run_id
        active = _get_active_run()
        if active and active.status not in _TERMINAL_STATUSES:
            raise HTTPException(status_code=409, detail="已有 Sentinel 采集任务正在运行")

        run = SentinelRun(
            run_id=uuid.uuid4().hex[:8],
            mode=mode,
            transport=transport,
            status="starting",
            started_at=_now_iso(),
            use_gateway=transport == "openclaw",
        )
        _runs[run.run_id] = run
        _run_order.append(run.run_id)
        _active_run_id = run.run_id
        _trim_runs_locked()
        return run


def _build_openclaw_message(mode: str) -> str:
    desc = _COLLECT_MODE_DESCRIPTIONS.get(mode, mode)
    return (
        "请在当前 workspace 中执行 Sentinel 安全情报任务。"
        f"采集模式：{mode}，目标：{desc}。"
        "优先使用现有脚本、技能与知识库目录完成采集、标准化、去重、按 OWASP LLM Top 10 分类，并在需要时更新日报或报告。"
        "在每个主要阶段开始时，请单独输出一行简短中文进度，格式必须是 [STATUS] <当前阶段>。"
        "例如：[STATUS] 正在采集 NVD、[STATUS] 正在整理 GitHub Advisory、[STATUS] 正在生成日报。"
        "如果缺少依赖、权限或配置，请直接明确报错原因。"
    )


def _build_subprocess_python(workspace_root: Path) -> Path:
    windows = workspace_root / ".venv" / "Scripts" / "python.exe"
    if windows.exists():
        return windows
    return workspace_root / ".venv" / "bin" / "python"


def _parse_optional_timeout_ms(name: str, default_ms: int | None) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default_ms

    value = raw.strip().lower()
    if value in {"0", "none", "off", "false", "unlimited", "infinite"}:
        return None

    parsed = int(value)
    return parsed if parsed > 0 else None


def _parse_optional_timeout_s(name: str, default_s: float | None) -> float | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default_s

    value = raw.strip().lower()
    if value in {"0", "none", "off", "false", "unlimited", "infinite"}:
        return None

    parsed = float(value)
    return parsed if parsed > 0 else None


def _format_duration(seconds: float) -> str:
    whole = max(0, int(seconds))
    minutes, secs = divmod(whole, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


async def _probe_gateway(settings: OpenClawSettings) -> dict[str, Any]:
    async with OpenClawGatewaySession(settings) as session:
        health = await session.call("health", {}, timeout=10.0)
        return {
            "reachable": True,
            "protocol": session.protocol,
            "server_version": session.server_info.get("version"),
            "conn_id": session.server_info.get("connId"),
            "default_agent_id": health.get("defaultAgentId"),
        }


async def _build_connection_snapshot() -> dict[str, Any]:
    settings = _load_openclaw_settings()
    issues: list[str] = []

    if not settings.config_exists:
        issues.append(f"未找到 OpenClaw 配置文件：{settings.config_path}")
    if settings.config_error:
        issues.append(settings.config_error)
    if not settings.workspace_exists:
        issues.append(f"Workspace 不存在：{settings.workspace_root}")
    if not settings.agent_configured:
        issues.append(f"OpenClaw agent 未配置：{settings.agent_id}")
    if settings.agent_workspace and not settings.agent_workspace_matches:
        issues.append(
            f"前端使用的 Workspace 与 agent 配置不一致：{settings.workspace_root} != {settings.agent_workspace}"
        )
    if not settings.gateway_token:
        issues.append("缺少 Gateway token，请配置 OPENCLAW_GATEWAY_TOKEN 或 OPENCLAW_HOOKS_TOKEN")

    gateway_info = {
        "http_url": settings.gateway_http_url,
        "ws_url": settings.gateway_ws_url,
        "auth_configured": bool(settings.gateway_token),
        "reachable": False,
        "protocol": None,
        "server_version": None,
        "default_agent_id": None,
    }

    if not issues:
        try:
            gateway_info.update(await _probe_gateway(settings))
        except Exception as exc:
            issues.append(str(exc))

    if gateway_info["reachable"] and not issues:
        status = "ready"
    elif settings.workspace_exists or settings.agent_configured:
        status = "degraded"
    else:
        status = "error"

    return {
        "status": status,
        "checked_at": _now_iso(),
        "workspace_root": str(settings.workspace_root),
        "workspace_exists": settings.workspace_exists,
        "workspace_source": settings.workspace_source,
        "agent": {
            "id": settings.agent_id,
            "configured": settings.agent_configured,
            "workspace": str(settings.agent_workspace) if settings.agent_workspace else None,
            "workspace_matches": settings.agent_workspace_matches,
        },
        "gateway": gateway_info,
        "hooks": {
            "enabled": settings.hooks_enabled,
            "mapping_present": settings.hook_mapping_present,
        },
        "preferred_transport": "openclaw" if status == "ready" else "subprocess",
        "issues": issues,
    }


async def _run_subprocess_collector(run: SentinelRun) -> None:
    settings = _load_openclaw_settings()
    workspace_root = settings.workspace_root
    python_bin = _build_subprocess_python(workspace_root)

    if not workspace_root.exists():
        await _finish_run(run, "failed", f"workspace not found: {workspace_root}")
        return
    if not python_bin.exists():
        await _finish_run(run, "failed", f"collector python not found: {python_bin}")
        return

    command = _COLLECTOR_COMMANDS[run.mode]
    node_name = _COLLECTOR_NODE_NAMES.get(run.mode, "sentinel")
    args = [str(python_bin), *[str(workspace_root / part) for part in command]]

    run.status = "running"
    run.add_event(
        {
            "type": "run_header",
            "run_id": run.run_id,
            "run_mode": run.mode,
            "source_runtime_mode": "subprocess",
            "llm_model": "workspace-script",
            "ts": _now_iso(),
        }
    )
    run.add_event(
        {
            "type": "node_detail",
            "node": node_name,
            "display_name": node_name,
            "message": f"启动本地采集脚本：{' '.join(command)}",
            "ts": _now_iso(),
        }
    )

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(workspace_root),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except Exception as exc:
        await _finish_run(run, "failed", f"failed to start collector: {exc}")
        return

    run.process = process

    try:
        while True:
            if run.cancel_requested and process.returncode is None:
                process.terminate()
            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=1.0)
            except asyncio.TimeoutError:
                if process.returncode is not None:
                    break
                continue
            if not line:
                if process.returncode is not None:
                    break
                continue

            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                run.add_event(
                    {
                        "type": "node_verbose",
                        "node": node_name,
                        "display_name": node_name,
                        "ts": _now_iso(),
                        "key": "stdout",
                        "value": text,
                        "truncated": False,
                    }
                )
    except asyncio.CancelledError:
        run.cancel_requested = True
        if process.returncode is None:
            process.terminate()
        raise
    finally:
        exit_code = process.returncode if process.returncode is not None else await process.wait()
        run.process = None

    if run.cancel_requested:
        await _finish_run(run, "cancelled")
    elif exit_code == 0:
        await _finish_run(run, "succeeded")
    else:
        await _finish_run(run, "failed", f"collector exited with code {exit_code}")


def _agent_event_matches(run: SentinelRun, event: dict[str, Any]) -> bool:
    if event.get("type") != "event" or event.get("event") != "agent":
        return False
    payload = event.get("payload") or {}
    return payload.get("runId") == run.gateway_run_id


def _emit_assistant_line(run: SentinelRun, text: str, ts: str) -> None:
    line = text.strip()
    if not line:
        return

    if line.startswith("[STATUS]"):
        run.add_event(
            {
                "type": "node_detail",
                "node": "openclaw",
                "display_name": "OpenClaw Agent",
                "message": line.removeprefix("[STATUS]").strip() or "OpenClaw 阶段更新",
                "ts": ts,
            }
        )
        return

    run.add_event(
        {
            "type": "node_verbose",
            "node": "openclaw",
            "display_name": "OpenClaw Agent",
            "ts": ts,
            "key": "assistant",
            "value": line,
            "truncated": False,
        }
    )


def _consume_assistant_delta(run: SentinelRun, text: str, ts: str) -> None:
    run.assistant_buffer += text
    while "\n" in run.assistant_buffer:
        line, run.assistant_buffer = run.assistant_buffer.split("\n", 1)
        _emit_assistant_line(run, line, ts)


def _summarize_tool_event(data: dict[str, Any]) -> str:
    tool_name = (
        data.get("tool")
        or data.get("toolName")
        or data.get("name")
        or data.get("id")
        or "tool"
    )
    phase = data.get("phase") or data.get("status") or data.get("event") or "update"
    detail = data.get("summary") or data.get("message") or data.get("state")
    if detail:
        return f"{tool_name}: {phase} - {detail}"
    return f"{tool_name}: {phase}"


def _translate_agent_event(run: SentinelRun, event: dict[str, Any]) -> None:
    payload = event.get("payload") or {}
    stream = payload.get("stream")
    data = payload.get("data") or {}
    ts = _ms_to_iso(payload.get("ts"))

    if stream == "lifecycle":
        phase = data.get("phase")
        if phase in {"end", "error"} and run.assistant_buffer.strip():
            _emit_assistant_line(run, run.assistant_buffer, ts)
            run.assistant_buffer = ""
        message = "OpenClaw agent 已开始执行" if phase == "start" else "OpenClaw agent 执行结束，等待最终状态确认"
        run.add_event(
            {
                "type": "node_detail",
                "node": "openclaw",
                "display_name": "OpenClaw Agent",
                "message": message,
                "ts": ts,
            }
        )
        return

    if stream == "assistant":
        full_text = data.get("text")
        if isinstance(full_text, str):
            run.assistant_text = full_text
        text = data.get("delta") or data.get("text")
        if text:
            _consume_assistant_delta(run, str(text), ts)
        return

    if stream == "tool":
        summary = _summarize_tool_event(data)
        run.add_event(
            {
                "type": "node_detail",
                "node": "openclaw_tool",
                "display_name": "OpenClaw Tool",
                "message": summary,
                "ts": ts,
            }
        )
        run.add_event(
            {
                "type": "node_verbose",
                "node": "openclaw_tool",
                "display_name": "OpenClaw Tool",
                "ts": ts,
                "key": "tool",
                "value": json.dumps(data, ensure_ascii=False),
                "truncated": False,
            }
        )
        return

    run.add_event(
        {
            "type": "node_verbose",
            "node": "openclaw",
            "display_name": "OpenClaw Agent",
            "ts": ts,
            "key": str(stream or "event"),
            "value": json.dumps(data, ensure_ascii=False),
            "truncated": False,
        }
    )


async def _run_openclaw_collector(run: SentinelRun) -> None:
    connection = await _build_connection_snapshot()
    if connection["preferred_transport"] != "openclaw":
        await _finish_run(run, "failed", "；".join(connection["issues"]) or "OpenClaw Gateway is not ready")
        return

    settings = _load_openclaw_settings()
    session_key = f"agent:{settings.agent_id}:saads-sentinel:{run.run_id}"
    agent_timeout_ms = _parse_optional_timeout_ms("OPENCLAW_AGENT_TIMEOUT_MS", 3_600_000)
    wait_timeout_ms = _parse_optional_timeout_ms(
        "OPENCLAW_WAIT_TIMEOUT_MS",
        agent_timeout_ms + 300_000 if agent_timeout_ms is not None else None,
    )
    wait_call_timeout_s = _parse_optional_timeout_s(
        "OPENCLAW_WAIT_TIMEOUT_S",
        (wait_timeout_ms / 1000.0 + 30.0) if wait_timeout_ms is not None else None,
    )
    run.session_key = session_key
    run.status = "running"
    run.add_event(
        {
            "type": "run_header",
            "run_id": run.run_id,
            "run_mode": run.mode,
            "source_runtime_mode": "openclaw",
            "llm_model": settings.agent_id,
            "ts": _now_iso(),
        }
    )
    run.add_event(
        {
            "type": "node_detail",
            "node": "openclaw",
            "display_name": "OpenClaw Gateway",
            "message": f"连接 Gateway：{settings.gateway_http_url}",
            "ts": _now_iso(),
        }
    )
    run.add_event(
        {
            "type": "node_detail",
            "node": "openclaw",
            "display_name": "OpenClaw Gateway",
            "message": (
                "Agent 超时覆盖："
                + (
                    f"{_format_duration(agent_timeout_ms / 1000)}"
                    if agent_timeout_ms is not None
                    else "关闭（使用 OpenClaw 默认配置）"
                )
                + "；等待超时："
                + (
                    f"{_format_duration(wait_timeout_ms / 1000)}"
                    if wait_timeout_ms is not None
                    else "不限制"
                )
            ),
            "ts": _now_iso(),
        }
    )

    abort_sent = False
    try:
        async with OpenClawGatewaySession(settings) as session:
            health = await session.call("health", {}, timeout=10.0)
            run.add_event(
                {
                    "type": "node_detail",
                    "node": "openclaw",
                    "display_name": "OpenClaw Gateway",
                    "message": f"Gateway 就绪，protocol={session.protocol}，defaultAgent={health.get('defaultAgentId')}",
                    "ts": _now_iso(),
                }
            )

            agent_params: dict[str, Any] = {
                "agentId": settings.agent_id,
                "sessionKey": session_key,
                "message": _build_openclaw_message(run.mode),
                "deliver": False,
                "label": f"SAADS Sentinel {run.mode}",
                "idempotencyKey": str(uuid.uuid4()),
            }
            if agent_timeout_ms is not None:
                agent_params["timeout"] = agent_timeout_ms

            agent_payload = await session.call("agent", agent_params, timeout=20.0)
            run.gateway_run_id = str(agent_payload.get("runId"))
            run.add_event(
                {
                    "type": "node_detail",
                    "node": "openclaw",
                    "display_name": "OpenClaw Gateway",
                    "message": f"已提交 agent run：{run.gateway_run_id}",
                    "ts": _now_iso(),
                }
            )

            wait_params: dict[str, Any] = {"runId": run.gateway_run_id}
            if wait_timeout_ms is not None:
                wait_params["timeoutMs"] = wait_timeout_ms

            wait_task = asyncio.create_task(
                session.call("agent.wait", wait_params, timeout=wait_call_timeout_s)
            )

            final_payload: dict[str, Any] | None = None
            loop_started_at = asyncio.get_running_loop().time()
            next_progress_ping = loop_started_at + 30.0
            while final_payload is None:
                if wait_task.done():
                    final_payload = await wait_task
                    break

                if run.cancel_requested and not abort_sent and run.gateway_run_id:
                    abort_sent = True
                    try:
                        await session.call(
                            "chat.abort",
                            {"sessionKey": session_key, "runId": run.gateway_run_id},
                            timeout=10.0,
                        )
                        run.add_event(
                            {
                                "type": "node_detail",
                                "node": "openclaw",
                                "display_name": "OpenClaw Gateway",
                                "message": "已向 OpenClaw 发送取消请求",
                                "ts": _now_iso(),
                            }
                        )
                    except Exception as exc:
                        run.add_event(
                            {
                                "type": "node_error_detail",
                                "node": "openclaw",
                                "display_name": "OpenClaw Gateway",
                                "message": f"取消请求失败：{exc}",
                                "ts": _now_iso(),
                            }
                        )

                try:
                    event = await session.next_event(timeout=1.0)
                except asyncio.TimeoutError:
                    now = asyncio.get_running_loop().time()
                    if now >= next_progress_ping:
                        run.add_event(
                            {
                                "type": "node_detail",
                                "node": "openclaw",
                                "display_name": "OpenClaw Agent",
                                "message": f"仍在执行，已运行 {_format_duration(now - loop_started_at)}，等待下一条进度或结果",
                                "ts": _now_iso(),
                            }
                        )
                        next_progress_ping = now + 30.0
                    continue

                if event.get("event") == "_connection_closed" and final_payload is None:
                    raise OpenClawGatewayError("gateway connection closed before run finished")
                if _agent_event_matches(run, event):
                    _translate_agent_event(run, event)
                    next_progress_ping = asyncio.get_running_loop().time() + 30.0

            status = str(final_payload.get("status") or "").lower() if final_payload else ""
            if run.cancel_requested or status in {"aborted", "cancelled", "canceled"}:
                await _finish_run(run, "cancelled")
            elif status == "ok":
                await _finish_run(run, "succeeded")
            else:
                await _finish_run(run, "failed", f"OpenClaw agent ended with status: {status or 'unknown'}")
    except asyncio.CancelledError:
        run.cancel_requested = True
        raise
    except Exception as exc:
        await _finish_run(run, "failed", str(exc))


class SentinelRunRequest(BaseModel):
    mode: str = "full"
    transport: str | None = None
    use_gateway: bool | None = None


@router.get("/connection")
async def get_connection() -> dict[str, Any]:
    return await _build_connection_snapshot()


@router.get("/status")
async def get_status() -> dict[str, Any]:
    settings = _load_openclaw_settings()
    active = _get_active_run()
    latest = _get_latest_run()

    daily_path = _latest_daily_file(settings.workspace_root)
    daily = _read_daily_intel(daily_path) if daily_path else {}
    snapshot = _read_coverage_snapshot(settings.workspace_root)

    if active and active.status not in _TERMINAL_STATUSES:
        status = "running"
    elif latest and latest.status == "failed":
        status = "warning"
    else:
        status = "idle"

    current_tasks: list[str] = []
    if active and active.status not in _TERMINAL_STATUSES:
        transport_label = "OpenClaw" if active.transport == "openclaw" else "subprocess"
        current_tasks.append(f"{active.mode} collector running via {transport_label}")

    uptime_seconds = 0
    if active:
        try:
            started = datetime.fromisoformat(_ensure_offset(active.started_at))
            uptime_seconds = max(0, int((_now() - started).total_seconds()))
        except ValueError:
            uptime_seconds = 0

    return {
        "wp_id": "sentinel",
        "status": status,
        "uptime_seconds": uptime_seconds,
        "version": "v2.0.0",
        "metrics": {
            "intel_count": _intel_count(daily),
            "owasp_coverage": _owasp_coverage_pct(snapshot),
            "high_risk_count": _high_risk_count(daily),
        },
        "current_tasks": current_tasks,
        "last_updated": _now_iso(),
    }


@router.get("/metrics")
async def get_metrics(
    keys: str = "intel_count,owasp_coverage,high_risk_count",
    window: str = "48h",
) -> list[dict[str, Any]]:
    settings = _load_openclaw_settings()
    key_list = [key.strip() for key in keys.split(",") if key.strip()]
    if not key_list:
        return []

    all_files = sorted((settings.workspace_root / "kb" / "daily").glob("ai-threat-*.json"))
    if not all_files:
        return [{"key": key, "unit": "", "points": []} for key in key_list]

    cutoff = _now() - timedelta(hours=_parse_window_hours(window))
    series: dict[str, list[dict[str, Any]]] = {key: [] for key in key_list}
    snapshot = _read_coverage_snapshot(settings.workspace_root)

    for file_path in all_files:
        daily = _read_daily_intel(file_path)
        if not daily:
            continue
        point_ts = _ensure_offset(str(daily.get("report_date") or _now_iso()))
        try:
            if datetime.fromisoformat(point_ts) < cutoff:
                continue
        except ValueError:
            pass

        values = {
            "intel_count": float(_intel_count(daily)),
            "owasp_coverage": float(_owasp_coverage_pct(snapshot)),
            "high_risk_count": float(_high_risk_count(daily)),
        }
        for key in key_list:
            if key in values:
                series[key].append({"timestamp": point_ts, "value": values[key]})

    units = {"intel_count": "items", "owasp_coverage": "%", "high_risk_count": "items"}
    return [{"key": key, "unit": units.get(key, ""), "points": series.get(key, [])} for key in key_list]


@router.get("/alerts")
async def get_alerts(limit: int = 10) -> list[dict[str, Any]]:
    settings = _load_openclaw_settings()
    daily_path = _latest_daily_file(settings.workspace_root)
    if not daily_path:
        return []

    daily = _read_daily_intel(daily_path)
    alerts: list[dict[str, Any]] = []
    for item in daily.get("top5", [])[:limit]:
        score = float(item.get("cvss_score") or 0.0)
        if score < 7.0:
            continue
        desc = str(item.get("description") or "")
        alerts.append(
            {
                "id": f"sentinel-{item.get('external_id', uuid.uuid4().hex[:8])}",
                "severity": "HIGH" if score >= 9.0 else "MEDIUM",
                "title": f"[{item.get('external_id', '?')}] {desc[:120]}{'...' if len(desc) > 120 else ''}",
                "cvss": score,
                "created_at": _ensure_offset(str(item.get("published_at") or _now_iso())),
            }
        )
    return alerts


@router.get("/reports")
async def list_reports() -> list[dict[str, str]]:
    settings = _load_openclaw_settings()
    date_re = re.compile(r"\d{4}-\d{2}-\d{2}")
    files = [
        file_path
        for file_path in (settings.workspace_root / "reports").rglob("*.md")
        if file_path.is_file() and date_re.search(file_path.name)
    ]
    files.sort(key=lambda item: item.name, reverse=True)
    return [
        {
            "date": date_re.search(file_path.name).group(0) if date_re.search(file_path.name) else "",
            "filename": file_path.name,
        }
        for file_path in files
    ]


@router.get("/reports/{date}")
async def get_report(date: str) -> dict[str, str]:
    settings = _load_openclaw_settings()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    for file_path in (settings.workspace_root / "reports").rglob("*.md"):
        if file_path.is_file() and date in file_path.name:
            return {
                "date": date,
                "content": file_path.read_text(encoding="utf-8", errors="replace"),
            }

    raise HTTPException(status_code=404, detail=f"report not found for {date}")


@router.post("/runs", status_code=201)
async def start_run(body: SentinelRunRequest) -> dict[str, Any]:
    if body.mode not in _COLLECTOR_COMMANDS:
        raise HTTPException(status_code=400, detail=f"unknown mode: {body.mode}")

    transport = body.transport
    if transport is None:
        transport = "openclaw" if body.use_gateway else "subprocess"
    if transport not in {"subprocess", "openclaw"}:
        raise HTTPException(status_code=400, detail=f"unknown transport: {transport}")

    if transport == "openclaw":
        connection = await _build_connection_snapshot()
        if connection["preferred_transport"] != "openclaw":
            raise HTTPException(
                status_code=503,
                detail="；".join(connection["issues"]) or "OpenClaw Gateway is not ready",
            )

    run = await _register_run(body.mode, transport)
    run.add_event(
        {
            "type": "init",
            "run_id": run.run_id,
            "run_mode": run.mode,
            "ts": run.started_at,
        }
    )
    run.task = asyncio.create_task(
        _run_openclaw_collector(run) if transport == "openclaw" else _run_subprocess_collector(run)
    )
    return _run_summary(run)


@router.get("/runs/active")
async def get_active_run_endpoint() -> dict[str, Any]:
    active = _get_active_run()
    if active is None or active.status in _TERMINAL_STATUSES:
        raise HTTPException(status_code=404, detail="no active run")
    return _run_summary(active)


@router.get("/runs/{run_id}")
async def get_run_endpoint(run_id: str) -> dict[str, Any]:
    run = _get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    return _run_summary(run)


@router.delete("/runs/{run_id}")
async def cancel_run(run_id: str) -> dict[str, Any]:
    run = _get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    if run.status in _TERMINAL_STATUSES:
        return _run_summary(run)

    run.cancel_requested = True
    run.status = "cancelling"
    if run.process is not None and run.process.returncode is None:
        with contextlib.suppress(ProcessLookupError):
            run.process.terminate()

    run.add_event(
        {
            "type": "node_detail",
            "node": "sentinel",
            "display_name": "Sentinel",
            "message": "收到取消请求",
            "ts": _now_iso(),
        }
    )
    return _run_summary(run)


def _sse_frame(index: int, payload: dict[str, Any]) -> str:
    return f"id: {index}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.get("/logs/stream")
async def stream_logs(
    last_event_index: int = Query(default=0, ge=0),
) -> StreamingResponse:
    async def event_generator():
        cursor = last_event_index
        source_run_id: str | None = None
        replayed_memory = False
        heartbeat_at = asyncio.get_running_loop().time()

        while True:
            source = _get_active_run() or _get_latest_run()
            if source is not None:
                if source_run_id != source.run_id:
                    source_run_id = source.run_id
                    if cursor > source.event_index:
                        cursor = 0
                    replayed_memory = True

                pending = [event for event in source.history if event.index > cursor]
                if pending:
                    for event in pending:
                        cursor = event.index
                        yield _sse_frame(event.index, event.payload)
                    source.updated.clear()
                    heartbeat_at = asyncio.get_running_loop().time()
                    continue

                source.updated.clear()
                await asyncio.sleep(1.0)
            else:
                if not replayed_memory and cursor == 0:
                    settings = _load_openclaw_settings()
                    memory_file = _latest_memory_file(settings.workspace_root)
                    if memory_file is not None:
                        next_index = 1
                        for line in memory_file.read_text(encoding="utf-8", errors="replace").splitlines():
                            if not line.strip():
                                continue
                            yield _sse_frame(
                                next_index,
                                {
                                    "type": "node_verbose",
                                    "node": "sentinel_memory",
                                    "display_name": "历史日志",
                                    "ts": _now_iso(),
                                    "key": "memory",
                                    "value": line,
                                    "truncated": False,
                                },
                            )
                            cursor = next_index
                            next_index += 1
                        yield _sse_frame(next_index, {"type": "done", "status": "succeeded", "percent": 100})
                        cursor = next_index
                    replayed_memory = True
                    heartbeat_at = asyncio.get_running_loop().time()
                    continue
                await asyncio.sleep(1.0)

            if asyncio.get_running_loop().time() - heartbeat_at >= 30:
                yield _sse_frame(cursor + 1, {"type": "heartbeat"})
                heartbeat_at = asyncio.get_running_loop().time()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
