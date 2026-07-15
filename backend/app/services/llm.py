"""大模型对话服务（通义千问，OpenAI 兼容模式，流式输出）。"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from loguru import logger
from openai import AsyncOpenAI

from backend.app.core.config import get_settings

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


async def stream_chat(
    messages: list[dict],
    model: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> AsyncGenerator[str, None]:
    """流式对话，逐段产出增量文本。

    messages 为 OpenAI 格式：[{"role": "system"|"user"|"assistant", "content": str}]
    """
    client = _get_client()
    logger.info("LLM 流式请求：model={} messages={} 条", model, len(messages))
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
