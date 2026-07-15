"""认证功能测试：验证码、注册、登录、当前用户。"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.app.core import captcha as captcha_mod
from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# ---------------- 验证码核心逻辑（白盒单元测试） ----------------

def test_password_hash_roundtrip():
    h = hash_password("MyStr0ng!")
    assert h != "MyStr0ng!"
    assert verify_password("MyStr0ng!", h) is True
    assert verify_password("wrong", h) is False


def test_jwt_roundtrip():
    token = create_access_token("bob")
    assert decode_access_token(token) == "bob"
    assert decode_access_token("invalid.token.value") is None


def test_captcha_generate_and_verify_once():
    captcha_id, image = captcha_mod.generate_captcha()
    assert image.startswith("data:image/png;base64,")
    # 从内存存储取出真实验证码（测试白盒）
    code = captcha_mod._store._data[captcha_id][0]
    # 一次性：首次校验成功，二次即失效
    assert captcha_mod.verify_captcha(captcha_id, code.lower()) is True
    assert captcha_mod.verify_captcha(captcha_id, code) is False


def test_captcha_wrong_code():
    captcha_id, _ = captcha_mod.generate_captcha()
    assert captcha_mod.verify_captcha(captcha_id, "0000") is False


# ---------------- 接口测试 ----------------

async def test_captcha_endpoint(client: AsyncClient):
    resp = await client.get("/api/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    assert "captcha_id" in data and data["captcha_id"]
    assert data["image"].startswith("data:image/png;base64,")


async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_register_success(client: AsyncClient, pass_captcha):
    resp = await client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "secret123",
            "confirm_password": "secret123",
            "captcha_id": "x",
            "captcha_code": "y",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["username"] == "alice"
    assert "id" in body


async def test_register_password_mismatch(client: AsyncClient, pass_captcha):
    resp = await client.post(
        "/api/auth/register",
        json={
            "username": "carol",
            "password": "secret123",
            "confirm_password": "different",
            "captcha_id": "x",
            "captcha_code": "y",
        },
    )
    # schema 层 model_validator 触发 422
    assert resp.status_code == 422
    assert "密码不一致" in resp.text


async def test_register_wrong_captcha(client: AsyncClient, fail_captcha):
    resp = await client.post(
        "/api/auth/register",
        json={
            "username": "dave",
            "password": "secret123",
            "confirm_password": "secret123",
            "captcha_id": "x",
            "captcha_code": "bad",
        },
    )
    assert resp.status_code == 400
    assert "验证码" in resp.text


async def test_register_duplicate(client: AsyncClient, pass_captcha):
    payload = {
        "username": "eve",
        "password": "secret123",
        "confirm_password": "secret123",
        "captcha_id": "x",
        "captcha_code": "y",
    }
    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/auth/register", json=payload)
    assert second.status_code == 409
    assert "已被注册" in second.text


async def test_login_success_and_me(client: AsyncClient, pass_captcha):
    reg = await client.post(
        "/api/auth/register",
        json={
            "username": "frank",
            "password": "secret123",
            "confirm_password": "secret123",
            "captcha_id": "x",
            "captcha_code": "y",
        },
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/auth/login",
        json={
            "username": "frank",
            "password": "secret123",
            "captcha_id": "x",
            "captcha_code": "y",
        },
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    assert token

    me = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "frank"


async def test_login_wrong_password(client: AsyncClient, pass_captcha):
    await client.post(
        "/api/auth/register",
        json={
            "username": "grace",
            "password": "secret123",
            "confirm_password": "secret123",
            "captcha_id": "x",
            "captcha_code": "y",
        },
    )
    login = await client.post(
        "/api/auth/login",
        json={
            "username": "grace",
            "password": "WRONGpass",
            "captcha_id": "x",
            "captcha_code": "y",
        },
    )
    assert login.status_code == 401


async def test_me_without_token(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
