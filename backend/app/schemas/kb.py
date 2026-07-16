"""知识库相关的请求/响应数据模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class KbCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="知识库名称")
    description: str = Field("", max_length=512)
    retrieval_type: Literal["dense", "hybrid"] = Field(
        "dense", description="检索方式：dense=稠密向量 / hybrid=混合检索"
    )


class KbOut(BaseModel):
    id: int
    name: str
    description: str
    retrieval_type: str
    created_at: datetime
    document_count: int = 0

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: int
    kb_id: int
    filename: str
    file_type: str
    status: str
    error_msg: str
    chunk_count: int
    char_count: int
    chunk_size: int
    chunk_overlap: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChunkOut(BaseModel):
    id: int
    kb_id: int
    document_id: int
    chunk_index: int
    content: str
    char_count: int

    model_config = {"from_attributes": True}


class ChunkPage(BaseModel):
    total: int
    items: list[ChunkOut]


class ChunkUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1, description="块的新内容")


class ChunkPreviewItem(BaseModel):
    chunk_index: int
    content: str
    char_count: int


class ChunkPreviewOut(BaseModel):
    """切块预览结果：总块数 + 前若干块（不落库）。"""

    total: int
    items: list[ChunkPreviewItem]
