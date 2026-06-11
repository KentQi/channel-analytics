<template>
  <div class="customer-retention-detail">
    <!-- 筛选器 -->
    <div class="filter-bar">
      <div class="filter-item">
        <span class="filter-label">追溯周期</span>
        <el-select v-model="filters.months" style="width: 120px" @change="loadData">
          <el-option :value="6" label="6 月" />
          <el-option :value="12" label="12 月" />
          <el-option :value="18" label="18 月" />
          <el-option :value="24" label="24 月" />
          <el-option :value="36" label="36 月" />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">客户</span>
        <el-input
          v-model="filters.customerKeyword"
          placeholder="搜索客户"
          clearable
          style="width: 180px"
          @clear="filters.customerKeyword = ''; loadData()"
          @keyup.enter="loadData"
        />
      </div>
      <div class="filter-item">
        <span class="filter-label">60天内进货</span>
        <el-select v-model="filters.active60d" style="width: 120px" @change="loadData">
          <el-option value="all" label="全部" />
          <el-option value="是" label="是" />
          <el-option value="否" label="否" />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">大区</span>
        <el-select v-model="filters.region" clearable style="width: 150px" @change="loadData">
          <el-option v-for="r in filterOptions.regions" :key="r" :label="r" :value="r" />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">客户经理</span>
        <el-select v-model="filters.manager" clearable style="width: 150px" @change="loadData">
          <el-option v-for="m in filterOptions.managers" :key="m" :label="m" :value="m" />
        </el-select>
      </div>
    </div>

    <!-- 客户明细表格 -->
    <div class="section-card">
      <div class="section-title">客户返单详情</div>
      <el-table :data="filteredCustomerStats" stripe border max-height="450" size="small">
        <el-table-column prop="customer" label="客户" min-width="140">
          <template #default="{ row }">
            <a class="customer-link" @click="openCustomerDialog(row.customer)">{{ row.customer }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="first_month" label="首次进货" width="110" align="center">
          <template #default="{ row }">{{ formatDate(row.first_month) }}</template>
        </el-table-column>
        <el-table-column prop="last_period" label="最后进货" width="110" align="center">
          <template #default="{ row }">{{ formatDate(row.last_period) }}</template>
        </el-table-column>
        <el-table-column prop="total_amount" label="累计金额" width="120" align="right">
          <template #default="{ row }">{{ formatAmount(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column prop="total_orders" label="累计订单数" width="100" align="center" />
        <el-table-column prop="max_interval_days" label="最大进货间隔(天)" width="140" align="center" />
        <el-table-column prop="avg_interval_days" label="平均进货间隔(天)" width="140" align="center" />
        <el-table-column prop="active_60d" label="60天内进货" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.active_60d === '是' ? 'success' : 'danger'" size="small">{{ row.active_60d }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 客户商品 Cohort 矩阵弹窗 -->
    <el-dialog v-model="customerDialogVisible" :title="selectedCustomer + ' - 出货时序数据'" width="1200px" style="height: 80vh" destroy-on-close>
      <div v-if="customerSummary" class="cohort-summary">
        此客户合作 {{ customerSummary.cooperation_days }} 天，累计出货 {{ formatAmount(customerSummary.total_amount) }} 万元，
        首次合作90天内出货 {{ formatAmount(customerSummary.amount_first_90d) }} 万元，
        合作90-180天内出货 {{ formatAmount(customerSummary.amount_90_to_180d) }} 万元，
        最近90天内出货 {{ formatAmount(customerSummary.amount_last_90d) }} 万元。
      </div>
      <el-table v-if="customerProductMatrix.length > 0" :data="customerProductMatrix" stripe border size="small" max-height="520" table-layout="fixed" :default-sort="{ prop: 'first_period', order: 'ascending' }" show-summary :summary-method="getCohortSummary" sum-text="合计">
        <el-table-column prop="material_code" label="物料编码" width="120" fixed />
        <el-table-column prop="material_name" label="物料名称" min-width="180" fixed />
        <el-table-column prop="first_period" label="首次进货时间" width="120" align="center">
          <template #default="{ row }">{{ formatDate(row.first_period) }}</template>
        </el-table-column>
        <el-table-column
          v-for="(col, idx) in customerProductMonthColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="getColumnLabel(idx)"
          width="80"
          align="right"
        >
          <template #default="{ row }">
            <span>{{ row[col.prop] }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div v-else style="text-align: center; color: #909399; padding: 40px">暂无该客户的商品数据</div>
      <template #footer>
        <el-button @click="toggleViewMode">
          {{ isDynamicView ? '切换: 偏移模式' : '切换: 动态日期' }}
        </el-button>
        <el-button v-if="customerProductMatrix.length > 0" type="success" @click="downloadCustomerMatrix">
          {{ isDynamicView ? '下载(动态日期)' : '下载(偏移模式)' }}
        </el-button>
        <el-button @click="customerDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { useFilterStore } from '@/stores/filter'
import { getCohortMatrix, getCustomerProductMatrix } from '@/api/repurchase'

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const filters = reactive({
  months: 12,
  customerKeyword: '',
  active60d: 'all',
  region: null,
  manager: null
})

const filterOptions = reactive({
  regions: [],
  managers: []
})

const customerStats = ref([])
const selectedCustomer = ref('')
const customerDialogVisible = ref(false)
const customerProductMatrix = ref([])
const customerProductMonthColumns = ref([])
const isDynamicView = ref(false)
const customerSummary = ref(null)

const filteredCustomerStats = computed(() => {
  let data = customerStats.value
  if (filters.active60d !== 'all') {
    data = data.filter(c => c.active_60d === filters.active60d)
  }
  return [...data].sort((a, b) => b.total_amount - a.total_amount)
})

function formatAmount(val) {
  if (val === null || val === undefined) return '0'
  const num = Number(val) / 10000
  if (isNaN(num)) return '0'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatDate(val) {
  if (!val) return ''
  const str = String(val)
  if (str.length === 8) {
    return `${str.slice(0, 4)}-${str.slice(4, 6)}-${str.slice(6, 8)}`
  }
  if (str.length === 6) {
    return `${str.slice(0, 4)}-${str.slice(4, 6)}`
  }
  return str
}

// 获取列标签
function getColumnLabel(idx) {
  if (!isDynamicView.value) {
    const labels = ['首月', '+1月', '+2月', '+3月', '+4月', '+5月', '+6月', '+7月', '+8月', '+9月', '+10月', '+11月']
    return labels[idx] || `+${idx}月`
  }
  // 动态模式：直接使用后端返回的列标签（YYYY-MM格式）
  return customerProductMonthColumns.value[idx]?.label || ''
}

// 合计行：前 3 列为文本/日期（留空），其后为月份列做 SUM
const COHORT_NUMERIC_COL_START = 3
function getCohortSummary({ columns, data }) {
  return columns.map((col, idx) => {
    if (idx < COHORT_NUMERIC_COL_START) return ''
    return data.reduce((sum, row) => {
      const v = Number(row[col.property])
      return sum + (isNaN(v) ? 0 : v)
    }, 0)
  })
}

function openCustomerDialog(customer) {
  selectedCustomer.value = customer
  customerDialogVisible.value = true
  buildCustomerProductMatrix(customer)
}

async function buildCustomerProductMatrix(customer) {
  try {
    const params = {
      customer,
      months: filters.months,
      view_mode: isDynamicView.value ? 'absolute' : 'offset'
    }
    if (filters.region) params.region = filters.region
    if (filters.manager) params.manager = filters.manager
    const res = await getCustomerProductMatrix(params)
    const data = res.data?.data || res.data || {}
    customerProductMatrix.value = data.matrix_data || []
    const cols = data.month_columns || []
    customerProductMonthColumns.value = cols.map(c => ({ prop: c, label: c }))
    customerSummary.value = data.summary || null
  } catch (e) {
    console.error('加载客户商品 Cohort 矩阵失败:', e)
    customerProductMatrix.value = []
    customerProductMonthColumns.value = []
    customerSummary.value = null
  }
}

function toggleViewMode() {
  isDynamicView.value = !isDynamicView.value
  // 重新加载数据（带新的view_mode）
  buildCustomerProductMatrix(selectedCustomer.value)
}

function downloadCustomerMatrix() {
  if (customerProductMatrix.value.length === 0) return

  // 下载时使用后端返回的实际列标签
  const labels = customerProductMonthColumns.value.map(c => c.label)
  const headers = ['物料编码', '物料名称', '首次进货时间', ...labels]
  const rows = customerProductMatrix.value.map(row => {
    return [
      row.material_code,
      row.material_name,
      formatDate(row.first_period),
      ...customerProductMonthColumns.value.map(c => row[c.prop] ?? 0)
    ]
  })

  const csvContent = [headers, ...rows].map(r => r.join(',')).join('\n')
  const BOM = '﻿'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${selectedCustomer.value}_商品Cohort矩阵${isDynamicView.value ? '(动态日期)' : '(偏移模式)'}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

async function loadData() {
  try {
    setLoading(true)
    const params = { months: filters.months }
    if (filters.region) params.region = filters.region
    if (filters.manager) params.manager = filters.manager
    if (filters.customerKeyword) params.customer = filters.customerKeyword
    const res = await getCohortMatrix(params)
    const data = res.data?.data || res.data || {}
    customerStats.value = data.customer_stats || []
  } catch (e) {
    console.error('加载客户明细失败:', e)
    customerStats.value = []
  } finally {
    setLoading(false)
  }
}

async function loadFilterOptions() {
  try {
    const regions = await filterStore.fetchRegions()
    filterOptions.regions = regions || []
    const managers = await filterStore.fetchManagers()
    filterOptions.managers = managers || []
  } catch (e) {
    console.error('加载筛选选项失败:', e)
  }
}

onMounted(() => {
  loadFilterOptions()
  loadData()
})
</script>

<style scoped>
.customer-retention-detail {
  padding: 0;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background-color: #f5f7fa;
  border-radius: 6px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.section-card {
  background-color: #fff;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.customer-link {
  color: #409eff;
  text-decoration: underline;
  cursor: pointer;
}

.customer-link:hover {
  color: #66b1ff;
}

:deep(.el-table__header th) {
  font-weight: bold;
  text-align: center;
}
:deep(.el-table__footer-wrapper td) {
  font-weight: bold;
}

.cohort-summary {
  margin-bottom: 12px;
  padding: 10px 16px;
  background-color: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}
</style>
