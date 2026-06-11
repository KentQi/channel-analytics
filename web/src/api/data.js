import request from './index'

// ========== 商品属性 ==========

export function getProductAttrs(params) {
  return request.get('/data/product-attrs', { params })
}

export function updateProductAttr(materialCode, data) {
  return request.put(`/data/product-attrs/${materialCode}`, data)
}

export function importProductAttrs(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/data/product-attrs/import', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function downloadProductAttrsTemplate() {
  return request.get('/data/product-attrs/template')
}

export function updateFirstStockDate() {
  return request.post('/data/product-attrs/update-first-stock-date')
}

export function updateLifecycleStatus() {
  return request.post('/data/product-attrs/update-lifecycle-status')
}

// ========== 客户信息 ==========

export function getCustomers(params) {
  return request.get('/data/customers', { params })
}

export function updateCustomer(customerName, data) {
  return request.put(`/data/customers/${customerName}`, data)
}

export function importCustomers(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/data/customers/import', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function downloadCustomersTemplate() {
  return request.get('/data/customers/template')
}

// ========== 省区指标 ==========

export function getRegionIndicators(params) {
  return request.get('/data/region-indicators', { params })
}

export function updateRegionIndicator(region, period, data) {
  return request.put(`/data/region-indicators/${region}/${period}`, data)
}

export function importRegionIndicators(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/data/region-indicators/import', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function downloadRegionIndicatorsTemplate() {
  return request.get('/data/region-indicators/template')
}

// ========== 客户指标 ==========

export function getCustomerIndicators(params) {
  return request.get('/data/customer-indicators', { params })
}

export function updateCustomerIndicator(customer, period, data) {
  return request.put(`/data/customer-indicators/${customer}/${period}`, data)
}

export function importCustomerIndicators(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/data/customer-indicators/import', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function downloadCustomerIndicatorsTemplate() {
  return request.get('/data/customer-indicators/template')
}

// ========== 筛选配置 ==========

export function getFilterConfigs(params) {
  return request.get('/data/filter-configs', { params })
}

export function updateFilterConfig(id, data) {
  return request.put(`/data/filter-configs/${id}`, data)
}

export function getFilterConfig(filterType) {
  return request.get(`/data/filter-config/${filterType}`)
}

export function saveFilterConfig(filterType, values) {
  return request.put(`/data/filter-config/${filterType}`, { values })
}

export function importFilterConfigs(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/data/filter-configs/import', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function downloadFilterConfigsTemplate() {
  return request.get('/data/filter-configs/template')
}

// ========== 自营品牌 ==========

export function getSelfOperatedBrands(params) {
  return request.get('/data/self-operated-brands', { params })
}

export function updateSelfOperatedBrand(id, data) {
  return request.put(`/data/self-operated-brands/${id}`, data)
}

export function importSelfOperatedBrands(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/data/self-operated-brands/import', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function downloadSelfOperatedBrandsTemplate() {
  return request.get('/data/self-operated-brands/template')
}

// ========== stg 数据源选项 ==========

export function getCustomerClasses() {
  return request.get('/data/stg-options/customer-classes')
}

export function getCustomersByClass(customerClasses) {
  const params = {}
  if (customerClasses && customerClasses.length) {
    params.customer_classes = customerClasses.join(',')
  }
  return request.get('/data/stg-options/customers', { params })
}

// ========== 通用 ==========

export function getTableTypes() {
  return request.get('/data/table-types')
}
