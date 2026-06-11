import { defineStore } from 'pinia'
import { reactive, computed } from 'vue'
import request from '@/api'

// 默认日期范围：最近30天
const getDefaultDateRange = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)
  return {
    dateFrom: start.toISOString().split('T')[0],
    dateTo: end.toISOString().split('T')[0]
  }
}

// 获取当月1日
const getFirstDayOfMonth = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`
}

// 获取今天
const getToday = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

// 获取当前月份
const getCurrentMonth = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export const useFilterStore = defineStore('filter', () => {
  // 销售分析筛选器 - 对齐源程序Tab1
  const sales = reactive({
    region: null,
    manager: null,
    customer: null,
    channel: null,
    // 日期筛选 - 单据日期默认不选，审核日期默认当月1日到今天
    docDateRange: null,   // 单据日期范围 [开始, 结束]
    auditDateRange: [getFirstDayOfMonth(), getToday()], // 审核日期范围 [开始, 结束]
    // 商品属性筛选（对齐源程序）
    category: null,           // 商品品类
    abcClass: null,           // ABC分类
    lifecycleStatus: null,    // 生命周期
    customFlag: null,         // 定制标记
    promotedFlag: null,       // 主推标记
    materialCode: null,       // 物料编码
    materialName: null,       // 物料名称（模糊搜索）
    // 兼容旧字段
    dateFrom: getFirstDayOfMonth(),
    dateTo: getToday()
  })

  // 仪表盘筛选器
  const dashboard = reactive({
    region: null,      // 大区
    startMonth: null,  // 起始期间 YYYY/MM
    endMonth: null     // 结束期间 YYYY/MM
  })

  // 指标达成筛选器
  const indicator = reactive({
    region: null,
    manager: null,
    month: getCurrentMonth()
  })

  // 销售明细筛选器
  const salesDetail = reactive({
    region: null,
    manager: null,
    customer: null,
    category: null,
    abcClass: null,
    materialCode: null,
    dateRange: [getFirstDayOfMonth(), getToday()]
  })

  // 单品货流筛选器
  const productFlow = reactive({
    materialCode: '',
    batchNo: '',
    customer: null,
    txType: null,
    ...getDefaultDateRange()
  })

  // 筛选器选项（从后端获取）
  const options = reactive({
    regions: [],
    managers: [],
    customers: [],
    channels: [],
    months: [],
    // 商品属性选项（对齐源程序）
    categories: [],      // 商品品类
    abcClasses: [],     // ABC分类
    lifecycleStatuses: [], // 生命周期
    customFlags: [],    // 定制标记
    promotedFlags: [],  // 主推标记
    materialCodes: [],   // 物料编码
    materialNameOptions: [], // 物料名称（远程搜索结果）
    // 仪表盘专用选项
    startMonths: [],     // 起始期间（过去12个月）
    txTypes: ['销售出库', '退货入库']  // 交易类型
  })

  // 选项加载状态
  const loadingOptions = reactive({
    regions: false,
    managers: false,
    customers: false,
    channels: false,
    months: false,
    // 商品属性加载状态
    categories: false,
    abcClasses: false,
    lifecycleStatuses: false,
    customFlags: false,
    promotedFlags: false,
    materialCodes: false
  })

  // 选项已加载标志
  const loadedOptions = reactive({
    regions: false,
    managers: false,
    customers: false,
    channels: false,
    months: false,
    // 商品属性加载标志
    categories: false,
    abcClasses: false,
    lifecycleStatuses: false,
    customFlags: false,
    promotedFlags: false,
    materialCodes: false
  })

  // 计算属性：是否有任何筛选器被激活
  const salesHasFilters = computed(() => {
    return !!(sales.region || sales.manager || sales.customer || sales.channel ||
             sales.dateFrom || sales.dateTo)
  })

  const dashboardHasFilters = computed(() => {
    return !!(dashboard.region || dashboard.manager)
  })

  const indicatorHasFilters = computed(() => {
    return !!(indicator.region || indicator.manager || indicator.month)
  })

  const salesDetailHasFilters = computed(() => {
    return !!(salesDetail.region || salesDetail.manager || salesDetail.customer ||
             salesDetail.dateRange)
  })

  const productFlowHasFilters = computed(() => {
    return !!(productFlow.materialCode || productFlow.batchNo)
  })

  // 重置销售分析筛选器 - 对齐源程序
  function resetSales() {
    sales.region = null
    sales.manager = null
    sales.customer = null
    sales.channel = null
    // 日期筛选重置 - 单据日期不选，审核日期默认当月1日到今天
    sales.docDateRange = null
    sales.auditDateRange = [getFirstDayOfMonth(), getToday()]
    // 商品属性重置
    sales.category = null
    sales.abcClass = null
    sales.lifecycleStatus = null
    sales.customFlag = null
    sales.promotedFlag = null
    sales.materialCode = null
    sales.materialName = null
    // 兼容旧字段
    sales.dateFrom = getFirstDayOfMonth()
    sales.dateTo = getToday()
  }

  // 重置仪表盘筛选器
  function resetDashboard() {
    dashboard.region = null
    // 默认：开始=当前月份-12，结束=当前月份
    const now = new Date()
    const currentYear = now.getFullYear()
    const currentMonth = now.getMonth() + 1
    // 计算12个月前的月份
    let startMonth = currentMonth - 11
    let startYear = currentYear
    if (startMonth <= 0) {
      startMonth += 12
      startYear -= 1
    }
    dashboard.startMonth = `${startYear}/${String(startMonth).padStart(2, '0')}`
    dashboard.endMonth = `${currentYear}/${String(currentMonth).padStart(2, '0')}`
  }

  // 重置指标达成筛选器
  function resetIndicator() {
    indicator.region = null
    indicator.manager = null
    indicator.month = getCurrentMonth()
  }

  // 重置销售明细筛选器
  function resetSalesDetail() {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 30)
    salesDetail.region = null
    salesDetail.manager = null
    salesDetail.customer = null
    salesDetail.dateRange = [start.toISOString().split('T')[0], end.toISOString().split('T')[0]]
    salesDetail.category = null
    salesDetail.abcClass = null
    salesDetail.materialCode = null
  }

  // 重置单品货流筛选器
  function resetProductFlow() {
    productFlow.materialCode = ''
    productFlow.batchNo = ''
  }

  // 下游级联重置
  function resetDownstream(field, value) {
    switch (field) {
      case 'region':
        // 重置大区后，下游的经理和客户也需要重置
        sales.manager = null
        sales.customer = null
        dashboard.manager = null
        indicator.manager = null
        salesDetail.manager = null
        salesDetail.customer = null
        break
      case 'manager':
        // 重置经理后，客户需要重置
        sales.customer = null
        salesDetail.customer = null
        break
      case 'dateFrom':
        // 日期范围变更时，不自动重置其他字段
        break
      case 'dateTo':
        break
      case 'month':
        // 月份变更时，不自动重置其他字段
        break
      case 'materialCode':
        // 物料编码变更时，批次号需要重置
        productFlow.batchNo = ''
        break
      default:
        break
    }
  }

  // 获取大区列表
  async function fetchRegions() {
    if (loadedOptions.regions) return options.regions
    loadingOptions.regions = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      options.regions = data.regions || []
      loadedOptions.regions = true
      return options.regions
    } catch (error) {
      console.error('获取大区列表失败:', error)
      options.regions = []
      return []
    } finally {
      loadingOptions.regions = false
    }
  }

  // 获取经理列表（可选的大区筛选）
  async function fetchManagers(regionId = null) {
    loadingOptions.managers = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      options.managers = data.managers || []
      loadedOptions.managers = true
      return options.managers
    } catch (error) {
      console.error('获取经理列表失败:', error)
      options.managers = []
      return []
    } finally {
      loadingOptions.managers = false
    }
  }

  // 获取客户列表（可选的经理筛选）
  async function fetchCustomers(managerId = null) {
    loadingOptions.customers = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      options.customers = data.customers || []
      loadedOptions.customers = true
      return options.customers
    } catch (error) {
      console.error('获取客户列表失败:', error)
      options.customers = []
      return []
    } finally {
      loadingOptions.customers = false
    }
  }

  // 获取渠道列表
  async function fetchChannels() {
    if (loadedOptions.channels) return options.channels
    loadingOptions.channels = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      options.channels = data.channels || []
      loadedOptions.channels = true
      return options.channels
    } catch (error) {
      console.error('获取渠道列表失败:', error)
      options.channels = []
      return []
    } finally {
      loadingOptions.channels = false
    }
  }

  // 获取月份列表
  async function fetchMonths() {
    if (loadedOptions.months) return options.months
    loadingOptions.months = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      const dateRange = data.date_range || {}
      if (dateRange.min_audit) {
        const start = new Date(dateRange.min_audit)
        const end = new Date(dateRange.max_audit || new Date())
        const months = []
        let current = new Date(start.getFullYear(), start.getMonth(), 1)
        while (current <= end) {
          months.push(`${current.getFullYear()}/${String(current.getMonth() + 1).padStart(2, '0')}`)
          current.setMonth(current.getMonth() + 1)
        }
        options.months = months.reverse()
      } else {
        options.months = []
      }
      loadedOptions.months = true
      return options.months
    } catch (error) {
      console.error('获取月份列表失败:', error)
      options.months = []
      return []
    } finally {
      loadingOptions.months = false
    }
  }

  // 生成起始期间选项（过去12个月）
  function generateStartMonths() {
    const now = new Date()
    const currentYear = now.getFullYear()
    const currentMonth = now.getMonth() + 1
    const months = []

    // 从11个月前开始
    for (let i = 11; i >= 0; i--) {
      let targetMonth = currentMonth - i
      let targetYear = currentYear
      while (targetMonth <= 0) {
        targetMonth += 12
        targetYear -= 1
      }
      months.push(`${targetYear}/${String(targetMonth).padStart(2, '0')}`)
    }
    options.startMonths = months
  }

  // 获取商品品类列表（对齐源程序）
  async function fetchCategories() {
    if (loadedOptions.categories) return options.categories
    loadingOptions.categories = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      options.categories = data.categories || []
      loadedOptions.categories = true
      return options.categories
    } catch (error) {
      console.error('获取商品品类列表失败:', error)
      options.categories = []
      return []
    } finally {
      loadingOptions.categories = false
    }
  }

  // 获取ABC分类列表（对齐源程序）
  async function fetchAbcClasses() {
    if (loadedOptions.abcClasses) return options.abcClasses
    loadingOptions.abcClasses = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      options.abcClasses = data.abc_classes || []
      loadedOptions.abcClasses = true
      return options.abcClasses
    } catch (error) {
      console.error('获取ABC分类列表失败:', error)
      options.abcClasses = []
      return []
    } finally {
      loadingOptions.abcClasses = false
    }
  }

  // 获取生命周期列表（对齐源程序）
  async function fetchLifecycleStatuses() {
    if (loadedOptions.lifecycleStatuses) return options.lifecycleStatuses
    loadingOptions.lifecycleStatuses = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      options.lifecycleStatuses = data.lifecycle_statuses || []
      loadedOptions.lifecycleStatuses = true
      return options.lifecycleStatuses
    } catch (error) {
      console.error('获取生命周期列表失败:', error)
      options.lifecycleStatuses = []
      return []
    } finally {
      loadingOptions.lifecycleStatuses = false
    }
  }

  // 获取定制标记列表（对齐源程序）
  async function fetchCustomFlags() {
    if (loadedOptions.customFlags) return options.customFlags
    loadingOptions.customFlags = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      options.customFlags = data.custom_flags || []
      loadedOptions.customFlags = true
      return options.customFlags
    } catch (error) {
      console.error('获取定制标记列表失败:', error)
      options.customFlags = []
      return []
    } finally {
      loadingOptions.customFlags = false
    }
  }

  // 获取主推标记列表（对齐源程序）
  async function fetchPromotedFlags() {
    if (loadedOptions.promotedFlags) return options.promotedFlags
    loadingOptions.promotedFlags = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      options.promotedFlags = data.promoted_flags || []
      loadedOptions.promotedFlags = true
      return options.promotedFlags
    } catch (error) {
      console.error('获取主推标记列表失败:', error)
      options.promotedFlags = []
      return []
    } finally {
      loadingOptions.promotedFlags = false
    }
  }

  // 获取物料编码列表（对齐源程序）
  async function fetchMaterialCodes() {
    if (loadedOptions.materialCodes) return options.materialCodes
    loadingOptions.materialCodes = true
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      options.materialCodes = data.material_codes || []
      loadedOptions.materialCodes = true
      return options.materialCodes
    } catch (error) {
      console.error('获取物料编码列表失败:', error)
      options.materialCodes = []
      return []
    } finally {
      loadingOptions.materialCodes = false
    }
  }

  // 远程搜索物料名称
  async function searchMaterialName(keyword) {
    try {
      const response = await request.get('/sales/material-name-options', {
        params: { keyword }
      })
      options.materialNameOptions = response.data || []
      return options.materialNameOptions
    } catch (error) {
      console.error('搜索物料名称失败:', error)
      options.materialNameOptions = []
      return []
    }
  }

  // 获取所有筛选器选项
  async function fetchAllOptions() {
    // 先调用 API 获取日期范围，用于生成 startMonths
    try {
      const response = await request.get('/sales/filter-options')
      const data = response.data.data || response.data || {}
      const dateRange = data.date_range || {}

      // 生成起始期间选项（从最早单据日期开始到当前月份）
      if (dateRange.doc_date && dateRange.doc_date.min) {
        const start = new Date(dateRange.doc_date.min)
        const now = new Date()
        const months = []
        let current = new Date(start.getFullYear(), start.getMonth(), 1)
        while (current <= now) {
          months.push(`${current.getFullYear()}/${String(current.getMonth() + 1).padStart(2, '0')}`)
          current.setMonth(current.getMonth() + 1)
        }
        options.startMonths = months.reverse()
      } else {
        generateStartMonths()  // 兜底：从当前日期往前推12个月
      }

      // 设置仪表盘默认值：开始=当前月份-11，结束=当前月份
      const now = new Date()
      const currentYear = now.getFullYear()
      const currentMonth = now.getMonth() + 1
      let startMonth = currentMonth - 11
      let startYear = currentYear
      if (startMonth <= 0) {
        startMonth += 12
        startYear -= 1
      }
      dashboard.startMonth = `${startYear}/${String(startMonth).padStart(2, '0')}`
      dashboard.endMonth = `${currentYear}/${String(currentMonth).padStart(2, '0')}`

      // 填充其他选项
      options.regions = data.regions || []
      options.managers = data.managers || []
      options.customers = data.customers || []
      options.channels = data.channels || []
      options.categories = data.categories || []
      options.abcClasses = data.abc_classes || []
      options.lifecycleStatuses = data.lifecycle_statuses || []
      options.customFlags = data.custom_flags || []
      options.promotedFlags = data.promoted_flags || []
      options.materialCodes = data.material_codes || []

      // 标记所有选项已加载
      loadedOptions.regions = true
      loadedOptions.managers = true
      loadedOptions.customers = true
      loadedOptions.channels = true
      loadedOptions.categories = true
      loadedOptions.abcClasses = true
      loadedOptions.lifecycleStatuses = true
      loadedOptions.customFlags = true
      loadedOptions.promotedFlags = true
      loadedOptions.materialCodes = true

    } catch (error) {
      console.error('获取筛选器选项失败:', error)
      generateStartMonths()  // 兜底
    }
  }

  // 清除所有缓存的选项
  function clearOptionsCache() {
    loadedOptions.regions = false
    loadedOptions.managers = false
    loadedOptions.customers = false
    loadedOptions.channels = false
    loadedOptions.months = false
    // 商品属性选项缓存
    loadedOptions.categories = false
    loadedOptions.abcClasses = false
    loadedOptions.lifecycleStatuses = false
    loadedOptions.customFlags = false
    loadedOptions.promotedFlags = false
    loadedOptions.materialCodes = false
  }

  return {
    // 筛选器状态
    sales,
    dashboard,
    indicator,
    salesDetail,
    productFlow,
    options,
    loadingOptions,

    // 计算属性
    salesHasFilters,
    dashboardHasFilters,
    indicatorHasFilters,
    salesDetailHasFilters,
    productFlowHasFilters,

    // 重置方法
    resetSales,
    resetDashboard,
    resetIndicator,
    resetSalesDetail,
    resetProductFlow,
    resetDownstream,

    // 获取选项方法
    fetchRegions,
    fetchManagers,
    fetchCustomers,
    fetchChannels,
    fetchMonths,
    fetchAllOptions,
    clearOptionsCache,

    // 商品属性选项方法（对齐源程序）
    fetchCategories,
    fetchAbcClasses,
    fetchLifecycleStatuses,
    fetchCustomFlags,
    fetchPromotedFlags,
    fetchMaterialCodes,
    searchMaterialName
  }
})
