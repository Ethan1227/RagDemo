"""FastAPI 应用入口。

负责：初始化日志与数据库、配置 CORS、挂载路由、提供健康检查。
启动：uv run uvicorn backend.app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.app.api import auth, case, chat, complaint, evidence, kb
from backend.app.core.config import get_settings
from backend.app.core.logging import setup_logging
from backend.app.db.session import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("应用启动中……")
    try:
        await init_db()
        logger.info("数据库表初始化完成")
    except Exception as exc:  # 显式失败：明确提示操作者启动基础设施
        logger.error("数据库初始化失败，请确认 MySQL 已启动（docker compose up -d）：{}", exc)
        raise
    yield
    logger.info("应用已关闭")


app = FastAPI(
    title="民事纠纷诉状生成与咨询 RAG 系统",
    description="基于法律知识库的民事纠纷诉状生成与法律咨询后端服务",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(kb.router)
app.include_router(chat.router)
app.include_router(case.router)
app.include_router(evidence.router)
app.include_router(complaint.router)


@app.get("/health", tags=["系统"], summary="健康检查")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "legal-rag-backend"}
