import http from './index'

// 认证相关接口
export const authApi = {
  getCaptcha() {
    return http.get('/api/auth/captcha')
  },
  register(payload) {
    return http.post('/api/auth/register', payload)
  },
  login(payload) {
    return http.post('/api/auth/login', payload)
  },
  me() {
    return http.get('/api/auth/me')
  },
}
