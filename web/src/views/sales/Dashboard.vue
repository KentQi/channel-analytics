<template>
  <div class="dashboard">
    <!-- Tab 切换 -->
    <div class="sub-tabs">
      <div
        v-for="tab in tabs"
        :key="tab.name"
        class="sub-tab-item"
        :class="{ active: activeTab === tab.name }"
        @click="switchTab(tab.name)"
      >
        {{ tab.label }}
      </div>
    </div>

    <!-- 筛选条件 -->
    <div class="flow-filter">
      <el-form inline :model="currentFilters">
        <el-form-item label="大区">
          <el-select v-model="currentFilters.region" placeholder="全部大区" clearable filterable style="width: 120px">
            <el-option v-for="item in options.regions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="起始期间">
          <el-select v-model="currentFilters.startMonth" placeholder="请选择起始期间" clearable filterable style="width: 150px">
            <el-option v-for="item in options.startMonths" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="结束期间">
          <el-select v-model="currentFilters.endMonth" placeholder="请选择结束期间" clearable filterable style="width: 150px">
            <el-option v-for="item in options.startMonths" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetCurrentFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 内容区域 -->
    <div class="content-area" style="position: relative;">
      <component :is="currentComponent" :months="currentTabData.months" :params="currentFilters" @loaded="onComponentLoaded" />
    </div>

    <!-- Loading Overlay -->
    <Transition name="fade">
      <div v-if="loading" class="loading-overlay">
        <div class="loading-spinner">
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
        </div>
        <p class="loading-text">加载中...</p>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { useFilterStore } from '@/stores/filter'
import {
  getSalesDashboard,
  getCustomerTier,
  getPromotedPenetration,
  getCategoryDistribution
} from '@/api/sales'

import Overview from './dashboard/Overview.vue'
import RegionProgress from './dashboard/RegionProgress.vue'
import CustomerAmount from './dashboard/CustomerAmount.vue'
import PromotedAmount from './dashboard/PromotedAmount.vue'
import PromotedPenetration from './dashboard/PromotedPenetration.vue'
import Category from './dashboard/Category.vue'

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const tabs = [
  { label: '出货概览', name: 'overview' },
  { label: '区域分解', name: 'region-progress' },
  { label: '客户分层', name: 'customer-amount' },
  { label: '主推品出货', name: 'promoted-amount' },
  { label: '主推品渗透', name: 'promoted-penetration' },
  { label: '品类分解', name: 'category' }
]

// 每个 tab 独立的筛选状态
const tabFilters = reactive({
  'overview': { region: null, startMonth: null, endMonth: null },
  'region-progress': { region: null, startMonth: null, endMonth: null },
  'customer-amount': { region: null, startMonth: null, endMonth: null },
  'promoted-amount': { region: null, startMonth: null, endMonth: null },
  'promoted-penetration': { region: null, startMonth: null, endMonth: null },
  'category': { region: null, startMonth: null, endMonth: null }
})

// 每个 tab 独立的数据
const tabData = reactive({
  'overview': { months: [] },
  'region-progress': { months: [] },
  'customer-amount': { months: [] },
  'promoted-amount': { months: [] },
  'promoted-penetration': { months: [] },
  'category': { months: [] }
})

const activeTab = ref('overview')
const loading = ref(false)
const loadedComponents = ref(new Set(['overview']))

const componentMap = {
  'overview': Overview,
  'region-progress': RegionProgress,
  'customer-amount': CustomerAmount,
  'promoted-amount': PromotedAmount,
  'promoted-penetration': PromotedPenetration,
  'category': Category
}

// 当前 tab 的筛选状态
const currentFilters = computed(() => tabFilters[activeTab.value])

// 当前 tab 的数据
const currentTabData = computed(() => tabData[activeTab.value])

const currentComponent = computed(() => componentMap[activeTab.value] || Overview)

const options = computed(() => filterStore.options)

function switchTab(tabName) {
  if (activeTab.value === tabName) return
  activeTab.value = tabName
}

function onComponentLoaded() {
  loadedComponents.value.add(activeTab.value)
  loading.value = false
}

async function loadData() {
  try {
    loading.value = true
    setLoading(true)
    const filters = currentFilters.value
    const params = {
      start_year_month: filters.startMonth,
      end_year_month: filters.endMonth,
      region: filters.region || undefined
    }

    const [dashboardRes, customerTierRes, promotedRes, categoryRes] = await Promise.all([
      getSalesDashboard(params),
      getCustomerTier(params),
      getPromotedPenetration({ start_month: filters.startMonth, end_month: filters.endMonth, region: filters.region || undefined }),
      getCategoryDistribution({ start_month: filters.startMonth, end_month: filters.endMonth, region: filters.region || undefined })
    ])

    const dashboardData = dashboardRes.data?.data || dashboardRes.data || {}
    const months = dashboardData.months || []

    // 为所有 tab 更新 months（使用同一个月份列表）
    Object.keys(tabData).forEach(key => {
      tabData[key].months = [...months]
    })

    loadedComponents.value.add(activeTab.value)
    loading.value = false
    setLoading(false)
  } catch (error) {
    console.error('加载数据失败:', error)
    loading.value = false
    setLoading(false)
  }
}

function resetCurrentFilters() {
  tabFilters[activeTab.value].region = null
  tabFilters[activeTab.value].startMonth = null
  tabFilters[activeTab.value].endMonth = null
  loadedComponents.value.delete(activeTab.value)
  loadData()
}

onMounted(async () => {
  await filterStore.fetchAllOptions()
  loadData()
})
</script>

<style scoped>
.dashboard {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.flow-filter {
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #f5f7fa;
  border-radius: 10px;
  border: 1px solid #ebeef5;
}

:deep(.el-form-item__label) {
  color: #606266;
  font-weight: 500;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00d9c0 0%, #06b6d4 100%);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0, 217, 192, 0.3);
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #00f5db 0%, #0891b2 100%);
  box-shadow: 0 6px 16px rgba(0, 217, 192, 0.4);
  transform: translateY(-1px);
}

:deep(.el-button) {
  border-radius: 8px;
  font-weight: 500;
}

.sub-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 20px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 10px;
  border: 1px solid #ebeef5;
}

.sub-tab-item {
  padding: 10px 18px;
  font-size: 13px;
  color: #606266;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.25s ease;
  font-weight: 500;
}

.sub-tab-item:hover {
  color: #00d9c0;
  background: rgba(0, 217, 192, 0.08);
}

.sub-tab-item.active {
  color: #fff;
  background: linear-gradient(135deg, #00d9c0 0%, #06b6d4 100%);
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0, 217, 192, 0.3);
}

.content-area {
  min-height: 400px;
}

/* Loading Overlay */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 100;
  border-radius: 12px;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  position: relative;
}

.spinner-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 3px solid transparent;
  border-top-color: #00d9c0;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-ring:nth-child(1) { animation-delay: 0s; }
.spinner-ring:nth-child(2) {
  animation-delay: 0.1s;
  border-top-color: #8b5cf6;
}
.spinner-ring:nth-child(3) {
  animation-delay: 0.2s;
  border-top-color: #06b6d4;
}
.spinner-ring:nth-child(4) {
  animation-delay: 0.3s;
  border-top-color: #8b5cf6;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  font-size: 14px;
  color: #606266;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
