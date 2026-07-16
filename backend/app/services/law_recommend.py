"""案由 → 核心法条静态推荐。

内置 8 个常见民事案由的核心法律依据（硬编码，确定性输出）。
可选传入 kb_ids 时，用知识库检索补充参考条文（阶段2 retriever）。
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

# 支持的案由及其核心法条（法律全称 + 条文号 + 要旨）
CAUSE_LAWS: dict[str, list[dict]] = {
    "民间借贷纠纷": [
        {"law": "中华人民共和国民法典", "article": "第六百六十七条", "summary": "借款合同是借款人向贷款人借款，到期返还借款并支付利息的合同。"},
        {"law": "中华人民共和国民法典", "article": "第六百七十五条", "summary": "借款人应当按照约定的期限返还借款。"},
        {"law": "中华人民共和国民法典", "article": "第六百八十条", "summary": "禁止高利放贷，借款利率不得违反国家有关规定。"},
        {"law": "中华人民共和国民法典", "article": "第一百八十八条", "summary": "向人民法院请求保护民事权利的诉讼时效期间为三年。"},
    ],
    "买卖合同纠纷": [
        {"law": "中华人民共和国民法典", "article": "第五百九十五条", "summary": "买卖合同是出卖人转移标的物所有权于买受人，买受人支付价款的合同。"},
        {"law": "中华人民共和国民法典", "article": "第六百二十六条", "summary": "买受人应当按照约定的数额和方式支付价款。"},
        {"law": "中华人民共和国民法典", "article": "第五百七十七条", "summary": "当事人一方不履行合同义务或者履行不符合约定的，应当承担违约责任。"},
    ],
    "租赁合同纠纷": [
        {"law": "中华人民共和国民法典", "article": "第七百零三条", "summary": "租赁合同是出租人将租赁物交付承租人使用、收益，承租人支付租金的合同。"},
        {"law": "中华人民共和国民法典", "article": "第七百二十一条", "summary": "承租人应当按照约定的期限支付租金。"},
        {"law": "中华人民共和国民法典", "article": "第七百二十二条", "summary": "承租人无正当理由未支付或者迟延支付租金的，出租人可以请求支付并可解除合同。"},
    ],
    "劳动争议": [
        {"law": "中华人民共和国劳动合同法", "article": "第三十条", "summary": "用人单位应当按照约定和国家规定，及时足额支付劳动报酬。"},
        {"law": "中华人民共和国劳动合同法", "article": "第四十七条", "summary": "经济补偿按劳动者在本单位工作年限，每满一年支付一个月工资的标准支付。"},
        {"law": "中华人民共和国劳动争议调解仲裁法", "article": "第二条", "summary": "劳动报酬、工伤医疗费、经济补偿等争议适用本法。"},
    ],
    "机动车交通事故责任纠纷": [
        {"law": "中华人民共和国民法典", "article": "第一千二百一十三条", "summary": "机动车交通事故造成损害，先由保险人在强制保险责任限额内赔偿。"},
        {"law": "中华人民共和国民法典", "article": "第一千一百七十九条", "summary": "侵害他人造成人身损害的，应当赔偿医疗费、护理费、误工费等费用。"},
        {"law": "中华人民共和国道路交通安全法", "article": "第七十六条", "summary": "机动车发生交通事故造成损害的赔偿责任划分规则。"},
    ],
    "离婚纠纷": [
        {"law": "中华人民共和国民法典", "article": "第一千零七十九条", "summary": "夫妻感情确已破裂，调解无效的，应当准予离婚。"},
        {"law": "中华人民共和国民法典", "article": "第一千零八十七条", "summary": "离婚时夫妻共同财产由双方协议处理，协议不成由人民法院判决。"},
        {"law": "中华人民共和国民法典", "article": "第一千零八十四条", "summary": "离婚后子女抚养权的确定以最有利于未成年子女为原则。"},
    ],
    "人身损害赔偿纠纷": [
        {"law": "中华人民共和国民法典", "article": "第一千一百六十五条", "summary": "行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。"},
        {"law": "中华人民共和国民法典", "article": "第一千一百七十九条", "summary": "侵害他人造成人身损害应赔偿医疗费、误工费等；造成残疾的还应赔偿残疾赔偿金。"},
    ],
    "物业服务合同纠纷": [
        {"law": "中华人民共和国民法典", "article": "第九百三十七条", "summary": "物业服务合同是物业服务人提供物业服务，业主支付物业费的合同。"},
        {"law": "中华人民共和国民法典", "article": "第九百四十四条", "summary": "业主应当按照约定向物业服务人支付物业费。"},
    ],
}


def list_causes() -> list[str]:
    """返回支持的案由列表。"""
    return list(CAUSE_LAWS.keys())


def recommend_by_cause(cause: str) -> list[dict]:
    """按案由返回核心法条（未知案由返回空列表）。"""
    return CAUSE_LAWS.get(cause, [])


async def recommend(
    cause: str, db: AsyncSession | None = None, kb_ids: list[int] | None = None
) -> list[dict]:
    """推荐法条：静态映射 + 可选知识库检索补充。"""
    items = list(recommend_by_cause(cause))
    if db is not None and kb_ids:
        from backend.app.services import retriever

        try:
            hits = await retriever.retrieve(db, cause, kb_ids, top_k=3)
            for h in hits:
                items.append(
                    {"law": h["filename"], "article": "知识库检索", "summary": h["content"][:100]}
                )
        except Exception:  # 检索失败不影响静态推荐
            pass
    return items
