import http from './index'

// 对话相关接口
export const chatApi = {
  createSession(name = '新对话') {
    return http.post('/api/chat/sessions', { name })
  },
  listSessions() {
    return http.get('/api/chat/sessions')
  },
  updateSession(sessionId, payload) {
    return http.put(`/api/chat/sessions/${sessionId}`, payload)
  },
  deleteSession(sessionId) {
    return http.delete(`/api/chat/sessions/${sessionId}`)
  },
  listMessages(sessionId) {
    return http.get(`/api/chat/sessions/${sessionId}/messages`)
  },
}

/**
 * SSE 流式问答（EventSource 不支持 POST，改用 fetch + ReadableStream）。
 *
 * @param {number} sessionId 会话 id
 * @param {string} question 用户问题
 * @param {object} handlers { onCitations, onDelta, onDone, onError }
 * @returns {Promise<void>} 流结束后 resolve
 */
export async function streamChat(sessionId, question, handlers) {
  const token = localStorage.getItem('access_token')
  const resp = await fetch(`/api/chat/sessions/${sessionId}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败（${resp.status}）`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // SSE 事件以空行分隔
    const parts = buffer.split('\n\n')
    buffer = parts.pop()
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data: ')) continue
      const event = JSON.parse(line.slice(6))
      if (event.type === 'citations') handlers.onCitations?.(event.citations)
      else if (event.type === 'delta') handlers.onDelta?.(event.content)
      else if (event.type === 'done') handlers.onDone?.(event)
      else if (event.type === 'error') handlers.onError?.(event.detail)
    }
  }
}
