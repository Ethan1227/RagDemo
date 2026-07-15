"""文本向量化服务（DashScope text-embedding-v3，OpenAI 兼容模式）。

- 固定向量维度 1024（Milvus 集合 schema 与其绑定，不可动态改）
- DashScope 单次批量上限为 10 条文本，超出自动分批
"""
from __future__ import annotations

from loguru import logger
from openai import AsyncOpenAI

from backend.app.core.config import get_settings

EMBED_DIM = 1024
EMBED_BATCH_SIZE = 10

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            api_key=settings.dashscope.api_key,
            base_url=settings.dashscope.base_url,
        )
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化文本，返回与输入顺序一致的向量列表。"""
    if not texts:
        return []
    settings = get_settings()
    client = _get_client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        resp = await client.embeddings.create(
            model=settings.dashscope.embedding_model,
            input=batch,
            dimensions=EMBED_DIM,
        )
        # API 返回顺序与输入一致，仍按 index 排序以防万一
        ordered = sorted(resp.data, key=lambda d: d.index)
        vectors.extend([d.embedding for d in ordered])
    logger.debug("向量化完成：{} 条文本", len(texts))
    return vectors


async def embed_query(text: str) -> list[float]:
    """向量化单条查询文本。"""
    vectors = await embed_texts([text])
    return vectors[0]
