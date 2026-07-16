"""案件信息路由：CRUD、分步暂存、案由列表、法条推荐。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.case import Case
from backend.app.models.user import User
from backend.app.schemas.case import (
    CaseCreateRequest,
    CaseOut,
    CaseUpdateRequest,
    LawRecommendOut,
)
from backend.app.services import law_recommend

router = APIRouter(prefix="/api/cases", tags=["案件信息"])


async def _get_owned_case(case_id: int, db: AsyncSession, user: User) -> Case:
    case = await db.get(Case, case_id)
    if case is None or case.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="案件不存在")
    return case


@router.get("/causes", summary="案由下拉列表")
async def list_causes(_: User = Depends(get_current_user)) -> list[str]:
    return law_recommend.list_causes()


@router.get("/law-recommend", response_model=LawRecommendOut, summary="按案由推荐法条")
async def recommend_law(
    cause: str,
    _: User = Depends(get_current_user),
) -> LawRecommendOut:
    items = law_recommend.recommend_by_cause(cause)
    return LawRecommendOut(cause=cause, items=items)


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED, summary="新建案件")
async def create_case(
    payload: CaseCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseOut:
    case = Case(user_id=user.id, title=payload.title, plaintiffs=[], defendants=[])
    db.add(case)
    await db.commit()
    await db.refresh(case)
    logger.info("案件创建：id={} user={}", case.id, user.username)
    return CaseOut.model_validate(case)


@router.get("", response_model=list[CaseOut], summary="案件列表")
async def list_cases(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CaseOut]:
    rows = (
        await db.execute(
            select(Case).where(Case.user_id == user.id).order_by(Case.id.desc())
        )
    ).scalars().all()
    return [CaseOut.model_validate(c) for c in rows]


@router.get("/{case_id}", response_model=CaseOut, summary="案件详情")
async def get_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseOut:
    case = await _get_owned_case(case_id, db, user)
    return CaseOut.model_validate(case)


@router.put("/{case_id}", response_model=CaseOut, summary="分步暂存/更新案件")
async def update_case(
    case_id: int,
    payload: CaseUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseOut:
    case = await _get_owned_case(case_id, db, user)
    data = payload.model_dump(exclude_none=True)
    # 当事人为 Pydantic 模型列表，转为可序列化 dict
    if "plaintiffs" in data:
        data["plaintiffs"] = [p.model_dump() for p in payload.plaintiffs]
    if "defendants" in data:
        data["defendants"] = [p.model_dump() for p in payload.defendants]
    for field, value in data.items():
        setattr(case, field, value)
    await db.commit()
    await db.refresh(case)
    return CaseOut.model_validate(case)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除案件")
async def delete_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    case = await _get_owned_case(case_id, db, user)
    await db.delete(case)
    await db.commit()
    logger.info("案件已删除：id={}", case_id)
