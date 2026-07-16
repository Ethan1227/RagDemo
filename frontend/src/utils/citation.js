/**
 * 引用角标渲染工具。
 *
 * AI 回答中的引用标记形如 [1]、[2]（由后端提示词约束输出，见
 * backend/app/services/prompts.py），本模块将其转换为可点击的
 * <sup class="citation-ref"> 角标，供溯源面板定位来源。
 */
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 引用编号最多支持 3 位数，避免误伤正文中的长数字方括号
const CITATION_PATTERN = /\[(\d{1,3})\]/g

/**
 * 在已消毒的 HTML 中将 [n] 替换为角标标签（纯字符串函数，便于单测）。
 * 仅当 1 <= n <= total 时替换，越界编号原样保留。
 *
 * @param {string} html 已经过 DOMPurify 消毒的 HTML
 * @param {number} total 引用来源总数
 * @returns {string}
 */
export function injectCitationRefs(html, total) {
  if (!html || !total || total < 1) return html || ''
  return html.replace(CITATION_PATTERN, (match, num) => {
    const index = Number(num)
    if (index < 1 || index > total) return match
    return `<sup class="citation-ref" data-index="${index}" role="button" title="查看引用来源 [${index}]">${index}</sup>`
  })
}

/**
 * 渲染 AI 回答：markdown → 消毒 → 注入引用角标。
 * 先消毒后注入：注入内容仅含受控的数字属性，不存在 XSS 面。
 *
 * @param {string} text markdown 原文
 * @param {Array} citations 引用来源列表（长度决定合法编号范围）
 * @returns {string} 可直接 v-html 的 HTML
 */
export function renderWithCitations(text, citations = []) {
  const html = DOMPurify.sanitize(marked.parse(text || ''))
  return injectCitationRefs(html, citations.length)
}
