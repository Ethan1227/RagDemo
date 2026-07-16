/**
 * formatClock 时间格式化单元测试。
 */
import { describe, expect, it } from 'vitest'
import { formatClock } from '../src/utils/format'

describe('formatClock', () => {
  it('格式化为 HH:mm，个位补零', () => {
    expect(formatClock(new Date(2026, 6, 16, 9, 5))).toBe('09:05')
    expect(formatClock(new Date(2026, 6, 16, 14, 30))).toBe('14:30')
  })

  it('午夜与临界时间', () => {
    expect(formatClock(new Date(2026, 6, 16, 0, 0))).toBe('00:00')
    expect(formatClock(new Date(2026, 6, 16, 23, 59))).toBe('23:59')
  })

  it('非 Date 或无效 Date 返回空串', () => {
    expect(formatClock(null)).toBe('')
    expect(formatClock(undefined)).toBe('')
    expect(formatClock('2026-07-16')).toBe('')
    expect(formatClock(new Date('invalid'))).toBe('')
  })
})
