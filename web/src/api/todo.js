import request from './index'

// 获取数据维护待办项
export function getTodoItems() {
  return request.get('/todo/items')
}
