"""对话相关的请求/响应数据模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    name: str = Field("新对话", max_length=128)


class SessionUpdateRequest(BaseModel):
    """会话可更新项：名称与推理参数（均可选，仅更新提供的字段）。"""

    name: str | None = Field(None, max_length=128)
    model: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    top_p: float | None = Field(None, gt=0.0, le=1.0)
    max_tokens: int | None = Field(None, ge=1, le=8192)
    history_rounds: int | None = Field(None, ge=0, le=20)
    kb_ids: list[int] | None = None


class SessionOut(BaseModel):
    id: int
    name: str
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    history_rounds: int
    kb_ids: list[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: list
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
