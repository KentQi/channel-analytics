<template>
  <div class="new-customer-tracking">
    <!-- 筛选器 -->
    <div class="filter-bar">
      <div class="filter-item">
        <span class="filter-label">新客户定义天数</span>
        <el-select v-model="newCustDays" style="width: 120px" @change="loadData">
          <el-option :value="60" label="60 天" />
          <el-option :value="90" label="90 天" />
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

    <!-- 新客户返单监控 -->
    <div class="section-card">
      <div class="section-title">新客户返单监控</div>
      <el-table :data="newCustomerWeekly" stripe border size="small" max-height="450">
        <el-table-column prop="customer" label="客户" min-width="150" show-overflow-tooltip />
        <el-table-column prop="first_order_date" label="首单日期" width="110" align="center" />
        <el-table-column prop="week_1" label="第1周" width="80" align="center" />
        <el-table-column prop="week_2" label="第2周" width="80" align="center" />
        <el-table-column prop="week_3" label="第3周" width="80" align="center" />
        <el-table-column prop="week_4" label="第4周" width="80" align="center" />
        <el-table-column prop="week_5" label="第5周" width="80" align="center" />
        <el-table-column prop="week_6" label="第6周" width="80" align="center" />
        <el-table-column prop="week_7" label="第7周" width="80" align="center" />
        <el-table-column prop="week_8" label="第8周" width="80" align="center" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, inject } from 'vue'
import { useFilterStore } from '@/stores/filter'
import { getNewCustomerRepurchase } from '@/api/repurchase'

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const newCustDays = ref(90)
const filters = reactive({
  customerKeyword: '',
  region: null,
  manager: null
})

const filterOptions = reactive({
  regions: [],
  managers: []
})

const newCustomerWeekly = ref([])

async function loadData() {
  try {
    setLoading(true)
    const params = { days: newCustDays.value }
    if (filters.region) params.region = filters.region
    if (filters.manager) params.manager = filters.manager
    if (filters.customerKeyword) params.customer = filters.customerKeyword
    const res = await getNewCustomerRepurchase(params)
    const data = res.data?.data || res.data || {}
    newCustomerWeekly.value = data.weekly_data || []
  } catch (e) {
    console.error('加载新客户返单监控失败:', e)
    newCustomerWeekly.value = []
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
.new-customer-tracking {
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
