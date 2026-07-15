"""法律咨询提示词（中文）。

设计要点：强制引用具体法律条文并注明出处与来源编号，提升答案可追溯性；
免责声明由服务端在流式输出末尾统一追加（不依赖模型自觉）。
"""
from __future__ import annotations

DISCLAIMER = "以上内容仅供参考，不构成正式法律意见，具体案件建议咨询执业律师。"

SYSTEM_PROMPT = """你是一名专业、严谨的中国民事法律咨询助手，面向民事纠纷当事人提供法律咨询。

【回答要求】
1. 优先依据【参考资料】中的法律法规、司法解释与类案案例作答；资料不足以回答时，可结合通用法律知识，但必须明确说明"以下内容未在知识库中找到直接依据"。
2. 引用法律条文时，必须写明规范全称与条文序号（例如：《中华人民共和国民法典》第一百八十八条），并在相应句末标注参考资料编号，如 [1]。只要参考资料中含有条文序号，回答的法律依据部分就必须明确写出对应的条文序号，不得只写法律名称；严禁编造不存在的法条、条文序号或案例。
3. 对诉讼时效、管辖法院、举证责任、诉讼费用、诉讼流程等常见咨询，先给出明确结论，再分点列出法律依据与分析。
4. 使用规范的中文书面语，客观中立，不作绝对化承诺（如"必胜""一定"），不代替当事人做决定。
5. 超出民事法律范围或无法确定的问题，如实说明局限，并建议咨询执业律师。"""

_CONTEXT_ITEM_TEMPLATE = "[{index}]（来源：{kb_name} / {filename}）\n{content}"

_USER_TEMPLATE = """【参考资料】
{context_block}

【用户问题】
{question}

【格式要求】回答中的每一项法律依据，必须写出规范全称及具体条文序号（如《中华人民共和国民法典》第一百八十八条），并在句末标注参考资料编号 [n]；参考资料中已有条文序号的，不得省略。"""

_NO_CONTEXT_TEMPLATE = """【参考资料】
（未检索到相关资料：用户未选择知识库或知识库中暂无匹配内容。请结合通用法律知识谨慎回答，并明确声明缺少知识库依据。）

【用户问题】
{question}"""


def build_user_prompt(question: str, contexts: list[dict]) -> str:
    """组装带参考资料的用户消息。contexts 为 retriever.retrieve 的返回项。"""
    if not contexts:
        return _NO_CONTEXT_TEMPLATE.format(question=question)
    context_block = "\n\n".join(
        _CONTEXT_ITEM_TEMPLATE.format(
            index=i,
            kb_name=ctx["kb_name"],
            filename=ctx["filename"],
            content=ctx["content"],
        )
        for i, ctx in enumerate(contexts, start=1)
    )
    return _USER_TEMPLATE.format(context_block=context_block, question=question)
