"""起诉状路由：SSE 流式生成、列表、编辑、删除、Word 导出。

流式协议（text/event-stream）：
  {"type":"laws","laws":[...]}          推荐法条
  {"type":"citations","citations":[...]}  知识库引用来源（选择知识库增强时推送，供前端溯源面板）
  {"type":"delta","content":"..."}      增量正文
  {"type":"done","complaint_id":N}      完成，含落库草稿 id
  {"type":"error","detail":"..."}       异常
"""
from __future__ import annotations

import json
import urllib.parse
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.chat import CITATION_SNIPPET_LEN
from backend.app.api.deps import get_current_user
from backend.app.db.session import async_session_maker, get_db
from backend.app.models.case import Case, Complaint, Evidence
from backend.app.models.user import User
from backend.app.schemas.complaint import (
    ComplaintGenerateRequest,
    ComplaintOut,
    ComplaintUpdateRequest,
)
from backend.app.services import complaint_gen, docx_export, law_recommend, retriever

router = APIRouter(prefix="/api/complaints", tags=["起诉状"])


async def _get_owned_complaint(cid: int, db: AsyncSession, user: User) -> Complaint:
    c = await db.get(Complaint, cid)
    if c is None or c.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="起诉状不存在")
    return c


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _stream_generate(
    case_id: int, user_id: int, kb_ids: list[int]
) -> AsyncGenerator[str, None]:
    accumulated = ""
    async with async_session_maker() as db:
        case = await db.get(Case, case_id)
        if case is None or case.user_id != user_id:
            yield _sse({"type": "error", "detail": "案件不存在"})
            return
        try:
            case_dict = {
                "cause": case.cause,
                "plaintiffs": case.plaintiffs,
                "defendants": case.defendants,
                "claims": case.claims,
                "facts": case.facts,
                "court": case.court,
            }
            # 证据清单
            ev_rows = (
                await db.execute(select(Evidence).where(Evidence.case_id == case_id))
            ).scalars().all()
            evidences = [
                {
                    "name": e.name,
                    "filename": e.filename,
                    "category": e.category,
                    "extracted": e.extracted,
                }
                for e in ev_rows
            ]
            # 推荐法条
            laws = law_recommend.recommend_by_cause(case.cause)
            yield _sse({"type": "laws", "laws": laws})

            # 可选知识库检索增强
            kb_contexts = []
            if kb_ids:
                query = f"{case.cause} {case.claims}"
                try:
                    kb_contexts = await retriever.retrieve(db, query, kb_ids, top_k=3)
                except Exception as exc:
                    logger.warning("起诉状知识库检索失败：{}", exc)
            # 引用来源结构与 chat 的 citations 事件保持一致，前端溯源面板复用
            citations = [
                {
                    "index": i,
                    "chunk_id": ctx["chunk_id"],
                    "kb_name": ctx["kb_name"],
                    "filename": ctx["filename"],
                    "score": ctx["score"],
                    "snippet": ctx["content"][:CITATION_SNIPPET_LEN],
                }
                for i, ctx in enumerate(kb_contexts, start=1)
            ]
            yield _sse({"type": "citations", "citations": citations})

            # 流式生成
            async for delta in complaint_gen.generate_stream(
                case_dict, evidences, laws, kb_contexts
            ):
                accumulated += delta
                yield _sse({"type": "delta", "content": delta})

            # 落库草稿
            complaint = Complaint(
                user_id=user_id,
                case_id=case_id,
                cause=case.cause,
                content=accumulated,
            )
            db.add(complaint)
            await db.commit()
            await db.refresh(complaint)
            yield _sse({"type": "done", "complaint_id": complaint.id})
        except Exception as exc:
            logger.error("起诉状生成异常：case={}：{}", case_id, exc)
            yield _sse({"type": "error", "detail": f"生成失败：{exc}"})


@router.post("/generate/stream", summary="流式生成起诉状（SSE）")
async def generate_stream(
    payload: ComplaintGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    case = await db.get(Case, payload.case_id)
    if case is None or case.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="案件不存在")
    return StreamingResponse(
        _stream_generate(payload.case_id, user.id, payload.kb_ids),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("", response_model=list[ComplaintOut], summary="起诉状列表")
async def list_complaints(
    case_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ComplaintOut]:
    stmt = select(Complaint).where(Complaint.user_id == user.id)
    if case_id is not None:
        stmt = stmt.where(Complaint.case_id == case_id)
    rows = (await db.execute(stmt.order_by(Complaint.id.desc()))).scalars().all()
    return [ComplaintOut.model_validate(c) for c in rows]


@router.get("/{cid}", response_model=ComplaintOut, summary="起诉状详情")
async def get_complaint(
    cid: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ComplaintOut:
    c = await _get_owned_complaint(cid, db, user)
    return ComplaintOut.model_validate(c)


@router.put("/{cid}", response_model=ComplaintOut, summary="在线编辑起诉状")
async def update_complaint(
    cid: int,
    payload: ComplaintUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ComplaintOut:
    c = await _get_owned_complaint(cid, db, user)
    c.content = payload.content
    await db.commit()
    await db.refresh(c)
    return ComplaintOut.model_validate(c)


@router.delete("/{cid}", status_code=status.HTTP_204_NO_CONTENT, summary="删除起诉状")
async def delete_complaint(
    cid: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    c = await _get_owned_complaint(cid, db, user)
    await db.delete(c)
    await db.commit()


@router.get("/{cid}/export/docx", summary="导出 Word")
async def export_docx(
    cid: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    c = await _get_owned_complaint(cid, db, user)
    data = docx_export.render_docx(c.content)
    filename = f"民事起诉状_{c.cause or '案件'}_{cid}.docx"
    # 中文文件名按 RFC 5987 编码，避免非 ASCII 报错
    quoted = urllib.parse.quote(filename)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )
