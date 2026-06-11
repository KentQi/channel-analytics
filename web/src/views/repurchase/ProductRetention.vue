<template>
  <div class="product-retention">
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
        <span class="filter-label">ABC分类</span>
        <el-select v-model="filters.abcClass" clearable style="width: 120px" @change="loadData">
          <el-option value="A" label="A类" />
          <el-option value="B" label="B类" />
          <el-option value="C" label="C类" />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">生命周期</span>
        <el-select v-model="filters.lifecycle" clearable style="width: 120px" @change="loadData">
          <el-option value="新品" label="新品" />
          <el-option value="成长" label="成长" />
          <el-option value="成熟" label="成熟" />
          <el-option value="衰退" label="衰退" />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">物料名称</span>
        <el-input v-model="filters.productName" placeholder="关键词搜索" clearable style="width: 180px" @change="loadData" />
      </div>
      <div class="filter-item">
        <span class="filter-label">品类</span>
        <el-select v-model="filters.category" clearable placeholder="全部" style="width: 130px" @change="loadData">
          <el-option v-for="c in filterOptions.categories" :key="c" :label="c" :value="c" />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">大区</span>
        <el-select v-model="filters.region" clearable style="width: 150px" @change="loadData">
          <el-option v-for="r in filterOptions.regions" :key="r" :label="r" :value="r" />
        </el-select>
      </div>
    </div>

    <!-- 客户留存率表 -->
    <div class="section-card">
      <div class="section-title">客户留存率表</div>
      <el-table :data="retentionData" stripe border size="small" max-height="450">
        <el-table-column prop="lifecycle_status" label="生命周期" width="80" align="center" fixed />
        <el-table-column prop="abc_class" label="ABC" width="60" align="center" fixed />
        <el-table-column prop="material_code" label="物料编码" width="110" fixed show-overflow-tooltip>
          <template #default="{ row }">
            <span class="link-text" @click="showCustomerCohort(row)">{{ row.material_code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="material_name" label="物料名称" min-width="140" fixed show-overflow-tooltip />
        <el-table-column prop="first_stock_in_date" label="首批入库" width="110" align="center" fixed />
        <el-table-column
          v-for="col in retentionMonthColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          width="80"
          align="center"
        >
          <template #default="{ row }">
            <span :style="{ color: getRetentionColor(row[col.prop]) }">{{ row[col.prop] !== '' && row[col.prop] !== undefined ? row[col.prop] + '%' : '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 单品返单详情弹窗 -->
    <el-dialog v-model="cohortDialogVisible" :title="dialogTitle" width="1200px" style="height: 80vh" destroy-on-close>
      <div v-if="productSummary" class="cohort-summary">
        此商品距首次采购入库 {{ productSummary.days_since_first }} 天，
        累计合作 {{ productSummary.total_customers }} 个客户，{{ formatAmount(productSummary.total_amount) }} 万元；
        开始3个月内 {{ productSummary.customers_first_3m }} 个客户进货，{{ formatAmount(productSummary.amount_first_3m) }} 万元；
        最近3个月内 {{ productSummary.customers_last_3m }} 个客户进货，{{ formatAmount(productSummary.amount_last_3m) }} 万元。
      </div>
      <el-table v-if="cohortData.length > 0" :data="cohortData" stripe border size="small" max-height="520" table-layout="fixed" :default-sort="{ prop: 'first_order_date', order: 'ascending' }" show-summary :summary-method="getCohortSummary" sum-text="合计">
        <el-table-column prop="customer" label="客户名称" min-width="150" fixed show-overflow-tooltip />
        <el-table-column prop="material_code" label="物料编码" width="120" show-overflow-tooltip />
        <el-table-column prop="material_name" label="物料名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="first_order_date" label="首次下单时间" width="120" align="center" />
        <el-table-column
          v-for="(col, idx) in cohortMonthColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="getColumnLabel(idx)"
          width="70"
          align="center"
        >
          <template #default="{ row }">
            <span :style="{ color: row[col.prop] > 0 ? '#2171b5' : '#c6dbef' }">{{ row[col.prop] || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty-tip">暂无数据</div>
      <template #footer>
        <el-button @click="toggleViewMode">
          {{ isDynamicView ? '切换: 偏移模式' : '切换: 动态日期' }}
        </el-button>
        <el-button v-if="cohortData.length > 0" type="success" @click="downloadCohortMatrix">
          {{ isDynamicView ? '下载(动态日期)' : '下载(偏移模式)' }}
        </el-button>
        <el-button @click="cohortDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { useFilterStore } from '@/stores/filter'
import { getCustomerRetention, getProductCustomerCohort } from '@/api/repurchase'

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const filters = reactive({
  months: 18,
  abcClass: null,
  lifecycle: null,
  productName: '',
  category: null,
  region: null
})

const filterOptions = reactive({
  regions: [],
  categories: []
})

const retentionData = ref([])
const retentionMonthColumns = ref([])

// 弹窗相关
const cohortDialogVisible = ref(false)
const selectedMaterial = ref('')
const selectedMaterialName = ref('')
const cohortData = ref([])
const cohortMonthColumns = ref([])
const isDynamicView = ref(false)
const productSummary = ref(null)

const dialogTitle = computed(() => {
  return selectedMaterial.value + ' - ' + selectedMaterialName.value + ' - 客户返单次数'
})

function formatAmount(val) {
  if (val === null || val === undefined) return '0'
  const num = Number(val) / 10000
  if (isNaN(num)) return '0'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function getRetentionColor(val) {
  if (val === '' || val === undefined || val === null) return '#909399'
  const num = Number(val)
  if (isNaN(num)) return '#909399'
  if (num >= 50) return '#2171b5'
  if (num >= 20) return '#6baed6'
  if (num > 0) return '#9ecae1'
  return '#c6dbef'
}

async function showCustomerCohort(row) {
  try {
    selectedMaterial.value = row.material_code
    selectedMaterialName.value = row.material_name || ''
    cohortDialogVisible.value = true
    const params = {
      material_code: row.material_code,
      months: filters.months,
      view_mode: isDynamicView.value ? 'absolute' : 'offset'
    }
    if (filters.category) params.category = filters.category
    const res = await getProductCustomerCohort(params)
    const data = res.data?.data || res.data || {}
    const materialName = data.material_name || row.material_name || ''
    selectedMaterialName.value = materialName
    cohortData.value = (data.cohort_data || []).map(item => ({
      ...item,
      material_code: row.material_code,
      material_name: materialName
    }))
    cohortMonthColumns.value = (data.month_columns || []).map(col => ({ prop: col, label: col }))
    productSummary.value = data.summary || null
  } catch (e) {
    console.error('加载单品返单详情失败:', e)
    cohortData.value = []
    productSummary.value = null
  }
}

// 获取列标签
function getColumnLabel(idx) {
  if (!isDynamicView.value) {
    const labels = ['首月', '+1月', '+2月', '+3月', '+4月', '+5月', '+6月', '+7月', '+8月', '+9月', '+10月', '+11月']
    return labels[idx] || `+${idx}月`
  }
  // 动态模式：直接使用后端返回的列标签（YYYY-MM格式）
  return cohortMonthColumns.value[idx]?.label || ''
}

// 合计行：前 4 列为文本/日期（留空），其后为月份列做 SUM
const COHORT_NUMERIC_COL_START = 4
function getCohortSummary({ columns, data }) {
  return columns.map((col, idx) => {
    if (idx < COHORT_NUMERIC_COL_START) return ''
    return data.reduce((sum, row) => {
      const v = Number(row[col.property])
      return sum + (isNaN(v) ? 0 : v)
    }, 0)
  })
}

// 获取所有行中最早的首次下单时间（用于判断动态模式）
function getEarliestFirstOrderDate() {
  let earliest = null
  cohortData.value.forEach(row => {
    const date = row.first_order_date
    if (date) {
      // first_order_date 格式可能是 YYYY-MM-DD 或 YYYYMMDD
      const normalized = date.replace(/-/g, '').slice(0, 6)
      if (!earliest || normalized < earliest) {
        earliest = normalized
      }
    }
  })
  return earliest
}

function toggleViewMode() {
  isDynamicView.value = !isDynamicView.value
  // 重新加载数据（带新的view_mode）
  showCustomerCohort({ material_code: selectedMaterial.value, material_name: selectedMaterialName.value })
}

function downloadCohortMatrix() {
  if (cohortData.value.length === 0) return

  // 下载时使用后端返回的实际列标签
  const labels = cohortMonthColumns.value.map(c => c.label)

  const headers = ['客户名称', '物料编码', '物料名称', '首次下单时间', ...labels]
  const rows = cohortData.value.map(row => {
    return [
      row.customer,
      row.material_code,
      row.material_name,
      row.first_order_date,
      ...cohortMonthColumns.value.map(c => row[c.prop] ?? 0)
    ]
  })

  const csvContent = [headers, ...rows].map(r => r.join(',')).join('\n')
  const BOM = '﻿'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${selectedMaterial.value}_${selectedMaterialName.value}_单品返单详情${isDynamicView.value ? '(动态日期)' : '(偏移模式)'}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

async function loadData() {
  try {
    setLoading(true)
    const params = { months: filters.months }
    if (filters.region) params.region = filters.region
    if (filters.abcClass) params.abc_class = filters.abcClass
    if (filters.lifecycle) params.lifecycle_status = filters.lifecycle
    if (filters.productName) params.product_name = filters.productName
    if (filters.category) params.category = filters.category
    const res = await getCustomerRetention(params)
    const data = res.data?.data || res.data || {}
    retentionData.value = data.retention_data || []
    if (retentionData.value.length > 0) {
      const allKeys = Object.keys(retentionData.value[0])
      retentionMonthColumns.value = allKeys
        .filter(k => k.startsWith('+'))
        .sort((a, b) => parseInt(a.replace('+', '').replace('月', '')) - parseInt(b.replace('+', '').replace('月', '')))
        .map(k => ({ prop: k, label: k }))
    } else {
      retentionMonthColumns.value = []
    }
  } catch (e) {
    console.error('加载客户留存率表失败:', e)
    retentionData.value = []
  } finally {
    setLoading(false)
  }
}

async function loadFilterOptions() {
  try {
    const [regions, categories] = await Promise.all([
      filterStore.fetchRegions(),
      filterStore.fetchCategories()
    ])
    filterOptions.regions = regions || []
    filterOptions.categories = categories || []
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
.product-retention {
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

:deep(.el-table__header th) {
  font-weight: bold;
  text-align: center;
}
:deep(.el-table__footer-wrapper td) {
  font-weight: bold;
}

.link-text {
  color: #409EFF;
  cursor: pointer;
}

.link-text:hover {
  text-decoration: underline;
}

.empty-tip {
  text-align: center;
  padding: 40px;
  color: #909399;
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
