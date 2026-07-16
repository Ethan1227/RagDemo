"""起诉状相关的请求/响应数据模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ComplaintGenerateRequest(BaseModel):
    case_id: int = Field(..., description="案件 ID")
    kb_ids: list[int] = Field(default_factory=list, description="可选：增强检索的知识库")


class ComplaintUpdateRequest(BaseModel):
    content: str = Field(..., description="编辑后的文书内容")


class ComplaintOut(BaseModel):
    id: int
    case_id: int
    cause: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
