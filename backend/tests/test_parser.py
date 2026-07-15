"""文档解析与切块测试。"""
from __future__ import annotations

import pytest

from backend.app.services.parser import (
    UnsupportedFileTypeError,
    detect_file_type,
    extract_text,
    split_text,
)


def test_detect_file_type_supported():
    assert detect_file_type("民法典.pdf") == "pdf"
    assert detect_file_type("案例.DOCX") == "docx"
    assert detect_file_type("笔记.markdown") == "md"
    assert detect_file_type("a.txt") == "txt"


def test_detect_file_type_rejects_unsupported():
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type("截图.png")
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type("无后缀")


def test_extract_text_txt_and_fallback_gbk():
    assert extract_text("a.txt", "你好世界".encode("utf-8")) == "你好世界"
    assert extract_text("a.txt", "你好世界".encode("gbk")) == "你好世界"


def test_split_text_basic():
    text = "第一条 自然人的民事权利能力一律平等。第二条 民事主体从事民事活动，应当遵循自愿原则。"
    chunks = split_text(text, chunk_size=30, chunk_overlap=5)
    assert len(chunks) >= 2
    # 完整覆盖原文关键内容
    joined = "".join(chunks)
    assert "民事权利能力" in joined and "自愿原则" in joined


def test_split_text_overlap():
    sentence = "这是一个测试句子。"
    text = sentence * 20
    chunks = split_text(text, chunk_size=50, chunk_overlap=20)
    # 相邻块之间应存在重叠内容
    assert len(chunks) >= 2
    assert chunks[1].startswith(sentence)


def test_split_text_long_sentence_hard_cut():
    text = "无标点超长文本" * 100  # 700 字无句读
    chunks = split_text(text, chunk_size=100, chunk_overlap=10)
    assert all(len(c) <= 110 for c in chunks)
    assert "".join(chunks).startswith("无标点超长文本")


def test_split_text_empty_returns_empty():
    assert split_text("", 100, 10) == []
    assert split_text("   \n  ", 100, 10) == []


def test_split_text_invalid_overlap_raises():
    with pytest.raises(ValueError):
        split_text("文本", chunk_size=50, chunk_overlap=50)
