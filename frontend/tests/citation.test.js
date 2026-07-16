/**
 * citation.js 引用角标渲染函数单元测试。
 *
 * 测试 injectCitationRefs（纯字符串，无 DOM 依赖）和
 * renderWithCitations（使用 marked + DOMPurify，需要 jsdom 环境）。
 */
import { describe, expect, it } from 'vitest'
import { injectCitationRefs, renderWithCitations } from '../src/utils/citation'

// ========================= injectCitationRefs =========================

describe('injectCitationRefs', () => {
  it('将范围内的 [n] 替换为 sup 角标', () => {
    const input = '根据《民法典》第一百八十八条[1]'
    const result = injectCitationRefs(input, 3)
    expect(result).toContain('<sup class="citation-ref" data-index="1"')
    // [1] 被替换为角标，角标内容不含方括号（title 属性中的 [1] 不影响判断）
    expect(result).toContain('>1</sup>')
  })

  it('越界编号（如 [99] 超出总数 3）原样保留', () => {
    const input = '请参见[99]以及正文。'
    const result = injectCitationRefs(input, 3)
    expect(result).toContain('[99]')
    expect(result).not.toContain('citation-ref')
  })

  it('编号 0 不匹配', () => {
    const input = '请参见[0]'
    const result = injectCitationRefs(input, 5)
    // [0] is not a positive index, should stay as-is
    expect(result).toContain('[0]')
  })

  it('长度为 0 时不做任何替换', () => {
    const input = '根据[1]和[2]'
    const result = injectCitationRefs(input, 0)
    expect(result).toBe(input)
  })

  it('空字符串直接返回空', () => {
    expect(injectCitationRefs('', 3)).toBe('')
  })

  it('null/undefined 安全返回空串', () => {
    expect(injectCitationRefs(null, 3)).toBe('')
    expect(injectCitationRefs(undefined, 5)).toBe('')
  })

  it('多个角标全部替换', () => {
    const result = injectCitationRefs('参见[1][2][3]', 3)
    const count = (result.match(/citation-ref/g) || []).length
    expect(count).toBe(3)
  })

  it('超过 3 位数的方括号忽略不替换', () => {
    const input = '[9999]不是合法角标'
    const result = injectCitationRefs(input, 10)
    expect(result).toContain('[9999]')
    expect(result).not.toContain('citation-ref')
  })

  it('data-index 属性值为对应的引用编号', () => {
    const result = injectCitationRefs('[1][3][2]', 3)
    // 每个角标的 data-index 值对应该编号
    expect(result).toContain('data-index="1"')
    expect(result).toContain('data-index="3"')
    expect(result).toContain('data-index="2"')
  })
})

// ========================= renderWithCitations =========================

describe('renderWithCitations', () => {
  it('渲染 markdown 并注入引用角标', () => {
    const text = '根据《民法典》第一百八十八条[1]，诉讼时效期间为三年。'
    const citations = [
      { index: 1, kb_name: '法律法规库', filename: '民法典.txt', score: 0.95, snippet: '诉讼时效期间为三年。' },
    ]
    const html = renderWithCitations(text, citations)
    expect(html).toContain('citation-ref')
    expect(html).toContain('data-index="1"')
  })

  it('citations 为空数组时 [n] 原样保留', () => {
    const text = '参见[1]相关条文。'
    const html = renderWithCitations(text, [])
    expect(html).toContain('[1]')
    expect(html).not.toContain('citation-ref')
  })

  it('citations 为 undefined 安全处理', () => {
    const text = '参见[1]相关条文。'
    const html = renderWithCitations(text, undefined)
    expect(html).toContain('[1]')
    expect(html).not.toContain('citation-ref')
  })

  it('XSS 注入被 DOMPurify 消毒', () => {
    const text = '<script>alert("xss")</script>正常文本'
    const citations = [{ index: 1, kb_name: 'x', filename: 'x', score: 0.5, snippet: 'x' }]
    const html = renderWithCitations(text, citations)
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('alert')
    expect(html).toContain('正常文本')
  })

  it('空文本安全返回', () => {
    const html = renderWithCitations('', [])
    expect(typeof html).toBe('string')
  })

  it('null/undefined 文本安全返回', () => {
    expect(typeof renderWithCitations(null, [])).toBe('string')
    expect(typeof renderWithCitations(undefined, [])).toBe('string')
  })
})
