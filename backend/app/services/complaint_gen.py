"""起诉状生成服务：组装提示词并流式生成。"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from backend.app.services import llm
from backend.app.services.complaint_templates import (
    COMPLAINT_STRUCTURE,
    cause_guidance,
)

_SYSTEM_PROMPT = """你是一名资深的中国民事诉讼律师，擅长起草规范的民事起诉状。
请根据用户提供的案件结构化信息、证据材料要点与法律依据，起草一份格式规范、要素齐全的民事起诉状。

要求：
1. 严格遵循民事起诉状的标准结构与书面语表述。
2. 诉讼请求应具体、明确、可执行；事实与理由应条理清晰并援引提供的法律条文。
3. 仅依据用户提供的信息撰写，信息缺失处以【】占位提示补充，不得编造当事人信息或证据。
4. 直接输出起诉状正文（Markdown 格式），不要输出额外说明。"""


def _format_parties(parties: list[dict], role: str) -> str:
    if not parties:
        return f"{role}：【待补充】"
    lines = []
    for i, p in enumerate(parties, start=1):
        prefix = f"{role}{i}" if len(parties) > 1 else role
        parts = [
            f"姓名/名称：{p.get('name') or '【待补充】'}",
            f"身份证号/统一社会信用代码：{p.get('id_card') or '【待补充】'}",
            f"住所：{p.get('address') or '【待补充】'}",
            f"联系方式：{p.get('phone') or '【待补充】'}",
        ]
        lines.append(f"{prefix}——" + "；".join(parts))
    return "\n".join(lines)


def _format_evidences(evidences: list[dict]) -> str:
    if not evidences:
        return "（暂无证据材料）"
    lines = []
    for i, e in enumerate(evidences, start=1):
        extracted = e.get("extracted") or {}
        summary = extracted.get("summary") or ""
        detail = []
        if extracted.get("amounts"):
            detail.append("金额：" + "、".join(extracted["amounts"]))
        if extracted.get("dates"):
            detail.append("日期：" + "、".join(extracted["dates"]))
        detail_str = f"（{'；'.join(detail)}）" if detail else ""
        lines.append(
            f"{i}. {e.get('name') or e.get('filename')}（{e.get('category', '书证')}）：{summary}{detail_str}"
        )
    return "\n".join(lines)


def _format_laws(laws: list[dict]) -> str:
    if not laws:
        return "（未匹配到推荐法条，请依据案情援引相关法律）"
    return "\n".join(
        f"- 《{law['law']}》{law['article']}：{law['summary']}" for law in laws
    )


def build_prompt(
    case: dict, evidences: list[dict], laws: list[dict], kb_contexts: list[dict] | None = None
) -> str:
    """组装用户消息。"""
    cause = case.get("cause") or "民事纠纷"
    kb_block = ""
    if kb_contexts:
        refs = "\n".join(
            f"- （{c['kb_name']}/{c['filename']}）{c['content'][:150]}" for c in kb_contexts
        )
        kb_block = f"\n\n【知识库检索到的补充参考】\n{refs}"

    return f"""{COMPLAINT_STRUCTURE}

【本案案由】{cause}

【当事人信息】
{_format_parties(case.get('plaintiffs') or [], '原告')}
{_format_parties(case.get('defendants') or [], '被告')}

【原告的诉讼请求（用户填写）】
{case.get('claims') or '【待补充】'}

【事实与理由（用户填写）】
{case.get('facts') or '【待补充】'}

【致送法院】
{case.get('court') or '【待补充】'}

【证据材料及要点】
{_format_evidences(evidences)}

【推荐援引的法律依据】
{_format_laws(laws)}

【本案由诉讼请求写作指引】
{cause_guidance(cause)}{kb_block}

请据此起草规范的民事起诉状。"""


async def generate_stream(
    case: dict,
    evidences: list[dict],
    laws: list[dict],
    kb_contexts: list[dict] | None = None,
    model: str = "qwen-max",
) -> AsyncGenerator[str, None]:
    """流式生成起诉状正文。"""
    prompt = build_prompt(case, evidences, laws, kb_contexts)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    async for delta in llm.stream_chat(
        messages, model=model, temperature=0.4, top_p=0.8, max_tokens=4096
    ):
        yield delta
