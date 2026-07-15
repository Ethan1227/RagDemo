"""法律咨询对话接口测试：会话 CRUD 与 SSE 流式问答（mock 检索与 LLM）。"""
from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

from backend.app.services.prompts import DISCLAIMER

FAKE_CONTEXT = {
    "chunk_id": 1,
    "content": "向人民法院请求保护民事权利的诉讼时效期间为三年。",
    "score": 0.95,
    "document_id": 1,
    "filename": "民法典.txt",
    "kb_id": 1,
    "kb_name": "法律法规库",
}


def _parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.split("\n\n"):
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


@pytest.fixture
def mock_rag(monkeypatch: pytest.MonkeyPatch):
    """mock 检索与 LLM 流式输出。"""

    async def fake_retrieve(db, query, kb_ids, top_k):
        return [FAKE_CONTEXT] if kb_ids else []

    async def fake_stream_chat(messages, model, temperature, top_p, max_tokens):
        yield "根据《中华人民共和国民法典》第一百八十八条 [1]，"
        yield "诉讼时效期间为三年。"

    monkeypatch.setattr("backend.app.services.retriever.retrieve", fake_retrieve)
    monkeypatch.setattr("backend.app.services.llm.stream_chat", fake_stream_chat)


async def _create_session(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post(
        "/api/chat/sessions", json={"name": "咨询诉讼时效"}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_session_crud(client: AsyncClient, auth_headers):
    session = await _create_session(client, auth_headers)
    assert session["name"] == "咨询诉讼时效"
    assert session["history_rounds"] == 5  # 默认历史轮数
    assert session["model"] == "qwen-max"

    # 重命名 + 调整参数
    resp = await client.put(
        f"/api/chat/sessions/{session['id']}",
        json={"name": "改名了", "temperature": 0.3, "history_rounds": 3, "kb_ids": [1, 2]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "改名了"
    assert body["temperature"] == 0.3
    assert body["kb_ids"] == [1, 2]

    # 列表
    sessions = (await client.get("/api/chat/sessions", headers=auth_headers)).json()
    assert len(sessions) == 1

    # 删除
    resp = await client.delete(
        f"/api/chat/sessions/{session['id']}", headers=auth_headers
    )
    assert resp.status_code == 204
    sessions = (await client.get("/api/chat/sessions", headers=auth_headers)).json()
    assert sessions == []


async def test_session_requires_auth(client: AsyncClient):
    resp = await client.get("/api/chat/sessions")
    assert resp.status_code == 401


async def test_stream_chat_full_flow(client: AsyncClient, auth_headers, mock_rag):
    session = await _create_session(client, auth_headers)
    await client.put(
        f"/api/chat/sessions/{session['id']}", json={"kb_ids": [1]}, headers=auth_headers
    )

    resp = await client.post(
        f"/api/chat/sessions/{session['id']}/stream",
        json={"question": "诉讼时效是多久？"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    types = [e["type"] for e in events]
    # 顺序：citations -> 若干 delta -> done
    assert types[0] == "citations"
    assert "delta" in types
    assert types[-1] == "done"

    # 引用包含来源信息
    citations = events[0]["citations"]
    assert citations[0]["filename"] == "民法典.txt"
    assert citations[0]["kb_name"] == "法律法规库"

    # 拼接回答：包含法条引用与免责声明
    answer = "".join(e["content"] for e in events if e["type"] == "delta")
    assert "第一百八十八条" in answer
    assert DISCLAIMER in answer

    # 历史落库：user + assistant，assistant 带引用与免责声明
    messages = (
        await client.get(
            f"/api/chat/sessions/{session['id']}/messages", headers=auth_headers
        )
    ).json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert DISCLAIMER in messages[1]["content"]
    assert messages[1]["citations"][0]["kb_name"] == "法律法规库"


async def test_stream_chat_no_kb_selected(client: AsyncClient, auth_headers, mock_rag):
    """未选知识库时也能回答（无引用），免责声明仍在。"""
    session = await _create_session(client, auth_headers)
    resp = await client.post(
        f"/api/chat/sessions/{session['id']}/stream",
        json={"question": "起诉需要什么材料？"},
        headers=auth_headers,
    )
    events = _parse_sse(resp.text)
    assert events[0] == {"type": "citations", "citations": []}
    answer = "".join(e["content"] for e in events if e["type"] == "delta")
    assert DISCLAIMER in answer


async def test_stream_chat_llm_error_emits_error_event(
    client: AsyncClient, auth_headers, monkeypatch
):
    async def fake_retrieve(db, query, kb_ids, top_k):
        return []

    async def broken_stream(messages, model, temperature, top_p, max_tokens):
        raise RuntimeError("API Key 无效")
        yield  # pragma: no cover

    monkeypatch.setattr("backend.app.services.retriever.retrieve", fake_retrieve)
    monkeypatch.setattr("backend.app.services.llm.stream_chat", broken_stream)

    session = await _create_session(client, auth_headers)
    resp = await client.post(
        f"/api/chat/sessions/{session['id']}/stream",
        json={"question": "问题"},
        headers=auth_headers,
    )
    events = _parse_sse(resp.text)
    assert events[-1]["type"] == "error"
    assert "回答生成失败" in events[-1]["detail"]


async def test_stream_other_users_session_404(client: AsyncClient, auth_headers, pass_captcha):
    session = await _create_session(client, auth_headers)
    # 另一个用户
    await client.post(
        "/api/auth/register",
        json={
            "username": "other",
            "password": "secret123",
            "confirm_password": "secret123",
            "captcha_id": "x",
            "captcha_code": "y",
        },
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": "other", "password": "secret123", "captcha_id": "x", "captcha_code": "y"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = await client.post(
        f"/api/chat/sessions/{session['id']}/stream",
        json={"question": "偷看"},
        headers=other_headers,
    )
    assert resp.status_code == 404
