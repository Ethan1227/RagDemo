"""pytest 公共夹具。

使用内存 SQLite（StaticPool 保持单连接，保证内存库在多次会话间不丢失）替代 MySQL，
并覆盖 get_db 依赖，使接口测试无需真实数据库/基础设施即可运行。

阶段 2 补充：
- kb/chat 模块的后台任务与流式生成器直接使用 async_session_maker，
  测试中将其替换为 SQLite 会话工厂
- auth_headers 夹具提供已登录用户的请求头
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

import backend.app.api.chat as chat_module
import backend.app.api.complaint as complaint_module
import backend.app.api.evidence as evidence_module
import backend.app.api.kb as kb_module
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
    # kb/chat/evidence/complaint 的后台任务与流式生成器使用独立会话工厂，测试中一并替换
    kb_orig = kb_module.async_session_maker
    chat_orig = chat_module.async_session_maker
    evidence_orig = evidence_module.async_session_maker
    complaint_orig = complaint_module.async_session_maker
    kb_module.async_session_maker = db_session_maker
    chat_module.async_session_maker = db_session_maker
    evidence_module.async_session_maker = db_session_maker
    complaint_module.async_session_maker = db_session_maker

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    kb_module.async_session_maker = kb_orig
    chat_module.async_session_maker = chat_orig
    evidence_module.async_session_maker = evidence_orig
    complaint_module.async_session_maker = complaint_orig
    app.dependency_overrides.clear()


@pytest.fixture
def pass_captcha(monkeypatch: pytest.MonkeyPatch) -> None:
    """让验证码校验恒为通过，聚焦测试其它认证逻辑。"""
    monkeypatch.setattr("backend.app.api.auth.verify_captcha", lambda cid, code: True)


@pytest.fixture
def fail_captcha(monkeypatch: pytest.MonkeyPatch) -> None:
    """让验证码校验恒为失败，测试验证码错误分支。"""
    monkeypatch.setattr("backend.app.api.auth.verify_captcha", lambda cid, code: False)


@pytest_asyncio.fixture
async def auth_headers(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    """注册并登录一个测试用户，返回带 token 的请求头。"""
    monkeypatch.setattr("backend.app.api.auth.verify_captcha", lambda cid, code: True)
    await client.post(
        "/api/auth/register",
        json={
            "username": "tester",
            "password": "secret123",
            "confirm_password": "secret123",
            "captcha_id": "x",
            "captcha_code": "y",
        },
    )
    resp = await client.post(
        "/api/auth/login",
        json={
            "username": "tester",
            "password": "secret123",
            "captcha_id": "x",
            "captcha_code": "y",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_vector_stack(monkeypatch: pytest.MonkeyPatch) -> dict:
    """屏蔽外部依赖：MinIO / DashScope 向量化 / Milvus，记录调用以便断言。"""
    calls: dict = {"upserts": [], "deleted_docs": [], "deleted_chunks": [], "deleted_kbs": []}

    async def fake_save_file(prefix, filename, data, content_type="application/octet-stream"):
        return f"{prefix}/fake-object"

    async def fake_remove_file(object_name):
        return None

    async def fake_embed_texts(texts):
        return [[0.1] * 4 for _ in texts]

    async def fake_embed_query(text):
        return [0.1] * 4

    async def fake_upsert(rows):
        calls["upserts"].extend(rows)

    async def fake_delete_by_document(doc_id):
        calls["deleted_docs"].append(doc_id)

    async def fake_delete_by_chunk_ids(ids):
        calls["deleted_chunks"].extend(ids)

    async def fake_delete_by_kb(kb_id):
        calls["deleted_kbs"].append(kb_id)

    monkeypatch.setattr("backend.app.services.storage.save_file", fake_save_file)
    monkeypatch.setattr("backend.app.services.storage.remove_file", fake_remove_file)
    monkeypatch.setattr("backend.app.services.embedding.embed_texts", fake_embed_texts)
    monkeypatch.setattr("backend.app.services.embedding.embed_query", fake_embed_query)
    monkeypatch.setattr("backend.app.services.milvus_store.upsert_chunks", fake_upsert)
    monkeypatch.setattr(
        "backend.app.services.milvus_store.delete_by_document", fake_delete_by_document
    )
    monkeypatch.setattr(
        "backend.app.services.milvus_store.delete_by_chunk_ids", fake_delete_by_chunk_ids
    )
    monkeypatch.setattr("backend.app.services.milvus_store.delete_by_kb", fake_delete_by_kb)
    return calls


@pytest.fixture
def mock_evidence_stack(monkeypatch: pytest.MonkeyPatch) -> dict:
    """屏蔽 MinIO / PaddleOCR / qwen 抽取，模拟 OCR 与抽取结果。"""
    calls: dict = {"removed": []}

    async def fake_save_file(prefix, filename, data, content_type="application/octet-stream"):
        return f"{prefix}/fake-object"

    async def fake_remove_file(object_name):
        calls["removed"].append(object_name)

    async def fake_recognize(filename, data):
        return "借款人张三于2024年1月1日向李四借款人民币50000元，约定一年内归还。"

    async def fake_extract(text):
        return {
            "parties": ["张三", "李四"],
            "amounts": ["人民币50000元"],
            "dates": ["2024年1月1日"],
            "summary": "张三向李四借款5万元的借条",
        }

    monkeypatch.setattr("backend.app.services.storage.save_file", fake_save_file)
    monkeypatch.setattr("backend.app.services.storage.remove_file", fake_remove_file)
    monkeypatch.setattr("backend.app.services.ocr.recognize", fake_recognize)
    monkeypatch.setattr("backend.app.services.extractor.extract", fake_extract)
    return calls
