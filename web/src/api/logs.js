import request from './index'

// 查询安全日志
export function getAuditLogs(params) {
  return request.get('/logs/audit', { params })
}

// 查询业务日志
export function getBusinessLogs(params) {
  return request.get('/logs/business', { params })
}

// 查询错误日志
export function getErrorLogs(params) {
  return request.get('/logs/error', { params })
}
