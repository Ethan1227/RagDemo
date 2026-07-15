"""知识库相关模型：知识库、文档、文档块。

块文本存 MySQL（用于预览/编辑/BM25 稀疏检索），向量存 Milvus，
Milvus 主键与 kb_chunks.id 一致，保证双端同步。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="知识库名称"
    )
    description: Mapped[str] = mapped_column(
        String(512), default="", comment="知识库描述"
    )
    retrieval_type: Mapped[str] = mapped_column(
        String(16), default="dense", comment="检索方式：dense=稠密 / hybrid=混合"
    )
    created_by: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="创建者用户ID（知识库全局共享，仅作审计）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    documents: Mapped[list["KbDocument"]] = relationship(
        back_populates="kb", cascade="all, delete-orphan"
    )


class KbDocument(Base):
    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="pdf/docx/md/txt"
    )
    status: Mapped[str] = mapped_column(
        String(16), default="parsing", comment="parsing/done/failed"
    )
    error_msg: Mapped[str] = mapped_column(String(512), default="")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_size: Mapped[int] = mapped_column(Integer, default=512, comment="切块大小")
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=50, comment="切块重叠")
    minio_object: Mapped[str] = mapped_column(
        String(512), default="", comment="MinIO 中的原件对象名"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    kb: Mapped["KnowledgeBase"] = relationship(back_populates="documents")
    chunks: Mapped[list["KbChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KbChunk(Base):
    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("kb_documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="块序号")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    document: Mapped["KbDocument"] = relationship(back_populates="chunks")
