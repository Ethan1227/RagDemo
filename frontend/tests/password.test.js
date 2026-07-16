/**
 * scorePassword 密码强度评估单元测试。
 * 规则：<6位或单一字符类=弱；2类=中；≥3类=强；空=level 0。
 */
import { describe, expect, it } from 'vitest'
import { scorePassword } from '../src/utils/password'

describe('scorePassword', () => {
  it('空密码返回 level 0（不展示强度条）', () => {
    expect(scorePassword('')).toEqual({ level: 0, label: '' })
    expect(scorePassword(null)).toEqual({ level: 0, label: '' })
    expect(scorePassword(undefined)).toEqual({ level: 0, label: '' })
  })

  it('长度不足 6 位为弱（即使多类字符）', () => {
    expect(scorePassword('aB1!')).toEqual({ level: 1, label: '弱' })
  })

  it('单一字符类为弱', () => {
    expect(scorePassword('abcdefgh')).toEqual({ level: 1, label: '弱' })
    expect(scorePassword('12345678')).toEqual({ level: 1, label: '弱' })
  })

  it('两类字符为中', () => {
    expect(scorePassword('abc12345')).toEqual({ level: 2, label: '中' })
    expect(scorePassword('Abcdefgh')).toEqual({ level: 2, label: '中' })
  })

  it('三类及以上字符为强', () => {
    expect(scorePassword('Abc12345')).toEqual({ level: 3, label: '强' })
    expect(scorePassword('Abc123!@')).toEqual({ level: 3, label: '强' })
  })

  it('中文等非字母数字字符计入符号类', () => {
    // 小写 + 数字 + 符号（中文）= 3 类 → 强
    expect(scorePassword('abc123密码')).toEqual({ level: 3, label: '强' })
  })
})
