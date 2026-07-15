"""认证路由：图形验证码、注册、登录、当前用户信息。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.core.captcha import generate_captcha, verify_captcha
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import (
    CaptchaResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.get("/captcha", response_model=CaptchaResponse, summary="获取图形验证码")
async def get_captcha() -> CaptchaResponse:
    captcha_id, image = generate_captcha()
    return CaptchaResponse(captcha_id=captcha_id, image=image)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> UserOut:
    # 1) 校验验证码（一次性）
    if not verify_captcha(payload.captcha_id, payload.captcha_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期"
        )

    # 2) 账号唯一性
    exists = await db.execute(select(User).where(User.username == payload.username))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="该账号已被注册"
        )

    # 3) 落库（两次密码一致性已在 schema 校验）
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("新用户注册成功：{}", user.username)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(
    payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    if not verify_captcha(payload.captcha_id, payload.captcha_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期"
        )

    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        # 账号或密码错误不区分提示，避免账号枚举
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误"
        )

    token = create_access_token(subject=user.username)
    logger.info("用户登录成功：{}", user.username)
    return TokenResponse(access_token=token, username=user.username)


@router.get("/me", response_model=UserOut, summary="获取当前登录用户")
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
