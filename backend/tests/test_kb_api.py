"""知识库管理接口测试（SQLite + mock 外部依赖）。

外部依赖（MinIO / DashScope / Milvus）由 mock_vector_stack 夹具屏蔽并记录调用，
验证真实业务行为：上传→后台解析→切块入库→向量 upsert→状态流转→块编辑/删除同步。
"""
from __future__ import annotations

import asyncio

from httpx import AsyncClient

SAMPLE_TEXT = (
    "第一百八十八条 向人民法院请求保护民事权利的诉讼时效期间为三年。"
    "法律另有规定的，依照其规定。"
    "第一百八十九条 当事人约定同一债务分期履行的，诉讼时效期间自最后一期履行期限届满之日起计算。"
) * 5


async def _create_kb(client: AsyncClient, headers: dict, name: str = "法律法规库", retrieval: str = "dense") -> dict:
    resp = await client.post(
        "/api/kb",
        json={"name": name, "description": "测试库", "retrieval_type": retrieval},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _upload_txt(client: AsyncClient, headers: dict, kb_id: int, filename: str = "民法典节选.txt") -> dict:
    resp = await client.post(
        f"/api/kb/{kb_id}/documents",
        files={"file": (filename, SAMPLE_TEXT.encode("utf-8"), "text/plain")},
        data={"chunk_size": "128", "chunk_overlap": "20"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    # BackgroundTasks 在响应后执行；让出事件循环等待其完成
    await asyncio.sleep(0.1)
    return resp.json()


async def test_kb_requires_auth(client: AsyncClient):
    resp = await client.get("/api/kb")
    assert resp.status_code == 401


async def test_kb_create_and_duplicate(client: AsyncClient, auth_headers):
    kb = await _create_kb(client, auth_headers)
    assert kb["name"] == "法律法规库"
    dup = await client.post(
        "/api/kb",
        json={"name": "法律法规库", "retrieval_type": "dense"},
        headers=auth_headers,
    )
    assert dup.status_code == 409


async def test_upload_parse_flow(client: AsyncClient, auth_headers, mock_vector_stack):
    kb = await _create_kb(client, auth_headers)
    doc = await _upload_txt(client, auth_headers, kb["id"])
    assert doc["status"] == "parsing"

    # 后台任务完成后：状态 done、块数>0、Milvus 收到 upsert
    docs = (await client.get(f"/api/kb/{kb['id']}/documents", headers=auth_headers)).json()
    assert docs[0]["status"] == "done", docs[0]
    assert docs[0]["chunk_count"] > 0
    assert len(mock_vector_stack["upserts"]) == docs[0]["chunk_count"]
    # 知识库列表统计文档数
    kbs = (await client.get("/api/kb", headers=auth_headers)).json()
    assert kbs[0]["document_count"] == 1


async def test_upload_unsupported_type(client: AsyncClient, auth_headers, mock_vector_stack):
    kb = await _create_kb(client, auth_headers, name="临时库")
    resp = await client.post(
        f"/api/kb/{kb['id']}/documents",
        files={"file": ("图片.png", b"fake", "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "阶段3" in resp.json()["detail"]


async def test_upload_invalid_overlap(client: AsyncClient, auth_headers, mock_vector_stack):
    kb = await _create_kb(client, auth_headers, name="参数库")
    resp = await client.post(
        f"/api/kb/{kb['id']}/documents",
        files={"file": ("a.txt", b"content", "text/plain")},
        data={"chunk_size": "100", "chunk_overlap": "100"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


async def test_chunk_page_edit_delete(client: AsyncClient, auth_headers, mock_vector_stack):
    kb = await _create_kb(client, auth_headers, name="块操作库")
    await _upload_txt(client, auth_headers, kb["id"])
    docs = (await client.get(f"/api/kb/{kb['id']}/documents", headers=auth_headers)).json()
    doc_id = docs[0]["id"]

    # 分页
    page = (
        await client.get(
            f"/api/kb/documents/{doc_id}/chunks?page=1&page_size=2", headers=auth_headers
        )
    ).json()
    assert page["total"] == docs[0]["chunk_count"]
    assert len(page["items"]) == 2
    chunk_id = page["items"][0]["id"]

    # 编辑：内容更新且重新向量化（upsert 次数 +1）
    before = len(mock_vector_stack["upserts"])
    resp = await client.put(
        f"/api/kb/chunks/{chunk_id}",
        json={"content": "修改后的法律条文内容"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "修改后的法律条文内容"
    assert len(mock_vector_stack["upserts"]) == before + 1

    # 删除：块消失且 Milvus 同步删除
    resp = await client.delete(f"/api/kb/chunks/{chunk_id}", headers=auth_headers)
    assert resp.status_code == 204
    assert chunk_id in mock_vector_stack["deleted_chunks"]
    page2 = (
        await client.get(
            f"/api/kb/documents/{doc_id}/chunks?page=1&page_size=100", headers=auth_headers
        )
    ).json()
    assert all(c["id"] != chunk_id for c in page2["items"])


async def test_delete_document_and_kb(client: AsyncClient, auth_headers, mock_vector_stack):
    kb = await _create_kb(client, auth_headers, name="删除流程库")
    await _upload_txt(client, auth_headers, kb["id"])
    docs = (await client.get(f"/api/kb/{kb['id']}/documents", headers=auth_headers)).json()
    doc_id = docs[0]["id"]

    resp = await client.delete(f"/api/kb/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 204
    assert doc_id in mock_vector_stack["deleted_docs"]

    resp = await client.delete(f"/api/kb/{kb['id']}", headers=auth_headers)
    assert resp.status_code == 204
    assert kb["id"] in mock_vector_stack["deleted_kbs"]
    kbs = (await client.get("/api/kb", headers=auth_headers)).json()
    assert all(k["id"] != kb["id"] for k in kbs)
