"""知识库管理路由：库 CRUD、文档上传解析、块预览/编辑/删除。

文档解析流程（后台任务）：MinIO 存原件 -> 提取文本 -> 切块 -> 向量化 -> 写 Milvus，
期间文档状态 parsing -> done/failed，前端轮询文档列表获取进度。
知识库为全局共享：所有登录用户可见可用，created_by 仅作审计。
"""
from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.db.session import async_session_maker, get_db
from backend.app.models.kb import KbChunk, KbDocument, KnowledgeBase
from backend.app.models.user import User
from backend.app.schemas.kb import (
    ChunkOut,
    ChunkPage,
    ChunkPreviewItem,
    ChunkPreviewOut,
    ChunkUpdateRequest,
    DocumentOut,
    KbCreateRequest,
    KbOut,
)
from backend.app.services import embedding, milvus_store, storage
from backend.app.services.parser import (
    UnsupportedFileTypeError,
    detect_file_type,
    extract_text,
    split_text,
)

router = APIRouter(
    prefix="/api/kb", tags=["知识库"], dependencies=[Depends(get_current_user)]
)

# 上传文件大小上限（50MB），超出显式拒绝
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# 切块预览返回的块数上限
PREVIEW_CHUNK_COUNT = 5


# ---------------- 知识库 CRUD ----------------

@router.post("", response_model=KbOut, status_code=status.HTTP_201_CREATED, summary="创建知识库")
async def create_kb(
    payload: KbCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KbOut:
    exists = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.name == payload.name)
    )
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="同名知识库已存在")
    kb = KnowledgeBase(
        name=payload.name,
        description=payload.description,
        retrieval_type=payload.retrieval_type,
        created_by=current_user.id,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    logger.info("知识库创建：{}（{}）", kb.name, kb.retrieval_type)
    return KbOut.model_validate(kb)


@router.get("", response_model=list[KbOut], summary="知识库列表")
async def list_kb(db: AsyncSession = Depends(get_db)) -> list[KbOut]:
    rows = (
        await db.execute(
            select(KnowledgeBase, func.count(KbDocument.id))
            .outerjoin(KbDocument, KbDocument.kb_id == KnowledgeBase.id)
            .group_by(KnowledgeBase.id)
            .order_by(KnowledgeBase.id.desc())
        )
    ).all()
    result = []
    for kb, doc_count in rows:
        item = KbOut.model_validate(kb)
        item.document_count = doc_count
        result.append(item)
    return result


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除知识库")
async def delete_kb(kb_id: int, db: AsyncSession = Depends(get_db)) -> None:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    await db.delete(kb)
    await db.commit()
    await milvus_store.delete_by_kb(kb_id)
    logger.info("知识库已删除：{}（id={}）", kb.name, kb_id)


# ---------------- 文档上传与解析 ----------------

async def _parse_document_task(document_id: int, filename: str, data: bytes) -> None:
    """后台解析任务：独立会话，完成后更新文档状态。"""
    async with async_session_maker() as db:
        doc = await db.get(KbDocument, document_id)
        if doc is None:
            return
        try:
            text = extract_text(filename, data)
            chunks = split_text(text, doc.chunk_size, doc.chunk_overlap)
            if not chunks:
                raise ValueError("解析结果为空：文档无可提取文本")

            # 块入 MySQL（先拿到自增 id 作为 Milvus 主键）
            chunk_rows = [
                KbChunk(
                    kb_id=doc.kb_id,
                    document_id=doc.id,
                    chunk_index=i,
                    content=content,
                    char_count=len(content),
                )
                for i, content in enumerate(chunks)
            ]
            db.add_all(chunk_rows)
            await db.flush()

            # 向量化并写入 Milvus
            vectors = await embedding.embed_texts([c.content for c in chunk_rows])
            await milvus_store.upsert_chunks(
                [
                    {
                        "id": c.id,
                        "kb_id": c.kb_id,
                        "document_id": c.document_id,
                        "vector": v,
                    }
                    for c, v in zip(chunk_rows, vectors)
                ]
            )

            doc.status = "done"
            doc.chunk_count = len(chunk_rows)
            doc.char_count = len(text)
            await db.commit()
            logger.info("文档解析完成：{}（{} 块）", filename, len(chunk_rows))
        except Exception as exc:
            await db.rollback()
            doc = await db.get(KbDocument, document_id)
            if doc is not None:
                doc.status = "failed"
                doc.error_msg = str(exc)[:500]
                await db.commit()
            logger.error("文档解析失败：{}：{}", filename, exc)


@router.post(
    "/{kb_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="上传文档并解析",
)
async def upload_document(
    kb_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    chunk_size: int = Form(512, ge=64, le=4096),
    chunk_overlap: int = Form(50, ge=0, le=1024),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    if chunk_overlap >= chunk_size:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="重叠大小必须小于切块大小"
        )
    try:
        file_type = detect_file_type(file.filename or "")
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="文件超过 50MB 上限"
        )
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="文件内容为空")

    minio_object = await storage.save_file("kb", file.filename or "unnamed", data)
    doc = KbDocument(
        kb_id=kb_id,
        filename=file.filename or "unnamed",
        file_type=file_type,
        status="parsing",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        minio_object=minio_object,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(_parse_document_task, doc.id, doc.filename, data)
    return DocumentOut.model_validate(doc)


@router.post(
    "/preview-chunks",
    response_model=ChunkPreviewOut,
    summary="预览切块效果（按参数试切，不落库）",
)
async def preview_chunks(
    file: UploadFile = File(...),
    chunk_size: int = Form(512, ge=64, le=4096),
    chunk_overlap: int = Form(50, ge=0, le=1024),
) -> ChunkPreviewOut:
    if chunk_overlap >= chunk_size:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="重叠大小必须小于切块大小"
        )
    try:
        detect_file_type(file.filename or "")
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="文件超过 50MB 上限"
        )
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="文件内容为空")

    text = extract_text(file.filename or "unnamed", data)
    chunks = split_text(text, chunk_size, chunk_overlap)
    return ChunkPreviewOut(
        total=len(chunks),
        items=[
            ChunkPreviewItem(chunk_index=i, content=c, char_count=len(c))
            for i, c in enumerate(chunks[:PREVIEW_CHUNK_COUNT])
        ],
    )


