"""重排服务（DashScope gte-rerank）。

dashscope SDK 为同步调用，包装到线程池避免阻塞事件循环。
rerank 失败时显式抛出异常，由调用方决定回退策略。
"""
from __future__ import annotations

import asyncio
from http import HTTPStatus

import dashscope
from loguru import logger

from backend.app.core.config import get_settings


def _rerank_sync(query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
    """同步调用 gte-rerank，返回 [(原始下标, 相关性得分)]，按得分降序。"""
    settings = get_settings()
    resp = dashscope.TextReRank.call(
        model=settings.dashscope.rerank_model,
        query=query,
        documents=documents,
        top_n=top_n,
        return_documents=False,
        api_key=settings.dashscope.api_key,
    )
    if resp.status_code != HTTPStatus.OK:
        raise RuntimeError(f"gte-rerank 调用失败：{resp.code} {resp.message}")
    return [(r["index"], r["relevance_score"]) for r in resp.output["results"]]


async def rerank(
    query: str, documents: list[str], top_n: int
) -> list[tuple[int, float]]:
    """异步重排：返回 [(原始下标, 得分)]，按相关性降序，最多 top_n 条。"""
    if not documents:
        return []
    result = await asyncio.to_thread(_rerank_sync, query, documents, top_n)
    logger.debug("重排完成：候选 {} 条 -> 保留 {} 条", len(documents), len(result))
    return result
