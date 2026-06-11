import request from './index'

// 上传文件
export function uploadFile(data) {
  return request.post('/etl/upload', data)
}

// 执行 ETL 任务（file_ids 作为 JSON body 传入）
export function executeEtlTask(fileIds) {
  return request.post('/etl/execute', fileIds)
}

// 获取任务状态
export function getTaskStatus(taskId) {
  return request.get(`/etl/status/${taskId}`)
}

// 获取文件列表
export function getFileList(params) {
  return request.get('/etl/files', { params })
}

// 删除文件
export function deleteFile(fileId) {
  return request.delete(`/etl/files/${fileId}`)
}

// 预览数据
export function previewData(data) {
  return request.post('/etl/preview', data)
}

// 获取数据库连接状态（含 STG 表信息）
export function getDbStatus() {
  return request.get('/etl/db-status')
}

// 预览 STG 表数据
export function previewStgTable(tableKey, maxRows = 100) {
  return request.get(`/etl/stg-preview/${tableKey}`, { params: { max_rows: maxRows } })
}
