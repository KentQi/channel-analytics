<template>
  <div class="customer-retention-overview">
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

    <!-- KPI 卡片 -->
    <div class="kpi-grid">
      <KpiCard label="总客户数" :value="metrics.total_customers" format-type="integer" :show-change="false" />
      <KpiCard label="客户留存率" :value="metrics.retentionRateValue" suffix="%" format-type="number" :decimals="1" :show-change="false" />
      <KpiCard label="活跃客户数" :value="metrics.active_customers" format-type="integer" :show-change="false" />
      <KpiCard label="流失客户数" :value="metrics.inactive_customers" format-type="integer" :show-change="false" />
    </div>

    <!-- 客户留存热力图 -->
    <div class="section-card">
      <div class="section-title">客户留存热力图</div>
      <v-chart :option="heatmapOption" style="height: 420px" autoresize />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HeatmapChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  VisualMapComponent,
  DataZoomComponent
} from 'echarts/components'
import KpiCard from '@/components/common/KpiCard.vue'
import { useFilterStore } from '@/stores/filter'
import { getCohortMatrix } from '@/api/repurchase'

use([
  CanvasRenderer,
  HeatmapChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  VisualMapComponent,
  DataZoomComponent
])

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const filters = reactive({
  months: 12,
  customerKeyword: '',
  region: null,
  manager: null
})

const filterOptions = reactive({
  regions: [],
  managers: []
})

const cohortMatrix = ref([])
const customerStats = ref([])
const metrics = reactive({
  total_customers: 0,
  active_customers: 0,
  inactive_customers: 0,
  retention_rate: '0%',
  retentionRateValue: 0
})

// ==================== 热力图 ====================
const heatmapOption = computed(() => {
  if (!cohortMatrix.value.length) return {}

  const offsetSet = new Set()
  cohortMatrix.value.forEach(row => {
    Object.keys(row).forEach(key => {
      if (key.startsWith('+') || key === '首月') offsetSet.add(key)
    })
  })

  const offsetCols = Array.from(offsetSet).sort((a, b) => {
    if (a === '首月') return -1
    if (b === '首月') return 1
    return parseInt(a.replace('+', '').replace('月', '')) - parseInt(b.replace('+', '').replace('月', ''))
  })

  const yLabels = cohortMatrix.value.map(r => r.first_month)
  const xLabels = offsetCols.map(c => c === '首月' ? '首月' : c)

  const data = []
  cohortMatrix.value.forEach((row, yi) => {
    offsetCols.forEach((col, xi) => {
      const val = row[col]
      if (val !== undefined && val !== null && val !== '') {
        data.push([xi, yi, Number(val)])
      }
    })
  })

  return {
    tooltip: {
      position: 'top',
      formatter: (params) => {
        return `${yLabels[params.value[1]]} / ${xLabels[params.value[0]]}<br/>留存率: ${params.value[2]}%`
      }
    },
    grid: {
      left: '10%',
      right: '12%',
      bottom: '12%',
      top: '5%',
      containLabel: true,
      splitLine: { show: false }
    },
    xAxis: {
      type: 'category',
      data: xLabels,
      splitArea: { show: false },
      axisLabel: { fontSize: 11 }
    },
    yAxis: {
      type: 'category',
      data: yLabels,
      splitArea: { show: false },
      axisLabel: { fontSize: 11 }
    },
    visualMap: {
      min: 0,
      max: 100,
      calculable: true,
      orient: 'vertical',
      right: 0,
      top: 'center',
      inRange: {
        color: ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#084594']
      }
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'inside', yAxisIndex: 0 }
    ],
    series: [{
      name: '留存率',
      type: 'heatmap',
      data: data,
      label: {
        show: true,
        formatter: (params) => params.value[2] !== '' ? params.value[2] : '',
        fontSize: 10,
        color: '#333'
      },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
      }
    }]
  }
})

async function loadCohortData() {
  try {
    setLoading(true)
    const params = { months: filters.months }
    if (filters.region) params.region = filters.region
    if (filters.manager) params.manager = filters.manager
    if (filters.customerKeyword) params.customer = filters.customerKeyword
    const res = await getCohortMatrix(params)
    const data = res.data?.data || res.data || {}
    cohortMatrix.value = data.cohort_matrix || []
    customerStats.value = data.customer_stats || []
    const m = data.metrics || {}
    metrics.total_customers = m.total_customers || 0
    metrics.active_customers = m.active_customers || 0
    metrics.inactive_customers = m.inactive_customers || 0
    metrics.retention_rate = m.retention_rate || '0%'
    const rateStr = String(metrics.retention_rate)
    metrics.retentionRateValue = parseFloat(rateStr) || 0
  } catch (e) {
    console.error('加载留存热力图失败:', e)
    cohortMatrix.value = []
    customerStats.value = []
  } finally {
    setLoading(false)
  }
}

function loadData() {
  loadCohortData()
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
.customer-retention-overview {
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

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
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
</style>
