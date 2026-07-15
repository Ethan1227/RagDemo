"""数据库会话与初始化（异步 SQLAlchemy 2.0）。

提供全局 async engine、session 工厂、FastAPI 依赖 get_db、以及建表 init_db。
默认连接 config 中的 MySQL；测试可通过依赖覆盖使用 SQLite。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.app.core.config import get_settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""


_settings = get_settings()

# create_async_engine 为惰性连接：导入时不会真正连库，首次使用才建立连接
engine = create_async_engine(
    _settings.mysql.async_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供一个数据库会话，请求结束自动关闭。"""
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    """创建所有表（若不存在）。启动时调用。"""
    # 确保模型已被导入注册到 Base.metadata
    from backend.app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
