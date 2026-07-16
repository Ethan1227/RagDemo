"""案件相关模型：案件、证据材料、起诉状。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


class Case(Base):
    """案件信息（Step 表单分步暂存，status=draft/complete）。"""

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="未命名案件")
    cause: Mapped[str] = mapped_column(String(64), default="", comment="案由")
    status: Mapped[str] = mapped_column(String(16), default="draft", comment="draft/complete")
    current_step: Mapped[int] = mapped_column(Integer, default=0, comment="表单当前步骤 0-3")
    plaintiffs: Mapped[list] = mapped_column(
        JSON, default=list, comment="原告列表 [{name,id_card,address,phone}]"
    )
    defendants: Mapped[list] = mapped_column(
        JSON, default=list, comment="被告列表，同原告结构"
    )
    claims: Mapped[str] = mapped_column(Text, default="", comment="诉讼请求")
    facts: Mapped[str] = mapped_column(Text, default="", comment="事实与理由")
    court: Mapped[str] = mapped_column(String(128), default="", comment="致送法院")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Evidence(Base):
    """证据材料（可独立上传，可选关联案件；OCR 后台处理）。"""

    __tablename__ = "evidences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), default="", comment="证据名称")
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="image/pdf/txt")
    category: Mapped[str] = mapped_column(
        String(32), default="书证", comment="书证/物证/视听资料/电子数据/证人证言/其他"
    )
    minio_object: Mapped[str] = mapped_column(String(512), default="")
    ocr_status: Mapped[str] = mapped_column(
        String(16), default="pending", comment="pending/processing/done/failed"
    )
    ocr_text: Mapped[str] = mapped_column(Text, default="", comment="OCR 识别全文")
    extracted: Mapped[dict] = mapped_column(
        JSON, default=dict, comment="{parties,amounts,dates,summary}"
    )
    error_msg: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Complaint(Base):
    """起诉状（LLM 生成草稿，支持在线编辑）。"""

    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    cause: Mapped[str] = mapped_column(String(64), default="")
    content: Mapped[str] = mapped_column(Text, default="", comment="文书内容(Markdown)")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
