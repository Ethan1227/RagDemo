"""起诉状接口测试（mock 检索与 LLM 流式）。"""
from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from docx import Document
import io


def _parse_sse(text: str) -> list[dict]:
    events = []
    for part in text.split("\n\n"):
        part = part.strip()
        if part.startswith("data: "):
            events.append(json.loads(part[6:]))
    return events


@pytest.fixture
def mock_gen(monkeypatch: pytest.MonkeyPatch):
    async def fake_stream_chat(messages, model, temperature, top_p, max_tokens):
        yield "民事起诉状\n\n"
        yield "原告：张三\n被告：李四\n\n"
        yield "诉讼请求：判令被告偿还借款本金50000元。\n\n"
        yield "此致\n北京市朝阳区人民法院"

    monkeypatch.setattr("backend.app.services.llm.stream_chat", fake_stream_chat)


async def _prepare_case(client: AsyncClient, headers: dict) -> int:
    case = (await client.post("/api/cases", json={"title": "借款案"}, headers=headers)).json()
    await client.put(
        f"/api/cases/{case['id']}",
        json={
            "cause": "民间借贷纠纷",
            "plaintiffs": [{"name": "张三", "id_card": "110", "address": "北京", "phone": "138"}],
            "defendants": [{"name": "李四"}],
            "claims": "判令被告偿还借款5万元",
            "facts": "2024年1月借款",
            "court": "北京市朝阳区人民法院",
        },
        headers=headers,
    )
    return case["id"]


async def test_generate_stream_and_persist(client: AsyncClient, auth_headers, mock_gen):
    case_id = await _prepare_case(client, auth_headers)
    resp = await client.post(
        "/api/complaints/generate/stream",
        json={"case_id": case_id, "kb_ids": []},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    types = [e["type"] for e in events]
    assert types[0] == "laws"  # 先推送推荐法条
    assert events[0]["laws"], "民间借贷应有推荐法条"
    assert "delta" in types
    assert types[-1] == "done"

    content = "".join(e["content"] for e in events if e["type"] == "delta")
    assert "民事起诉状" in content
    assert "张三" in content and "李四" in content

    # 落库草稿
    cid = events[-1]["complaint_id"]
    detail = (await client.get(f"/api/complaints/{cid}", headers=auth_headers)).json()
    assert detail["cause"] == "民间借贷纠纷"
    assert "诉讼请求" in detail["content"]


async def test_edit_and_export_docx(client: AsyncClient, auth_headers, mock_gen):
    case_id = await _prepare_case(client, auth_headers)
    resp = await client.post(
        "/api/complaints/generate/stream", json={"case_id": case_id}, headers=auth_headers
    )
    cid = _parse_sse(resp.text)[-1]["complaint_id"]

    # 在线编辑
    edited = "# 民事起诉状\n\n诉讼请求：判令被告偿还借款本金50000元及利息。\n\n此致\n北京市朝阳区人民法院"
    upd = await client.put(
        f"/api/complaints/{cid}", json={"content": edited}, headers=auth_headers
    )
    assert upd.status_code == 200
    assert "利息" in upd.json()["content"]

    # 导出 Word 并回读校验
    export = await client.get(f"/api/complaints/{cid}/export/docx", headers=auth_headers)
    assert export.status_code == 200
    assert "wordprocessingml" in export.headers["content-type"]
    doc = Document(io.BytesIO(export.content))
    texts = "\n".join(p.text for p in doc.paragraphs)
    assert "民事起诉状" in texts
    assert "偿还借款本金50000元" in texts


async def test_generate_other_user_case_404(client: AsyncClient, auth_headers, pass_captcha, mock_gen):
    case_id = await _prepare_case(client, auth_headers)
    await client.post(
        "/api/auth/register",
        json={"username": "other", "password": "secret123", "confirm_password": "secret123",
              "captcha_id": "x", "captcha_code": "y"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": "other", "password": "secret123", "captcha_id": "x", "captcha_code": "y"},
    )
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = await client.post(
        "/api/complaints/generate/stream", json={"case_id": case_id}, headers=other
    )
    assert resp.status_code == 404


async def test_complaint_list_and_delete(client: AsyncClient, auth_headers, mock_gen):
    case_id = await _prepare_case(client, auth_headers)
    resp = await client.post(
        "/api/complaints/generate/stream", json={"case_id": case_id}, headers=auth_headers
    )
    cid = _parse_sse(resp.text)[-1]["complaint_id"]

    lst = (await client.get("/api/complaints", headers=auth_headers)).json()
    assert len(lst) == 1

    resp = await client.delete(f"/api/complaints/{cid}", headers=auth_headers)
    assert resp.status_code == 204
    assert (await client.get("/api/complaints", headers=auth_headers)).json() == []
