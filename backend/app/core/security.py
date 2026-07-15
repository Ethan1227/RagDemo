"""认证安全工具：密码哈希（bcrypt）与 JWT 生成/校验。

直接使用 bcrypt 库（规避 passlib 与新版 bcrypt 的兼容问题）。
bcrypt 对超过 72 字节的密码会截断，这里显式截断以保证行为确定。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from backend.app.core.config import get_settings

_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    """将密码编码为 bytes 并截断到 bcrypt 支持的最大长度。"""
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """生成 bcrypt 密码哈希。"""
    return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """生成 JWT 访问令牌，subject 通常为用户名或用户 ID。"""
    settings = get_settings()
    minutes = expires_minutes or settings.app.jwt_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(
        payload, settings.app.secret_key, algorithm=settings.app.jwt_algorithm
    )


def decode_access_token(token: str) -> str | None:
    """校验并解析 JWT，返回 subject；无效返回 None。"""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.app.secret_key, algorithms=[settings.app.jwt_algorithm]
        )
    except JWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
