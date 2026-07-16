/**
 * 密码强度评估（注册页强度条）。
 *
 * 规则硬编码，保持确定性：
 * - 长度 < 6：弱
 * - 字符类别（小写/大写/数字/符号）仅 1 类：弱
 * - 2 类：中
 * - ≥3 类：强
 */
const LEVEL_LABELS = ['', '弱', '中', '强']

/**
 * @param {string} password
 * @returns {{ level: 0|1|2|3, label: string }} level 0 表示空密码（不展示强度条）
 */
export function scorePassword(password) {
  if (!password) return { level: 0, label: LEVEL_LABELS[0] }

  const classes = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^a-zA-Z0-9]/].filter((re) =>
    re.test(password)
  ).length

  let level
  if (password.length < 6 || classes <= 1) level = 1
  else if (classes === 2) level = 2
  else level = 3

  return { level, label: LEVEL_LABELS[level] }
}
