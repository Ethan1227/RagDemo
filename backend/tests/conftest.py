"""pytest 公共夹具。

使用内存 SQLite（StaticPool 保持单连接，保证内存库在多次会话间不丢失）替代 MySQL，
并覆盖 get_db 依赖，使认证接口测试无需真实数据库/基础设施即可运行。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401  确保模型注册到 Base.metadata
from backend.app.db.session import Base, get_db
from backend.app.main import app


@pytest_asyncio.fixture
async def db_session_maker() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest_asyncio.fixture
async def client(
    db_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with db_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def pass_captcha(monkeypatch: pytest.MonkeyPatch) -> None:
    """让验证码校验恒为通过，聚焦测试其它认证逻辑。"""
    monkeypatch.setattr("backend.app.api.auth.verify_captcha", lambda cid, code: True)


@pytest.fixture
def fail_captcha(monkeypatch: pytest.MonkeyPatch) -> None:
    """让验证码校验恒为失败，测试验证码错误分支。"""
    monkeypatch.setattr("backend.app.api.auth.verify_captcha", lambda cid, code: False)
