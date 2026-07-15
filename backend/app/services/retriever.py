"""混合检索服务：稠密(Milvus) + 稀疏(BM25) + RRF 融合 + 重排。

- 稠密：查询向量化后走 Milvus HNSW/COSINE
- 稀疏：jieba 分词 + BM25Okapi，对选中知识库在 MySQL 中的块文本建临时索引
  （语料规模中小时性能足够；后续可替换为持久化倒排/升级 Milvus 2.5 原生 BM25）
- 融合：Reciprocal Rank Fusion（k=60）
- 重排：gte-rerank；调用失败时记录告警并回退到融合排序（保证检索可用）
"""
from __future__ import annotations

import jieba
from loguru import logger
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.kb import KbChunk, KbDocument, KnowledgeBase
from backend.app.services import embedding, milvus_store, reranker

# 候选扩展倍数：先取 top_k*3 的候选再融合/重排，提升召回
CANDIDATE_MULTIPLIER = 3
RRF_K = 60


def tokenize(text: str) -> list[str]:
    """jieba 精确模式分词，过滤空白。"""
    return [t for t in jieba.lcut(text) if t.strip()]


def bm25_search(
    query: str, corpus: list[tuple[int, str]], limit: int
) -> list[tuple[int, float]]:
    """BM25 稀疏检索。corpus: [(chunk_id, content)]，返回 [(chunk_id, score)] 降序。"""
    if not corpus:
        return []
    tokenized = [tokenize(content) for _, content in corpus]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(zip((cid for cid, _ in corpus), scores), key=lambda x: x[1], reverse=True)
    return [(cid, float(s)) for cid, s in ranked[:limit] if s > 0]


def rrf_fuse(
    result_lists: list[list[tuple[int, float]]], k: int = RRF_K
) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion：score = Σ 1/(k + rank)。返回按融合分降序。"""
    fused: dict[int, float] = {}
    for results in result_lists:
        for rank, (chunk_id, _) in enumerate(results, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)


async def retrieve(
    db: AsyncSession, query: str, kb_ids: list[int], top_k: int
) -> list[dict]:
    """检索主入口。

    返回 [{chunk_id, content, score, document_id, filename, kb_id, kb_name}]，
    数量最多 top_k，按相关性降序。
    """
    if not kb_ids:
        return []

    # 选中的知识库中任一配置为 hybrid，即启用混合检索
    kb_rows = (
        await db.execute(select(KnowledgeBase).where(KnowledgeBase.id.in_(kb_ids)))
    ).scalars().all()
    if not kb_rows:
        return []
    use_hybrid = any(kb.retrieval_type == "hybrid" for kb in kb_rows)
    candidate_limit = top_k * CANDIDATE_MULTIPLIER

    # 1) 稠密检索
    query_vector = await embedding.embed_query(query)
    dense = await milvus_store.search_chunks(query_vector, kb_ids, candidate_limit)

    # 2) 稀疏检索 + RRF 融合（仅混合模式）
    if use_hybrid:
        corpus_rows = (
            await db.execute(
                select(KbChunk.id, KbChunk.content).where(KbChunk.kb_id.in_(kb_ids))
            )
        ).all()
        sparse = bm25_search(query, [(r.id, r.content) for r in corpus_rows], candidate_limit)
        candidates = rrf_fuse([dense, sparse])
        logger.debug("混合检索：dense={} sparse={} fused={}", len(dense), len(sparse), len(candidates))
    else:
        candidates = dense

    candidate_ids = [cid for cid, _ in candidates[:candidate_limit]]
    if not candidate_ids:
        return []

    # 3) 取块内容（保持候选顺序）
    chunk_rows = (
        await db.execute(
            select(KbChunk, KbDocument.filename, KnowledgeBase.name)
            .join(KbDocument, KbChunk.document_id == KbDocument.id)
            .join(KnowledgeBase, KbChunk.kb_id == KnowledgeBase.id)
            .where(KbChunk.id.in_(candidate_ids))
        )
    ).all()
    by_id = {row.KbChunk.id: row for row in chunk_rows}
    ordered = [by_id[cid] for cid in candidate_ids if cid in by_id]
    score_map = dict(candidates)

    # 4) 重排（失败回退融合排序，不中断检索）
    try:
        reranked = await reranker.rerank(
            query, [row.KbChunk.content for row in ordered], top_n=top_k
        )
        final_rows = [(ordered[idx], score) for idx, score in reranked]
    except Exception as exc:
        logger.warning("重排失败，回退到融合排序：{}", exc)
        final_rows = [
            (row, score_map.get(row.KbChunk.id, 0.0)) for row in ordered[:top_k]
        ]

    return [
        {
            "chunk_id": row.KbChunk.id,
            "content": row.KbChunk.content,
            "score": round(float(score), 6),
            "document_id": row.KbChunk.document_id,
            "filename": row.filename,
            "kb_id": row.KbChunk.kb_id,
            "kb_name": row.name,
        }
        for row, score in final_rows
    ]
