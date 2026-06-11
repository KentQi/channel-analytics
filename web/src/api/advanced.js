import request from './index'

export function getProductLifecycle(params) {
  return request.get('/advanced/product-lifecycle', { params })
}

export function getCustomerLifecycle(params) {
  return request.get('/advanced/customer-lifecycle', { params })
}

export function getProductCluster(params) {
  return request.get('/advanced/product-cluster', { params })
}

export function getCustomerCluster(params) {
  return request.get('/advanced/customer-cluster', { params })
}

/**
 * 调用LLM生成个性化商品生命周期运营建议
 * @param {Object} productData - 商品数据对象
 * @returns {Promise}
 */
export function getLlmLifecycleAdvice(productData) {
  return request.post('/advanced/product-lifecycle/advice', productData, { timeout: 60000 })
}
