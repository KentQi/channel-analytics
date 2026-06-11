import request from './index'

// 调度器状态
export function getRpaStatus() {
  return request.get('/rpa/status')
}

// 统计信息
export function getRpaStats() {
  return request.get('/rpa/stats')
}

// 支持的模块列表
export function getRpaModules() {
  return request.get('/rpa/modules')
}

// 任务 CRUD
export function getRpaTasks() {
  return request.get('/rpa/tasks')
}

export function getRpaTask(id) {
  return request.get(`/rpa/tasks/${id}`)
}

export function createRpaTask(data) {
  return request.post('/rpa/tasks', data)
}

export function updateRpaTask(id, data) {
  return request.put(`/rpa/tasks/${id}`, data)
}

export function deleteRpaTask(id) {
  return request.delete(`/rpa/tasks/${id}`)
}

export function toggleRpaTask(id) {
  return request.post(`/rpa/tasks/${id}/toggle`)
}

// 执行日志
export function getRpaLogs(params = {}) {
  return request.get('/rpa/logs', { params })
}

// 测试连接
export function testRpaConnection(data) {
  return request.post('/rpa/test-connection', data)
}

// 手动触发单个任务
export function runRpaTask(id) {
  return request.post(`/rpa/tasks/${id}/run`)
}

// 临时采集：触发所有已启用任务
export function runAllRpaTasks() {
  return request.post('/rpa/run-all')
}

// 停止所有正在运行的采集
export function stopRpaTasks() {
  return request.post('/rpa/stop')
}

// 登录配置
export function getRpaLoginConfig() {
  return request.get('/rpa/login-config')
}

export function updateRpaLoginConfig(data) {
  return request.put('/rpa/login-config', data)
}

// 邮件通知配置
export function getRpaEmailConfig() {
  return request.get('/rpa/email-config')
}

export function updateRpaEmailConfig(data) {
  return request.put('/rpa/email-config', data)
}
