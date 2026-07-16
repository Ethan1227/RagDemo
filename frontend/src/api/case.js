import http from './index'

// 案件信息相关接口
export const caseApi = {
  listCauses() {
    return http.get('/api/cases/causes')
  },
  recommendLaw(cause) {
    return http.get('/api/cases/law-recommend', { params: { cause } })
  },
  create(title) {
    return http.post('/api/cases', { title })
  },
  list() {
    return http.get('/api/cases')
  },
  get(caseId) {
    return http.get(`/api/cases/${caseId}`)
  },
  update(caseId, payload) {
    return http.put(`/api/cases/${caseId}`, payload)
  },
  remove(caseId) {
    return http.delete(`/api/cases/${caseId}`)
  },
}
