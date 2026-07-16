import http from './index'

// 知识库相关接口
export const kbApi = {
  createKb(payload) {
    return http.post('/api/kb', payload)
  },
  listKb() {
    return http.get('/api/kb')
  },
  deleteKb(kbId) {
    return http.delete(`/api/kb/${kbId}`)
  },
  uploadDocument(kbId, file, chunkSize, chunkOverlap) {
    const form = new FormData()
    form.append('file', file)
    form.append('chunk_size', chunkSize)
    form.append('chunk_overlap', chunkOverlap)
    return http.post(`/api/kb/${kbId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  previewChunks(file, chunkSize, chunkOverlap) {
    const form = new FormData()
    form.append('file', file)
    form.append('chunk_size', chunkSize)
    form.append('chunk_overlap', chunkOverlap)
    return http.post('/api/kb/preview-chunks', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  listDocuments(kbId) {
    return http.get(`/api/kb/${kbId}/documents`)
  },
  deleteDocument(docId) {
    return http.delete(`/api/kb/documents/${docId}`)
  },
  listChunks(docId, page, pageSize) {
    return http.get(`/api/kb/documents/${docId}/chunks`, {
      params: { page, page_size: pageSize },
    })
  },
  updateChunk(chunkId, content) {
    return http.put(`/api/kb/chunks/${chunkId}`, { content })
  },
  deleteChunk(chunkId) {
    return http.delete(`/api/kb/chunks/${chunkId}`)
  },
}
