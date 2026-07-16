/**
 * confirmState 证据核对状态单元测试。
 */
import { describe, expect, it } from 'vitest'
import { confirmState } from '../src/utils/evidence'

describe('confirmState', () => {
  it('OCR 完成且未核对 → unconfirmed（显示待确认标记）', () => {
    expect(confirmState({ ocr_status: 'done', extracted: { parties: [] } })).toBe('unconfirmed')
    expect(confirmState({ ocr_status: 'done', extracted: {} })).toBe('unconfirmed')
    expect(confirmState({ ocr_status: 'done' })).toBe('unconfirmed')
  })

  it('保存修正（confirmed: true）后 → confirmed', () => {
    expect(confirmState({ ocr_status: 'done', extracted: { confirmed: true } })).toBe('confirmed')
  })

  it('OCR 未完成/失败时无核对概念 → null', () => {
    expect(confirmState({ ocr_status: 'pending' })).toBe(null)
    expect(confirmState({ ocr_status: 'processing' })).toBe(null)
    expect(confirmState({ ocr_status: 'failed' })).toBe(null)
  })

  it('空入参安全返回 null', () => {
    expect(confirmState(null)).toBe(null)
    expect(confirmState(undefined)).toBe(null)
  })
})
