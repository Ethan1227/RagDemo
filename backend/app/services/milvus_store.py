"""Milvus 向量存储服务。

集合 legal_chunks 结构（主键与 MySQL kb_chunks.id 一致，保证双端同步）：
  id(INT64, PK) | kb_id(INT64) | document_id(INT64) | vector(FLOAT_VECTOR 1024)

- 懒连接：首次调用时才连接 Milvus
- pymilvus 为同步 SDK，公开接口均包装到线程池，避免阻塞事件循环
- 索引固定为 HNSW + COSINE（M=16, efConstruction=200，检索 ef=64）
"""
from __future__ import annotations

import asyncio
import threading

from loguru import logger
from pymilvus import DataType, MilvusClient

from backend.app.core.config import get_settings
from backend.app.services.embedding import EMBED_DIM

COLLECTION_NAME = "legal_chunks"
_INDEX_PARAMS = {"M": 16, "efConstruction": 200}
_SEARCH_EF = 64

_client: MilvusClient | None = None
_lock = threading.Lock()


def _get_client() -> MilvusClient:
    """获取（并按需初始化）Milvus 客户端与集合。"""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                settings = get_settings()
                uri = f"http://{settings.milvus.host}:{settings.milvus.port}"
                client = MilvusClient(uri=uri)
                _ensure_collection(client)
                _client = client
                logger.info("Milvus 已连接：{}，集合 {} 就绪", uri, COLLECTION_NAME)
    return _client


def _ensure_collection(client: MilvusClient) -> None:
    """集合不存在时创建（含索引），存在则直接加载。"""
    if client.has_collection(COLLECTION_NAME):
        client.load_collection(COLLECTION_NAME)
        return

    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field("kb_id", DataType.INT64)
    schema.add_field("document_id", DataType.INT64)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=EMBED_DIM)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",
        metric_type="COSINE",
        params=_INDEX_PARAMS,
    )
    client.create_collection(
        COLLECTION_NAME, schema=schema, index_params=index_params
    )
    logger.info("Milvus 集合 {} 创建完成（dim={}）", COLLECTION_NAME, EMBED_DIM)


# ---------------- 同步实现 ----------------

def _upsert_sync(rows: list[dict]) -> None:
    client = _get_client()
    client.upsert(collection_name=COLLECTION_NAME, data=rows)


def _search_sync(vector: list[float], kb_ids: list[int], limit: int) -> list[tuple[int, float]]:
    client = _get_client()
    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[vector],
        limit=limit,
        filter=f"kb_id in {list(kb_ids)}",
        search_params={"metric_type": "COSINE", "params": {"ef": _SEARCH_EF}},
    )
    hits = results[0] if results else []
    return [(hit["id"], hit["distance"]) for hit in hits]


def _delete_sync(filter_expr: str) -> None:
    client = _get_client()
    client.delete(collection_name=COLLECTION_NAME, filter=filter_expr)


# ---------------- 异步公开接口 ----------------

async def upsert_chunks(rows: list[dict]) -> None:
    """写入/更新向量。rows: [{id, kb_id, document_id, vector}]"""
    if not rows:
        return
    await asyncio.to_thread(_upsert_sync, rows)
    logger.debug("Milvus upsert {} 条", len(rows))


async def search_chunks(
    vector: list[float], kb_ids: list[int], limit: int
) -> list[tuple[int, float]]:
    """稠密检索：返回 [(chunk_id, 相似度得分)]，按得分降序。"""
    if not kb_ids:
        return []
    return await asyncio.to_thread(_search_sync, vector, kb_ids, limit)


async def delete_by_chunk_ids(chunk_ids: list[int]) -> None:
    if not chunk_ids:
        return
    await asyncio.to_thread(_delete_sync, f"id in {list(chunk_ids)}")


async def delete_by_document(document_id: int) -> None:
    await asyncio.to_thread(_delete_sync, f"document_id == {document_id}")


async def delete_by_kb(kb_id: int) -> None:
    await asyncio.to_thread(_delete_sync, f"kb_id == {kb_id}")
