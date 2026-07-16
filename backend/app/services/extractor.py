"""证据关键信息抽取服务（qwen 结构化输出）。

从 OCR 文本中抽取：当事人姓名、金额、日期、内容摘要。
提示词强约束仅输出 JSON；解析失败重试 1 次后显式失败。
"""
from __future__ import annotations

import json
import re

from loguru import logger
from openai import AsyncOpenAI

from backend.app.core.config import get_settings

_client: AsyncOpenAI | None = None
_MAX_TEXT_CHARS = 4000  # 送入模型的 OCR 文本上限

_SYSTEM = "你是专业的法律文书信息抽取助手，只输出 JSON，不输出任何解释性文字。"

_PROMPT_TEMPLATE = """请从以下证据材料文本中抽取关键信息，严格按 JSON 格式输出，不要输出 JSON 以外的任何内容。

字段说明：
- parties: 涉及的当事人姓名或单位名称列表（字符串数组，无则空数组）
- amounts: 涉及的金额列表，保留原文表述如"人民币10000元"（字符串数组，无则空数组）
- dates: 涉及的日期列表，保留原文表述如"2024年3月1日"（字符串数组，无则空数组）
- summary: 一句话概括该证据的主要内容（字符串）

输出格式示例：
{{"parties": ["张三", "李四"], "amounts": ["人民币50000元"], "dates": ["2024年1月1日"], "summary": "张三向李四借款5万元的借条"}}

证据材料文本：
{text}"""


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            api_key=settings.dashscope.api_key, base_url=settings.dashscope.base_url
        )
    return _client


def _parse_json(raw: str) -> dict:
    """容错解析：去除 ```json 包裹，提取首个 JSON 对象。"""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("模型输出中未找到 JSON")
    return json.loads(match.group(0))


def _normalize(data: dict) -> dict:
    """字段规整：确保四个字段类型正确。"""
    def _as_list(v):
        if isinstance(v, list):
            return [str(x) for x in v]
        if v:
            return [str(v)]
        return []

    return {
        "parties": _as_list(data.get("parties")),
        "amounts": _as_list(data.get("amounts")),
        "dates": _as_list(data.get("dates")),
        "summary": str(data.get("summary") or ""),
    }


async def extract(ocr_text: str) -> dict:
    """抽取关键信息，返回 {parties, amounts, dates, summary}。"""
    text = (ocr_text or "").strip()
    if not text:
        return {"parties": [], "amounts": [], "dates": [], "summary": ""}

    settings = get_settings()
    client = _get_client()
    prompt = _PROMPT_TEMPLATE.format(text=text[:_MAX_TEXT_CHARS])
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": prompt},
    ]

    last_err: Exception | None = None
    for attempt in range(2):  # 最多尝试 2 次（1 次重试）
        try:
            resp = await client.chat.completions.create(
                model=settings.dashscope.llm_model,
                messages=messages,
                temperature=0.1,
            )
            data = _parse_json(resp.choices[0].message.content or "")
            return _normalize(data)
        except Exception as exc:
            last_err = exc
            logger.warning("信息抽取第 {} 次失败：{}", attempt + 1, exc)

    raise RuntimeError(f"证据信息抽取失败：{last_err}")
