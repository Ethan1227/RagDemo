import http from './index'

// 起诉状相关接口
export const complaintApi = {
  list(caseId) {
    return http.get('/api/complaints', { params: caseId != null ? { case_id: caseId } : {} })
  },
  get(id) {
    return http.get(`/api/complaints/${id}`)
  },
  update(id, content) {
    return http.put(`/api/complaints/${id}`, { content })
  },
  remove(id) {
    return http.delete(`/api/complaints/${id}`)
  },
  exportDocxUrl(id) {
    return `/api/complaints/${id}/export/docx`
  },
}

/**
 * 流式生成起诉状（fetch + ReadableStream，复用 chat 的 SSE 模式）。
 * handlers: { onLaws, onDelta, onDone, onError }
 */
export async function streamGenerate(caseId, kbIds, handlers) {
  const token = localStorage.getItem('access_token')
  const resp = await fetch('/api/complaints/generate/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ case_id: caseId, kb_ids: kbIds || [] }),
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
    const parts = buffer.split('\n\n')
    buffer = parts.pop()
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data: ')) continue
      const event = JSON.parse(line.slice(6))
      if (event.type === 'laws') handlers.onLaws?.(event.laws)
      else if (event.type === 'delta') handlers.onDelta?.(event.content)
      else if (event.type === 'done') handlers.onDone?.(event)
      else if (event.type === 'error') handlers.onError?.(event.detail)
    }
  }
}
