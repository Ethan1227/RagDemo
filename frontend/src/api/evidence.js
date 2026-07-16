import http from './index'

// 证据材料相关接口
export const evidenceApi = {
  listCategories() {
    return http.get('/api/evidence/categories')
  },
  upload(file, category, name, caseId) {
    const form = new FormData()
    form.append('file', file)
    form.append('category', category)
    if (name) form.append('name', name)
    if (caseId != null) form.append('case_id', caseId)
    return http.post('/api/evidence', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list(caseId) {
    return http.get('/api/evidence', { params: caseId != null ? { case_id: caseId } : {} })
  },
  get(id) {
    return http.get(`/api/evidence/${id}`)
  },
  update(id, payload) {
    return http.put(`/api/evidence/${id}`, payload)
  },
  remove(id) {
    return http.delete(`/api/evidence/${id}`)
  },
}
