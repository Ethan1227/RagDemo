"""案件相关的请求/响应数据模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Party(BaseModel):
    """当事人（原告/被告）信息。"""

    name: str = Field("", max_length=64)
    id_card: str = Field("", max_length=32, description="身份证号/统一社会信用代码")
    address: str = Field("", max_length=255)
    phone: str = Field("", max_length=32)


class CaseCreateRequest(BaseModel):
    title: str = Field("未命名案件", max_length=255)


class CaseUpdateRequest(BaseModel):
    """分步暂存：所有字段可选，仅更新提供的字段。"""

    title: str | None = Field(None, max_length=255)
    cause: str | None = Field(None, max_length=64)
    status: str | None = Field(None, pattern="^(draft|complete)$")
    current_step: int | None = Field(None, ge=0, le=3)
    plaintiffs: list[Party] | None = None
    defendants: list[Party] | None = None
    claims: str | None = None
    facts: str | None = None
    court: str | None = Field(None, max_length=128)


class CaseOut(BaseModel):
    id: int
    title: str
    cause: str
    status: str
    current_step: int
    plaintiffs: list
    defendants: list
    claims: str
    facts: str
    court: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LawRecommendItem(BaseModel):
    law: str = Field(..., description="法律规范全称")
    article: str = Field(..., description="条文序号")
    summary: str = Field(..., description="条文要旨")


class LawRecommendOut(BaseModel):
    cause: str
    items: list[LawRecommendItem]
