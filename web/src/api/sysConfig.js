import request from './index'

/**
 * 获取大模型API配置
 */
export function getLlmConfig() {
  return request.get('/sys-config/llm')
}

/**
 * 更新大模型API配置
 * @param {Object} data - { minimax_api_key, minimax_base_url, minimax_model }
 */
export function updateLlmConfig(data) {
  return request.put('/sys-config/llm', data)
}

/**
 * 测试大模型API连接
 */
export function testLlmConnection() {
  return request.post('/sys-config/llm/test', {}, { timeout: 30000 })
}
