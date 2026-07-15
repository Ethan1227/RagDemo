"""混合检索纯逻辑测试：分词、BM25、RRF 融合。"""
from __future__ import annotations

from backend.app.services.retriever import bm25_search, rrf_fuse, tokenize


def test_tokenize_chinese():
    tokens = tokenize("诉讼时效期间为三年")
    assert "诉讼" in tokens or "诉讼时效" in tokens
    assert all(t.strip() for t in tokens)


def test_bm25_search_relevance():
    corpus = [
        (1, "向人民法院请求保护民事权利的诉讼时效期间为三年"),
        (2, "对公民提起的民事诉讼，由被告住所地人民法院管辖"),
        (3, "当事人对自己提出的主张，有责任提供证据"),
    ]
    results = bm25_search("诉讼时效是多久", corpus, limit=3)
    assert results, "应有命中"
    assert results[0][0] == 1, "诉讼时效相关块应排第一"


def test_bm25_search_empty_corpus():
    assert bm25_search("问题", [], 5) == []


def test_bm25_limit_and_zero_score_filtered():
    # 注：语料需 >=3 条，词项出现于其中 1 条时 IDF 才为正
    #（BM25Okapi 在 2 条语料、词项占一半文档的病态场景下 IDF=0）
    corpus = [
        (1, "合同违约责任的承担方式"),
        (2, "完全无关的内容水果蔬菜"),
        (3, "另一段无关内容天气晴朗"),
    ]
    results = bm25_search("合同违约", corpus, limit=5)
    ids = [cid for cid, _ in results]
    assert 1 in ids
    assert 2 not in ids and 3 not in ids, "零分块应被过滤"


def test_rrf_fuse_combines_rankings():
    dense = [(1, 0.95), (2, 0.90), (3, 0.85)]
    sparse = [(2, 8.0), (3, 6.0)]
    fused = rrf_fuse([dense, sparse])
    # chunk2 在两路均靠前，应排第一
    assert fused[0][0] == 2
    # 三个块都应出现
    assert {cid for cid, _ in fused} == {1, 2, 3}


def test_rrf_fuse_single_list_keeps_order():
    single = [(7, 0.9), (8, 0.5)]
    fused = rrf_fuse([single])
    assert [cid for cid, _ in fused] == [7, 8]


def test_rrf_fuse_empty():
    assert rrf_fuse([[], []]) == []
