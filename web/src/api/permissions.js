import request from './index'

// ========== 角色权限管理 ==========
// 获取所有角色及其权限配置
export function getRoles() {
  return request.get('/permissions/roles')
}

// 获取指定角色权限
export function getRolePermissions(role) {
  return request.get(`/permissions/roles/${role}`)
}

// 保存角色权限（三维权限）
export function saveRolePermissions(role, permissions, newRoleName = null) {
  const params = newRoleName ? { new_role_name: newRoleName } : {}
  return request.put(`/permissions/roles/${role}`, permissions, { params })
}

// 创建新角色
export function createRole(roleName) {
  return request.post('/permissions/roles', null, { params: { role: roleName } })
}

// 删除角色
export function deleteRole(role) {
  return request.delete(`/permissions/roles/${role}`)
}

// ========== 用户管理 ==========
// 获取用户列表
export function getUsers(params) {
  return request.get('/permissions/users', { params })
}

// 创建用户
export function createUser(data) {
  return request.post('/permissions/users', null, {
    params: {
      username: data.username,
      display_name: data.display_name,
      password: data.password,
      role: data.role
    }
  })
}

// 更新用户
export function updateUser(id, data) {
  return request.put(`/permissions/users/${id}`, data)
}

// 删除用户
export function deleteUser(id) {
  return request.delete(`/permissions/users/${id}`)
}

// ========== 区域数据 ==========
// 获取所有可用区域（从 rpt_sales_out_wide 动态获取）
export function getRegions() {
  return request.get('/permissions/regions')
}

// ========== 可用角色 ==========
// 获取系统中所有可用角色名
export function getAvailableRoles() {
  return request.get('/permissions/available-roles')
}
