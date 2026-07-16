"""证据材料路由：上传（后台 OCR + 抽取）、列表、详情、修正、删除。"""
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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.db.session import async_session_maker, get_db
from backend.app.models.case import Evidence
from backend.app.models.user import User
from backend.app.schemas.evidence import (
    EVIDENCE_CATEGORIES,
    EvidenceOut,
    EvidenceUpdateRequest,
)
from backend.app.services import extractor, ocr, storage

router = APIRouter(
    prefix="/api/evidence", tags=["证据材料"], dependencies=[Depends(get_current_user)]
)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


async def _get_owned_evidence(ev_id: int, db: AsyncSession, user: User) -> Evidence:
    ev = await db.get(Evidence, ev_id)
    if ev is None or ev.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="证据不存在")
    return ev


async def _process_evidence_task(evidence_id: int, filename: str, data: bytes) -> None:
    """后台任务：OCR 识别 -> qwen 抽取关键信息 -> 更新状态。"""
    async with async_session_maker() as db:
        ev = await db.get(Evidence, evidence_id)
        if ev is None:
            return
        ev.ocr_status = "processing"
        await db.commit()
        try:
            text = await ocr.recognize(filename, data)
            extracted = await extractor.extract(text)
            ev = await db.get(Evidence, evidence_id)
            ev.ocr_text = text
            ev.extracted = extracted
            ev.ocr_status = "done"
            if not ev.name:
                ev.name = extracted.get("summary", "")[:100] or filename
            await db.commit()
            logger.info("证据处理完成：{}（{} 字符）", filename, len(text))
        except Exception as exc:
            await db.rollback()
            ev = await db.get(Evidence, evidence_id)
            if ev is not None:
                ev.ocr_status = "failed"
                ev.error_msg = str(exc)[:500]
                await db.commit()
            logger.error("证据处理失败：{}：{}", filename, exc)


@router.get("/categories", summary="证据分类列表")
async def list_categories() -> list[str]:
    return EVIDENCE_CATEGORIES


@router.post("", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED, summary="上传证据")
async def upload_evidence(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form("书证"),
    name: str = Form(""),
    case_id: int | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EvidenceOut:
    try:
        file_type = ocr.detect_evidence_type(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="文件超过 20MB 上限")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="文件内容为空")

    minio_object = await storage.save_file("evidence", file.filename or "unnamed", data)
    ev = Evidence(
        user_id=user.id,
        case_id=case_id,
        name=name,
        filename=file.filename or "unnamed",
        file_type=file_type,
        category=category,
        minio_object=minio_object,
        ocr_status="pending",
        extracted={},
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)

    background_tasks.add_task(_process_evidence_task, ev.id, ev.filename, data)
    return EvidenceOut.model_validate(ev)


@router.get("", response_model=list[EvidenceOut], summary="证据列表（可按案件过滤）")
async def list_evidence(
    case_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EvidenceOut]:
    stmt = select(Evidence).where(Evidence.user_id == user.id)
    if case_id is not None:
        stmt = stmt.where(Evidence.case_id == case_id)
    rows = (await db.execute(stmt.order_by(Evidence.id.desc()))).scalars().all()
    return [EvidenceOut.model_validate(e) for e in rows]


@router.get("/{ev_id}", response_model=EvidenceOut, summary="证据详情")
async def get_evidence(
    ev_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EvidenceOut:
    ev = await _get_owned_evidence(ev_id, db, user)
    return EvidenceOut.model_validate(ev)


@router.put("/{ev_id}", response_model=EvidenceOut, summary="修正证据信息/抽取结果")
async def update_evidence(
    ev_id: int,
    payload: EvidenceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EvidenceOut:
    ev = await _get_owned_evidence(ev_id, db, user)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(ev, field, value)
    await db.commit()
    await db.refresh(ev)
    return EvidenceOut.model_validate(ev)


@router.delete("/{ev_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除证据")
async def delete_evidence(
    ev_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    ev = await _get_owned_evidence(ev_id, db, user)
    minio_object = ev.minio_object
    await db.delete(ev)
    await db.commit()
    await storage.remove_file(minio_object)
    logger.info("证据已删除：id={}", ev_id)
