import axios from '@/api/index'

const BASE_URL = '/alerts'

// Alert Rules API
export function getAlertRules(params = {}) {
  return axios.get(`${BASE_URL}/rules`, { params })
}

export function getAlertRule(ruleId) {
  return axios.get(`${BASE_URL}/rules/${ruleId}`)
}

export function createAlertRule(data) {
  return axios.post(`${BASE_URL}/rules`, data)
}

export function updateAlertRule(ruleId, data) {
  return axios.put(`${BASE_URL}/rules/${ruleId}`, data)
}

export function deleteAlertRule(ruleId) {
  return axios.delete(`${BASE_URL}/rules/${ruleId}`)
}

export function testAlertRule(ruleId) {
  return axios.post(`${BASE_URL}/rules/${ruleId}/test`)
}

// Alert History API
export function getAlertHistory(params = {}) {
  return axios.get(`${BASE_URL}/history`, { params })
}

export function acknowledgeAlert(historyId, acknowledgedBy) {
  return axios.post(`${BASE_URL}/history/${historyId}/ack`, { acknowledged_by: acknowledgedBy })
}

// Notifications API
export function getNotifications(params = {}) {
  return axios.get(`${BASE_URL}/notifications`, { params })
}

export function markNotificationRead(notificationId) {
  return axios.post(`${BASE_URL}/notifications/${notificationId}/read`)
}

// Stats API
export function getAlertStats() {
  return axios.get(`${BASE_URL}/stats`)
}
