/**
 * 时间格式化工具。
 */

/**
 * 格式化为 HH:mm 时钟串（用于"草稿已自动保存于 xx:xx"提示）。
 * @param {Date} date
 * @returns {string}
 */
export function formatClock(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return ''
  const h = String(date.getHours()).padStart(2, '0')
  const m = String(date.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}