@router.get("/{kb_id}/documents", response_model=list[DocumentOut], summary="文档列表")
async def list_documents(
    kb_id: int, db: AsyncSession = Depends(get_db)
) -> list[DocumentOut]:
    rows = (
        await db.execute(
            select(KbDocument)
            .where(KbDocument.kb_id == kb_id)
            .order_by(KbDocument.id.desc())
        )
    ).scalars().all()
    return [DocumentOut.model_validate(d) for d in rows]


@router.delete(
    "/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除文档"
)
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)) -> None:
    doc = await db.get(KbDocument, doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="文档不存在")
    minio_object = doc.minio_object
    await db.delete(doc)
    await db.commit()
    await milvus_store.delete_by_document(doc_id)
    await storage.remove_file(minio_object)
    logger.info("文档已删除：{}（id={}）", doc.filename, doc_id)


# ---------------- 块预览 / 编辑 / 删除 ----------------

@router.get(
    "/documents/{doc_id}/chunks", response_model=ChunkPage, summary="文档块分页预览"
)
async def list_chunks(
    doc_id: int,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
) -> ChunkPage:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = (
        await db.execute(
            select(func.count(KbChunk.id)).where(KbChunk.document_id == doc_id)
        )
    ).scalar_one()
    rows = (
        await db.execute(
            select(KbChunk)
            .where(KbChunk.document_id == doc_id)
            .order_by(KbChunk.chunk_index)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return ChunkPage(total=total, items=[ChunkOut.model_validate(c) for c in rows])


@router.put("/chunks/{chunk_id}", response_model=ChunkOut, summary="编辑文档块")
async def update_chunk(
    chunk_id: int, payload: ChunkUpdateRequest, db: AsyncSession = Depends(get_db)
) -> ChunkOut:
    chunk = await db.get(KbChunk, chunk_id)
    if chunk is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="文档块不存在")
    chunk.content = payload.content
    chunk.char_count = len(payload.content)
    await db.commit()
    await db.refresh(chunk)

    # 内容变更后重新向量化并同步 Milvus
    vector = await embedding.embed_query(payload.content)
    await milvus_store.upsert_chunks(
        [
            {
                "id": chunk.id,
                "kb_id": chunk.kb_id,
                "document_id": chunk.document_id,
                "vector": vector,
            }
        ]
    )
    logger.info("文档块已更新并重新向量化：chunk_id={}", chunk_id)
    return ChunkOut.model_validate(chunk)


@router.delete(
    "/chunks/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除文档块"
)
async def delete_chunk(chunk_id: int, db: AsyncSession = Depends(get_db)) -> None:
    chunk = await db.get(KbChunk, chunk_id)
    if chunk is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="文档块不存在")
    doc = await db.get(KbDocument, chunk.document_id)
    await db.delete(chunk)
    if doc is not None and doc.chunk_count > 0:
        doc.chunk_count -= 1
    await db.commit()
    await milvus_store.delete_by_chunk_ids([chunk_id])
    logger.info("文档块已删除：chunk_id={}", chunk_id)
