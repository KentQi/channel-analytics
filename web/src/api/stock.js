import request from './index'

// 获取库存 KPI（7 个指标）
export function getStockKpis(params) {
  return request.get('/stock/kpis', { params })
}

// 帕累托分析
export function getParetoAnalysis(params) {
  return request.get('/stock/pareto', { params })
}

// 批次分析
export function getBatchAnalysis(params) {
  return request.get('/stock/batch-analysis', { params })
}

// 效期状态分布
export function getExpiryStatus(params) {
  return request.get('/stock/expiry-status', { params })
}

// 效期×周转矩阵
export function getExpiryTurnoverMatrix(params) {
  return request.get('/stock/expiry-turnover-matrix', { params })
}

// 不动销分析
export function getNoSalesData(params) {
  return request.get('/stock/no-sales', { params })
}

// 库存汇总
export function getStockSummary(params) {
  return request.get('/stock/summary', { params })
}

// 周转状态分布
export function getTurnoverStatus(params) {
  return request.get('/stock/turnover-status', { params })
}

// 通用报表查询
export function getReportTable(tableName) {
  return request.get(`/stock/report/${tableName}`)
}
