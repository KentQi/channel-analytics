<template>
  <div class="churn-warning">
    <!-- 筛选器 -->
    <div class="filter-bar">
      <div class="filter-item">
        <span class="filter-label">阈值天数</span>
        <el-select v-model="churnDays" style="width: 120px" @change="loadData">
          <el-option :value="60" label="60 天" />
          <el-option :value="90" label="90 天" />
          <el-option :value="120" label="120 天" />
          <el-option :value="180" label="180 天" />
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

    <!-- 流失预警表格 -->
    <div class="section-card">
      <div class="section-title">流失预警客户名单</div>
      <el-table :data="churnCustomers" stripe border size="small" max-height="450">
        <el-table-column prop="customer" label="客户" min-width="150" show-overflow-tooltip />
        <el-table-column prop="first_month" label="首次进货" width="110" align="center">
          <template #default="{ row }">{{ formatDate(row.first_month) }}</template>
        </el-table-column>
        <el-table-column prop="last_period" label="最后进货" width="110" align="center">
          <template #default="{ row }">{{ formatDate(row.last_period) }}</template>
        </el-table-column>
        <el-table-column prop="total_amount" label="累计金额" width="120" align="right">
          <template #default="{ row }">{{ formatAmount(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column prop="order_count" label="订单数" width="80" align="center" />
        <el-table-column prop="max_interval_days" label="最大间隔(天)" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.max_interval_days >= 180 ? 'danger' : row.max_interval_days >= 120 ? 'warning' : 'info'" size="small">
              {{ row.max_interval_days }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, inject } from 'vue'
import { useFilterStore } from '@/stores/filter'
import { getChurnWarning } from '@/api/repurchase'

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const churnDays = ref(90)
const filters = reactive({
  customerKeyword: '',
  region: null,
  manager: null
})

const filterOptions = reactive({
  regions: [],
  managers: []
})

const churnCustomers = ref([])

function formatAmount(val) {
  if (val === null || val === undefined) return '0'
  const num = Number(val)
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

async function loadData() {
  try {
    setLoading(true)
    const params = { days: churnDays.value }
    if (filters.region) params.region = filters.region
    if (filters.manager) params.manager = filters.manager
    if (filters.customerKeyword) params.customer = filters.customerKeyword
    const res = await getChurnWarning(params)
    const data = res.data?.data || res.data || {}
    churnCustomers.value = data.churn_customers || []
  } catch (e) {
    console.error('加载流失预警失败:', e)
    churnCustomers.value = []
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
.churn-warning {
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
</style>
