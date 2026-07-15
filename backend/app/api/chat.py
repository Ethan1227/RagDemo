"""法律咨询对话路由：会话 CRUD、历史消息、SSE 流式问答。

流式协议（text/event-stream，每条 data: JSON）：
  {"type":"citations","citations":[...]}   检索完成，先推送引用来源
  {"type":"delta","content":"..."}         增量文本（多条）
  {"type":"done","message_id":N}           完成，含落库后的消息 id
  {"type":"error","detail":"..."}          异常（显式暴露，不静默）
免责声明由服务端在回答末尾统一追加。
"""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.core.config import get_settings
from backend.app.db.session import async_session_maker, get_db
from backend.app.models.chat import ChatMessage, ChatSession
from backend.app.models.user import User
from backend.app.schemas.chat import (
    ChatRequest,
    MessageOut,
    SessionCreateRequest,
    SessionOut,
    SessionUpdateRequest,
)
from backend.app.services import llm, retriever
from backend.app.services.prompts import DISCLAIMER, SYSTEM_PROMPT, build_user_prompt

router = APIRouter(prefix="/api/chat", tags=["法律咨询"])

# 引用片段在响应中的截断长度（前端悬浮展示用）
CITATION_SNIPPET_LEN = 200


async def _get_owned_session(
    session_id: int, db: AsyncSession, user: User
) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return session


# ---------------- 会话 CRUD ----------------

@router.post(
    "/sessions",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="新建会话",
)
async def create_session(
    payload: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionOut:
    settings = get_settings()
    session = ChatSession(
        user_id=user.id,
        name=payload.name,
        model=settings.dashscope.llm_model,
        temperature=settings.chat.temperature,
        top_p=settings.chat.top_p,
        max_tokens=settings.chat.max_tokens,
        history_rounds=settings.chat.history_rounds,
        kb_ids=[],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionOut.model_validate(session)


@router.get("/sessions", response_model=list[SessionOut], summary="会话列表")
async def list_sessions(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[SessionOut]:
    rows = (
        await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(ChatSession.id.desc())
        )
    ).scalars().all()
    return [SessionOut.model_validate(s) for s in rows]


@router.put("/sessions/{session_id}", response_model=SessionOut, summary="更新会话（重命名/参数）")
async def update_session(
    session_id: int,
    payload: SessionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionOut:
    session = await _get_owned_session(session_id, db, user)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(session, field, value)
    await db.commit()
    await db.refresh(session)
    return SessionOut.model_validate(session)


@router.delete(
    "/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除会话"
)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    session = await _get_owned_session(session_id, db, user)
    await db.delete(session)
    await db.commit()
    logger.info("会话已删除：id={} user={}", session_id, user.username)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[MessageOut],
    summary="历史消息",
)
async def list_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MessageOut]:
    await _get_owned_session(session_id, db, user)
    rows = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id)
        )
    ).scalars().all()
    return [MessageOut.model_validate(m) for m in rows]


# ---------------- SSE 流式问答 ----------------

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _stream_answer(
    session_id: int, question: str
) -> AsyncGenerator[str, None]:
    """流式生成回答：检索 -> 引用 -> LLM 增量 -> 免责声明 -> 落库。"""
    settings = get_settings()
    accumulated = ""
    citations: list[dict] = []
    async with async_session_maker() as db:
        session = await db.get(ChatSession, session_id)
        if session is None:
            yield _sse({"type": "error", "detail": "会话不存在"})
            return
        try:
            # 1) 保存用户消息
            db.add(ChatMessage(session_id=session_id, role="user", content=question))
            await db.commit()

            # 2) 历史消息（最近 history_rounds 轮，不含刚保存的这条）
            history_limit = session.history_rounds * 2
            history: list[ChatMessage] = []
            if history_limit > 0:
                rows = (
                    await db.execute(
                        select(ChatMessage)
                        .where(ChatMessage.session_id == session_id)
                        .order_by(ChatMessage.id.desc())
                        .offset(1)
                        .limit(history_limit)
                    )
                ).scalars().all()
                history = list(reversed(rows))

            # 3) 检索选中知识库
            contexts = await retriever.retrieve(
                db, question, list(session.kb_ids or []), settings.rag.top_k
            )
            citations = [
                {
                    "index": i,
                    "chunk_id": ctx["chunk_id"],
                    "kb_name": ctx["kb_name"],
                    "filename": ctx["filename"],
                    "score": ctx["score"],
                    "snippet": ctx["content"][:CITATION_SNIPPET_LEN],
                }
                for i, ctx in enumerate(contexts, start=1)
            ]
            yield _sse({"type": "citations", "citations": citations})

            # 4) 组装消息并流式生成
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages += [{"role": m.role, "content": m.content} for m in history]
            messages.append(
                {"role": "user", "content": build_user_prompt(question, contexts)}
            )
            async for delta in llm.stream_chat(
                messages,
                model=session.model,
                temperature=session.temperature,
                top_p=session.top_p,
                max_tokens=session.max_tokens,
            ):
                accumulated += delta
                yield _sse({"type": "delta", "content": delta})

            # 5) 服务端统一追加免责声明
            disclaimer_block = f"\n\n---\n{DISCLAIMER}"
            accumulated += disclaimer_block
            yield _sse({"type": "delta", "content": disclaimer_block})

            # 6) 落库助手消息
            assistant = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=accumulated,
                citations=citations,
            )
            db.add(assistant)
            await db.commit()
            await db.refresh(assistant)
            yield _sse({"type": "done", "message_id": assistant.id})
        except Exception as exc:
            logger.error("流式问答异常：session={}：{}", session_id, exc)
            # 已产出的部分内容也落库，避免用户所见与历史不一致
            if accumulated:
                db.add(
                    ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content=accumulated + "\n\n（回答因异常中断）",
                        citations=citations,
                    )
                )
                await db.commit()
            yield _sse({"type": "error", "detail": f"回答生成失败：{exc}"})


@router.post("/sessions/{session_id}/stream", summary="流式问答（SSE）")
async def stream_chat_endpoint(
    session_id: int,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    # 归属校验在请求会话中完成，流式生成器内使用独立会话
    await _get_owned_session(session_id, db, user)
    return StreamingResponse(
        _stream_answer(session_id, payload.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
