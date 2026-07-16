"""证据材料接口测试（mock OCR / 抽取 / MinIO）。"""
from __future__ import annotations

import asyncio

from httpx import AsyncClient


async def _upload(client: AsyncClient, headers: dict, filename="借条.png", category="书证", case_id=None):
    data = {"category": category}
    if case_id is not None:
        data["case_id"] = str(case_id)
    resp = await client.post(
        "/api/evidence",
        files={"file": (filename, b"fake-image-bytes", "image/png")},
        data=data,
        headers=headers,
    )
    await asyncio.sleep(0.1)  # 等待后台任务
    return resp


async def test_evidence_requires_auth(client: AsyncClient):
    assert (await client.get("/api/evidence")).status_code == 401


async def test_evidence_categories(client: AsyncClient, auth_headers):
    cats = (await client.get("/api/evidence/categories", headers=auth_headers)).json()
    assert "书证" in cats and "电子数据" in cats


async def test_upload_ocr_extract_flow(client: AsyncClient, auth_headers, mock_evidence_stack):
    resp = await _upload(client, auth_headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["ocr_status"] == "pending"

    lst = (await client.get("/api/evidence", headers=auth_headers)).json()
    ev = lst[0]
    assert ev["ocr_status"] == "done", ev
    assert "张三" in ev["extracted"]["parties"]
    assert ev["extracted"]["amounts"] == ["人民币50000元"]
    assert ev["ocr_text"]  # OCR 全文已保存
    assert ev["name"]  # 未填名称时用摘要回填


async def test_upload_unsupported_type(client: AsyncClient, auth_headers, mock_evidence_stack):
    resp = await client.post(
        "/api/evidence",
        files={"file": ("视频.mp4", b"x", "video/mp4")},
        data={"category": "视听资料"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "不支持" in resp.json()["detail"]


async def test_update_and_delete_evidence(client: AsyncClient, auth_headers, mock_evidence_stack):
    await _upload(client, auth_headers)
    ev = (await client.get("/api/evidence", headers=auth_headers)).json()[0]

    # 修正分类与抽取结果
    upd = await client.put(
        f"/api/evidence/{ev['id']}",
        json={"category": "电子数据", "extracted": {"parties": ["修正人"], "amounts": [], "dates": [], "summary": "修正"}},
        headers=auth_headers,
    )
    assert upd.status_code == 200
    assert upd.json()["category"] == "电子数据"
    assert upd.json()["extracted"]["parties"] == ["修正人"]

    # 删除（同步移除 MinIO 原件）
    resp = await client.delete(f"/api/evidence/{ev['id']}", headers=auth_headers)
    assert resp.status_code == 204
    assert mock_evidence_stack["removed"]


async def test_evidence_filter_by_case(client: AsyncClient, auth_headers, mock_evidence_stack):
    case = (await client.post("/api/cases", json={"title": "案A"}, headers=auth_headers)).json()
    await _upload(client, auth_headers, filename="关联.png", case_id=case["id"])
    await _upload(client, auth_headers, filename="独立.png")

    linked = (await client.get(f"/api/evidence?case_id={case['id']}", headers=auth_headers)).json()
    assert len(linked) == 1
    assert linked[0]["case_id"] == case["id"]
    all_ev = (await client.get("/api/evidence", headers=auth_headers)).json()
    assert len(all_ev) == 2


async def test_ocr_failure_marks_failed(client: AsyncClient, auth_headers, monkeypatch):
    async def fake_save_file(prefix, filename, data, content_type="application/octet-stream"):
        return "evidence/x"

    async def broken_recognize(filename, data):
        raise RuntimeError("OCR 引擎异常")

    monkeypatch.setattr("backend.app.services.storage.save_file", fake_save_file)
    monkeypatch.setattr("backend.app.services.ocr.recognize", broken_recognize)

    await _upload(client, auth_headers)
    ev = (await client.get("/api/evidence", headers=auth_headers)).json()[0]
    assert ev["ocr_status"] == "failed"
    assert "OCR 引擎异常" in ev["error_msg"]
