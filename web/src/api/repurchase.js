import request from './index'

// 获取客户留存热力图数据（cohort matrix）
export function getCohortMatrix(params) {
  return request.get('/repurchase/cohort-matrix', { params })
}

// 获取客户价值散点图数据
export function getCustomerValueScatter(params) {
  return request.get('/repurchase/customer-value', { params })
}

// 获取流失预警客户列表
export function getChurnWarning(params) {
  return request.get('/repurchase/churn-warning', { params })
}

// 获取新客户返单监控
export function getNewCustomerRepurchase(params) {
  return request.get('/repurchase/new-customer-repurchase', { params })
}

// 获取商品生命周期表（上市后销量）
export function getProductLifecycle(params) {
  return request.get('/repurchase/product-lifecycle', { params })
}

// 获取客户留存率表（单品维度）
export function getCustomerRetention(params) {
  return request.get('/repurchase/customer-retention', { params })
}

// 获取新品预警表
export function getNewProductWarning(params) {
  return request.get('/repurchase/new-product-warning', { params })
}

// 获取客户商品 Cohort 矩阵
export function getCustomerProductMatrix(params) {
  return request.get('/repurchase/customer-product-matrix', { params })
}

// 获取单品客户 Cohort 矩阵
export function getProductCustomerCohort(params) {
  return request.get('/repurchase/product-customer-cohort', { params })
}
