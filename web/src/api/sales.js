import request from './index'

// 获取销售分析筛选选项
export function getSalesFilterOptions() {
  return request.get('/sales/filter-options')
}

// 获取销售出库宽表数据
export function getSalesWideTable(params) {
  return request.get('/sales/wide-table', { params })
}

// 获取出货仪表盘数据
export function getSalesDashboard(params) {
  return request.get('/sales/dashboard', { params })
}

// 获取指标达成进度
export function getSalesIndicatorProgress(params) {
  return request.get('/sales/indicator-progress', { params })
}

// 获取销售出库明细
export function getSalesDetail(params) {
  return request.get('/sales/sales-detail', { params })
}

// 获取单品货流明细
export function getProductFlow(params) {
  return request.get('/sales/product-flow', { params })
}

// 获取明星商品 TOP N
export function getStarProducts(params) {
  return request.get('/sales/star-products', { params })
}

// 获取客户分层数据
export function getCustomerTier(params) {
  return request.get('/sales/customer-tier', { params })
}

// 获取品类分布
export function getCategoryDistribution(params) {
  return request.get('/sales/category-distribution', { params })
}

// 获取主推品渗透
export function getPromotedPenetration(params) {
  return request.get('/sales/promoted-penetration', { params })
}

// 获取渠道分析（别名，调用主推品渗透接口）
export function getChannelAnalysis(params) {
  return request.get('/sales/promoted-penetration', { params })
}

// 兼容别名
export const getSalesTable = getSalesWideTable
export const getSalesIndicator = getSalesIndicatorProgress
export const getSalesRanking = getStarProducts
