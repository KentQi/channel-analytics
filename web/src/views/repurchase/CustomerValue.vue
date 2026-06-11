<template>
  <div class="customer-value">
    <!-- 筛选器 -->
    <div class="filter-bar">
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

    <!-- 客户价值散点图 -->
    <div class="section-card">
      <div class="section-title">客户价值散点图</div>
      <v-chart :option="scatterOption" style="height: 500px" autoresize />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { ScatterChart, LineChart } from 'echarts/charts'
import {
  TooltipComponent,
  GridComponent,
  DataZoomComponent,
  LegendComponent
} from 'echarts/components'
import { useFilterStore } from '@/stores/filter'
import { getCustomerValueScatter } from '@/api/repurchase'

use([
  CanvasRenderer,
  ScatterChart,
  LineChart,
  TooltipComponent,
  GridComponent,
  DataZoomComponent,
  LegendComponent
])

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const filters = reactive({
  customerKeyword: '',
  region: null,
  manager: null
})

const filterOptions = reactive({
  regions: [],
  managers: []
})

const scatterData = ref([])

const scatterOption = computed(() => {
  if (!scatterData.value.length) return {}

  const activeData = scatterData.value.filter(d => d.active_60d === '是').map(d => [d.order_count, d.total_amount, d.customer])
  const inactiveData = scatterData.value.filter(d => d.active_60d === '否').map(d => [d.order_count, d.total_amount, d.customer])

  const allOrderCounts = scatterData.value.map(d => d.order_count)
  const allTotalAmounts = scatterData.value.map(d => d.total_amount)
  const orderCount75 = percentile(allOrderCounts, 75)
  const totalAmount75 = percentile(allTotalAmounts, 75)
  const maxOrderCount = Math.max(...allOrderCounts)
  const maxTotalAmount = Math.max(...allTotalAmounts)

  return {
    tooltip: {
      formatter: (params) => {
        const seriesName = params.seriesName
        return `${seriesName}<br/>客户: ${params.value[2]}<br/>订单数: ${params.value[0]}<br/>累计金额: ¥${formatAmount(params.value[1])}`
      }
    },
    legend: {
      data: ['60天内进货: 是', '60天内进货: 否'],
      top: 0
    },
    grid: {
      left: '5%',
      right: '5%',
      bottom: '12%',
      containLabel: true
    },
    xAxis: {
      name: '累计订单数量',
      nameLocation: 'center',
      nameGap: 30,
      type: 'value',
      splitLine: { show: false }
    },
    yAxis: {
      name: '累计金额',
      nameLocation: 'center',
      nameGap: 50,
      type: 'value',
      splitLine: { show: false },
      axisLabel: {
        formatter: (val) => val >= 10000 ? (val / 10000).toFixed(0) + '万' : val
      }
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'inside', yAxisIndex: 0 }
    ],
    series: [
      {
        name: '60天内进货: 是',
        type: 'scatter',
        data: activeData,
        symbolSize: 8,
        itemStyle: { color: '#2171b5', opacity: 0.7 }
      },
      {
        name: '60天内进货: 否',
        type: 'scatter',
        data: inactiveData,
        symbolSize: 8,
        itemStyle: { color: '#e9403a', opacity: 0.7 }
      },
      {
        name: '金额75%分位线',
        type: 'line',
        symbol: 'none',
        lineStyle: { color: 'green', type: 'dashed', width: 1 },
        label: { show: false },
        legend: { show: false },
        data: [[0, totalAmount75], [maxOrderCount, totalAmount75]],
        tooltip: { show: false }
      },
      {
        name: '订单数75%分位线',
        type: 'line',
        symbol: 'none',
        lineStyle: { color: 'green', type: 'dashed', width: 1 },
        label: { show: false },
        legend: { show: false },
        data: [[orderCount75, 0], [orderCount75, maxTotalAmount]],
        tooltip: { show: false }
      }
    ]
  }
})

function formatAmount(val) {
  if (val === null || val === undefined) return '0'
  const num = Number(val)
  if (isNaN(num)) return '0'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function percentile(arr, p) {
  if (!arr || arr.length === 0) return 0
  const sorted = [...arr].sort((a, b) => a - b)
  const index = (p / 100) * (sorted.length - 1)
  const lower = Math.floor(index)
  const upper = Math.ceil(index)
  if (lower === upper) return sorted[lower]
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower)
}

async function loadData() {
  try {
    setLoading(true)
    const params = {}
    if (filters.region) params.region = filters.region
    if (filters.manager) params.manager = filters.manager
    if (filters.customerKeyword) params.customer = filters.customerKeyword
    const res = await getCustomerValueScatter(params)
    const data = res.data?.data || res.data || {}
    scatterData.value = data.scatter_data || []
  } catch (e) {
    console.error('加载客户价值散点图失败:', e)
    scatterData.value = []
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
.customer-value {
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
</style>
