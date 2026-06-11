import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      const { status, data, config } = error.response

      // 登录接口返回 403 时，显示具体错误信息，不跳转
      if (config?.url?.includes('/auth/login') && status === 403) {
        ElMessage.error(data?.detail || '用户名或密码错误')
        return Promise.reject(error)
      }

      switch (status) {
        case 401:
          localStorage.removeItem('auth_token')
          ElMessage.error('登录已过期，请重新登录')
          router.push({ name: 'Login' })
          break
        case 403:
          ElMessage.error(data?.detail || data?.message || '您没有权限执行此操作')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误，请稍后重试')
          break
        default:
          if (data?.detail || data?.message) {
            ElMessage.error(data.detail || data.message)
          }
      }
    } else if (error.request) {
      ElMessage.error('网络连接失败，请检查网络')
    } else {
      ElMessage.error('请求配置错误')
    }
    return Promise.reject(error)
  }
)

export default request
