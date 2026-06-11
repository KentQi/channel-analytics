import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, getMe } from '@/api/auth'

const AUTH_KEY = 'auth_token'
const ROLE_KEY = 'auth_role'
const MODULES_KEY = 'auth_modules'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(AUTH_KEY) || '')
  const username = ref(localStorage.getItem('auth_username') || '')
  const displayName = ref(localStorage.getItem('auth_display_name') || '')
  const role = ref(localStorage.getItem(ROLE_KEY) || '')
  const userId = ref(localStorage.getItem('auth_user_id') || null)
  // 菜单模块权限：null = 不限制（admin/创建人），[] = 啥都不能看
  const modules = ref(JSON.parse(localStorage.getItem(MODULES_KEY) || 'null'))

  const isAuthenticated = computed(() => !!token.value)
  // null = 不限制（admin/创建人），其他 role 严格按列表过滤
  const isAdmin = computed(() => ['admin', '创建人'].includes(role.value))
  const hasModule = (moduleName) => {
    if (isAdmin.value) return true
    if (modules.value === null) return true
    return Array.isArray(modules.value) && modules.value.includes(moduleName)
  }

  function setAuth(data) {
    token.value = data.token || data.access_token || ''
    username.value = data.username || ''
    displayName.value = data.display_name || data.displayName || data.username || ''
    role.value = data.role || ''
    userId.value = data.user_id || data.userId || null
    modules.value = data.modules === undefined ? null : data.modules

    if (token.value) {
      localStorage.setItem(AUTH_KEY, token.value)
      localStorage.setItem('auth_username', username.value)
      localStorage.setItem('auth_display_name', displayName.value)
      localStorage.setItem(ROLE_KEY, role.value)
      localStorage.setItem('auth_user_id', userId.value || '')
      localStorage.setItem(MODULES_KEY, JSON.stringify(modules.value))
    }
  }

  function clearAuth() {
    token.value = ''
    username.value = ''
    displayName.value = ''
    role.value = ''
    userId.value = null
    modules.value = null
    localStorage.removeItem(AUTH_KEY)
    localStorage.removeItem('auth_username')
    localStorage.removeItem('auth_display_name')
    localStorage.removeItem(ROLE_KEY)
    localStorage.removeItem('auth_user_id')
    localStorage.removeItem(MODULES_KEY)
  }

  async function login(username, password) {
    const response = await apiLogin(username, password)
    setAuth(response.data)
    return response
  }

  // 初始化：从服务器获取用户信息（如果本地有token）
  async function initAuth() {
    if (!token.value) return
    try {
      const response = await getMe()
      const data = response.data
      // 兼容：role_permissions 字典 或 直接的 modules 字段
      const perms = data.role_permissions || data
      setAuth({
        token: token.value,
        username: data.username,
        display_name: data.display_name,
        role: data.role,
        user_id: data.id,
        modules: perms.modules
      })
    } catch (e) {
      // token 失效，清除认证状态
      clearAuth()
    }
  }

  function logout() {
    clearAuth()
  }

  return {
    token,
    username,
    displayName,
    role,
    userId,
    modules,
    isAuthenticated,
    isAdmin,
    hasModule,
    login,
    logout,
    initAuth
  }
})
