"""证据材料相关的请求/响应数据模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

EVIDENCE_CATEGORIES = [
    "书证",
    "物证",
    "视听资料",
    "电子数据",
    "证人证言",
    "鉴定意见",
    "勘验笔录",
    "其他",
]


class EvidenceUpdateRequest(BaseModel):
    """修正证据元信息或抽取结果（均可选）。"""

    name: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=32)
    case_id: int | None = None
    extracted: dict | None = None


class EvidenceOut(BaseModel):
    id: int
    case_id: int | None
    name: str
    filename: str
    file_type: str
    category: str
    ocr_status: str
    ocr_text: str
    extracted: dict
    error_msg: str
    created_at: datetime

    model_config = {"from_attributes": True}
