"""案件信息接口测试。"""
from __future__ import annotations

from httpx import AsyncClient


async def _create_case(client: AsyncClient, headers: dict, title: str = "借款纠纷案") -> dict:
    resp = await client.post("/api/cases", json={"title": title}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_cases_require_auth(client: AsyncClient):
    assert (await client.get("/api/cases")).status_code == 401


async def test_case_causes_and_law_recommend(client: AsyncClient, auth_headers):
    causes = (await client.get("/api/cases/causes", headers=auth_headers)).json()
    assert "民间借贷纠纷" in causes

    rec = (
        await client.get(
            "/api/cases/law-recommend", params={"cause": "民间借贷纠纷"}, headers=auth_headers
        )
    ).json()
    assert rec["cause"] == "民间借贷纠纷"
    assert len(rec["items"]) > 0
    assert rec["items"][0]["law"].startswith("中华人民共和国")
    assert "第" in rec["items"][0]["article"]


async def test_law_recommend_unknown_cause_empty(client: AsyncClient, auth_headers):
    rec = (
        await client.get(
            "/api/cases/law-recommend", params={"cause": "未知纠纷"}, headers=auth_headers
        )
    ).json()
    assert rec["items"] == []


async def test_case_create_and_stepwise_save(client: AsyncClient, auth_headers):
    case = await _create_case(client, auth_headers)
    assert case["status"] == "draft"
    cid = case["id"]

    # 第 1 步：当事人
    r1 = await client.put(
        f"/api/cases/{cid}",
        json={
            "current_step": 1,
            "plaintiffs": [{"name": "张三", "id_card": "110101", "address": "北京", "phone": "138"}],
            "defendants": [{"name": "李四"}],
        },
        headers=auth_headers,
    )
    assert r1.status_code == 200
    body = r1.json()
    assert body["plaintiffs"][0]["name"] == "张三"
    assert body["defendants"][0]["name"] == "李四"

    # 第 2 步：案由与诉讼请求（部分更新，不影响已存字段）
    r2 = await client.put(
        f"/api/cases/{cid}",
        json={"current_step": 2, "cause": "民间借贷纠纷", "claims": "判令被告偿还借款5万元"},
        headers=auth_headers,
    )
    assert r2.json()["cause"] == "民间借贷纠纷"
    assert r2.json()["plaintiffs"][0]["name"] == "张三"  # 上一步数据仍在

    # 完成
    r3 = await client.put(
        f"/api/cases/{cid}",
        json={"status": "complete", "facts": "2024年借款", "court": "北京朝阳区法院"},
        headers=auth_headers,
    )
    assert r3.json()["status"] == "complete"


async def test_case_list_and_delete(client: AsyncClient, auth_headers):
    case = await _create_case(client, auth_headers)
    cases = (await client.get("/api/cases", headers=auth_headers)).json()
    assert len(cases) == 1

    resp = await client.delete(f"/api/cases/{case['id']}", headers=auth_headers)
    assert resp.status_code == 204
    assert (await client.get("/api/cases", headers=auth_headers)).json() == []


async def test_case_other_user_404(client: AsyncClient, auth_headers, pass_captcha):
    case = await _create_case(client, auth_headers)
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
    assert (await client.get(f"/api/cases/{case['id']}", headers=other)).status_code == 404
