"""认证相关的请求/响应数据模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class CaptchaResponse(BaseModel):
    captcha_id: str = Field(..., description="验证码标识，提交时回传")
    image: str = Field(..., description="验证码图片，base64 data URI")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, description="登录账号")
    password: str = Field(..., min_length=6, max_length=64, description="密码")
    confirm_password: str = Field(..., description="确认密码")
    captcha_id: str = Field(..., description="验证码标识")
    captcha_code: str = Field(..., min_length=1, description="验证码文本")

    @field_validator("username")
    @classmethod
    def username_no_space(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("账号不能为空")
        if any(c.isspace() for c in v):
            raise ValueError("账号不能包含空格")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self


class LoginRequest(BaseModel):
    username: str = Field(..., description="登录账号")
    password: str = Field(..., description="密码")
    captcha_id: str = Field(..., description="验证码标识")
    captcha_code: str = Field(..., min_length=1, description="验证码文本")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}
