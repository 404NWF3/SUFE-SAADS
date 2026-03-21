"""server.py — FastAPI 应用入口（WP1-1 后端服务）"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.agents.intel_agents.orchestrator.runtime import Phase1GraphRuntime
from backend.api.run_store import RunStore
from backend.api.routers import wp11


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """启动时初始化共享资源；关闭时清理。"""
    app.state.wp11_runtime = Phase1GraphRuntime()
    app.state.run_store = RunStore()
    yield
    # 取消所有未完成的运行任务
    store: RunStore = app.state.run_store
    for record in store._runs.values():
        if record.task and not record.task.done():
            record.task.cancel()


app = FastAPI(
    title="SUFE-SAADS WP1-1 API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wp11.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
