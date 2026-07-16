/**
 * 证据核对状态判断。
 *
 * OCR 抽取的关键信息在人工核对前标记"待确认"；
 * 保存修正时前端在 extracted 中写入 confirmed: true。
 */

/**
 * @param {object} evidence EvidenceOut（含 ocr_status 与 extracted）
 * @returns {'unconfirmed'|'confirmed'|null} 非 done 状态返回 null（无核对概念）
 */
export function confirmState(evidence) {
  if (!evidence || evidence.ocr_status !== 'done') return null
  return evidence.extracted?.confirmed ? 'confirmed' : 'unconfirmed'
}
