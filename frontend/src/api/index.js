import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 统一 axios 实例：注入 token、统一错误处理
const http = axios.create({
  baseURL: '/',
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail

    if (status === 401) {
      // 登录失效：清理并跳转登录页
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      if (router.currentRoute.value.name !== 'login') {
        ElMessage.warning('登录已失效，请重新登录')
        router.push({ name: 'login' })
      }
    } else if (Array.isArray(detail)) {
      // FastAPI 校验错误（422）
      ElMessage.error(detail[0]?.msg || '请求参数有误')
    } else if (detail) {
      ElMessage.error(detail)
    } else {
      ElMessage.error(error.message || '网络请求失败')
    }
    return Promise.reject(error)
  },
)

export default http
