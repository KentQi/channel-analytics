import axios from 'axios'

// Create axios instance with interceptor configuration
const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// Copy intercepters from main axios
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

const BASE_URL = '/reports'

// Tables API
export function getAvailableTables() {
  return request.get(`${BASE_URL}/tables`)
}

export function getTableFields(tableName) {
  return request.get(`${BASE_URL}/tables/${tableName}/fields`)
}

// Preview API
export function previewReport(data) {
  return request.post(`${BASE_URL}/preview`, data)
}

// Template CRUD
export function getReports() {
  return request.get(BASE_URL)
}

export function getReport(templateId) {
  return request.get(`${BASE_URL}/${templateId}`)
}

export function createReport(data) {
  return request.post(BASE_URL, data)
}

export function updateReport(templateId, data) {
  return request.put(`${BASE_URL}/${templateId}`, data)
}

export function deleteReport(templateId) {
  return request.delete(`${BASE_URL}/${templateId}`)
}

// Execute/Export
export function executeReport(templateId, params = {}) {
  return request.post(`${BASE_URL}/${templateId}/execute`, params)
}

export function exportReport(templateId, params = {}) {
  return request.post(`${BASE_URL}/${templateId}/export`, params)
}

// Share
export function shareReport(templateId, data) {
  return request.post(`${BASE_URL}/${templateId}/share`, data)
}