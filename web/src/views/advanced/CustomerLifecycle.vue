<template>
  <div class="customer-lifecycle">
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
    </div>

    <!-- KPI卡片 -->
    <div class="kpi-row">
      <KpiCard label="总客户数" :value="metrics.total_customers || 0" format-type="integer" :show-change="false" />
      <KpiCard label="新客户" :value="metrics.new_count || 0" format-type="integer" :show-change="false" />
      <KpiCard label="成长客户" :value="metrics.growth_count || 0" format-type="integer" :show-change="false" />
      <KpiCard label="成熟客户" :value="metrics.mature_count || 0" format-type="integer" :show-change="false" />
      <KpiCard label="衰退客户" :value="metrics.decline_count || 0" format-type="integer" :show-change="false" />
      <KpiCard label="流失客户" :value="metrics.churned_count || 0" format-type="integer" :show-change="false" />
      <KpiCard label="平均CLV" :value="metrics.avg_clv || 0" format-type="currency" :show-change="false" />
    </div>

    <!-- 热力图：客户阶段 × 品类 -->
    <div class="chart-card" v-if="crossTab.stages.length > 0">
      <div class="chart-header">
        <div class="chart-title">客户阶段 × 品类分布</div>
        <el-radio-group v-model="heatMode" size="small" @change="updateHeatmap">
          <el-radio-button value="customer">客户数</el-radio-button>
          <el-radio-button value="amount">金额</el-radio-button>
        </el-radio-group>
      </div>
      <v-chart :option="heatmapOption" style="height: 320px" autoresize />
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">客户生命周期阶段分布</div>
        <v-chart :option="pieOption" style="height: 300px" autoresize />
      </div>
      <div class="chart-card">
        <div class="chart-title">CLV分布</div>
        <v-chart :option="barOption" style="height: 300px" autoresize />
      </div>
    </div>

    <!-- 表格 -->
    <div class="section-card">
      <div class="section-title">客户生命周期明细</div>
      <el-table :data="tableData" stripe border size="small" max-height="400">
        <el-table-column prop="customer" label="客户名称" min-width="150" fixed show-overflow-tooltip />
        <el-table-column prop="stage" label="生命周期阶段" width="100" align="center">
          <template #default="{ row }">
            <span :style="{ color: getStageColor(row.stage) }">{{ row.stage }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="r" label="R(最近购买天数)" width="130" align="right" />
        <el-table-column prop="f" label="F(购买次数)" width="100" align="right" />
        <el-table-column prop="m" label="M(累计金额)" width="120" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.m) }}
          </template>
        </el-table-column>
        <el-table-column prop="r_score" label="R评分" width="70" align="center" />
        <el-table-column prop="f_score" label="F评分" width="70" align="center" />
        <el-table-column prop="m_score" label="M评分" width="70" align="center" />
        <el-table-column prop="clv" label="CLV" width="120" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.clv) }}
          </template>
        </el-table-column>
        <el-table-column prop="avg_order_value" label="客单价" width="100" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.avg_order_value) }}
          </template>
        </el-table-column>
        <el-table-column prop="category_count" label="品类数" width="80" align="right" />
        <el-table-column prop="last_purchase_date" label="最近购买" width="110" align="center" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { getCustomerLifecycle } from '@/api/advanced'
import KpiCard from '@/components/common/KpiCard.vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart, HeatmapChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent } from 'echarts/components'

use([CanvasRenderer, PieChart, BarChart, HeatmapChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent])

const setLoading = inject('setLoading', () => {})

const filters = reactive({
  months: 18,
})

const tableData = ref([])
const metrics = ref({})
const crossTab = ref({ stages: [], categories: [], customer_matrix: [], amount_matrix: [] })
const heatMode = ref('customer')

function getStageColor(stage) {
  const colors = {
    '新客户': '#409EFF',
    '成长客户': '#67C23A',
    '成熟客户': '#E6A23C',
    '衰退客户': '#F56C6C',
    '流失客户': '#909399',
    '一般客户': '#909399',
  }
  return colors[stage] || '#909399'
}

function formatNumber(val) {
  if (val === null || val === undefined) return '-'
  return Number(val).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

// 热力图
const heatmapOption = computed(() => {
  const ct = crossTab.value
  if (!ct.stages.length || !ct.categories.length) return {}

  const matrix = heatMode.value === 'customer' ? ct.customer_matrix : ct.amount_matrix
  const isAmount = heatMode.value === 'amount'

  // 构造 data: [x, y, value]
  const data = []
  let maxVal = 0
  for (let yi = 0; yi < ct.stages.length; yi++) {
    for (let xi = 0; xi < ct.categories.length; xi++) {
      const v = (matrix[yi] && matrix[yi][xi]) || 0
      data.push([xi, yi, v])
      if (v > maxVal) maxVal = v
    }
  }

  return {
    tooltip: {
      formatter(params) {
        const cat = ct.categories[params.value[0]] || ''
        const stage = ct.stages[params.value[1]] || ''
        const val = params.value[2]
        const label = isAmount ? `金额: ¥${Number(val).toLocaleString()}` : `客户数: ${val}`
        return `${stage} × ${cat}<br/>${label}`
      },
    },
    grid: { left: 80, right: 30, top: 10, bottom: 60 },
    xAxis: {
      type: 'category',
      data: ct.categories,
      axisLabel: { rotate: ct.categories.length > 6 ? 45 : 0, fontSize: 11 },
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: ct.stages,
      axisLabel: { fontSize: 11 },
      splitArea: { show: true },
    },
    visualMap: {
      min: 0,
      max: maxVal || 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#f0f5ff', '#d6e4ff', '#adc6ff', '#85a5ff', '#597ef7', '#2f54eb', '#1d39c4'] },
      text: isAmount ? ['高金额', '低金额'] : ['多', '少'],
    },
    series: [{
      type: 'heatmap',
      data,
      label: { show: true, fontSize: 10, formatter: (p) => isAmount ? (p.value[2] >= 10000 ? (p.value[2] / 10000).toFixed(1) + 'w' : p.value[2]) : p.value[2] },
      emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0, 0, 0, 0.3)' } },
    }],
  }
})

function updateHeatmap() {
  // 触发 computed 重算（vue 自动响应 heatMode 变化）
}

// 饼图
const pieOption = computed(() => {
  const data = [
    { name: '新客户', value: metrics.value.new_count || 0 },
    { name: '成长客户', value: metrics.value.growth_count || 0 },
    { name: '成熟客户', value: metrics.value.mature_count || 0 },
    { name: '衰退客户', value: metrics.value.decline_count || 0 },
    { name: '流失客户', value: metrics.value.churned_count || 0 },
  ].filter(d => d.value > 0)

  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 10, left: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}: {c}' },
      data,
      color: ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399'],
    }],
  }
})

// CLV 柱状图
const barOption = computed(() => {
  const clvRanges = [
    { label: '0-10k', min: 0, max: 10000 },
    { label: '10k-50k', min: 10000, max: 50000 },
    { label: '50k-100k', min: 50000, max: 100000 },
    { label: '100k+', min: 100000, max: Infinity },
  ]
  const counts = clvRanges.map(range => {
    return tableData.value.filter(row => {
      const clv = row.clv || 0
      return clv >= range.min && clv < range.max
    }).length
  })

  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: clvRanges.map(r => r.label) },
    yAxis: { type: 'value', name: '客户数' },
    series: [{
      type: 'bar',
      data: counts,
      itemStyle: { color: '#409EFF', borderRadius: [4, 4, 0, 0] },
    }],
  }
})

async function loadData() {
  try {
    setLoading(true)
    const params = { months: filters.months }

    const res = await getCustomerLifecycle(params)
    const data = res.data?.data || res.data || {}
    tableData.value = data.customer_data || []
    metrics.value = data.metrics || {}
    crossTab.value = data.cross_tab || { stages: [], categories: [], customer_matrix: [], amount_matrix: [] }
  } catch (e) {
    console.error('加载客户生命周期数据失败:', e)
    tableData.value = []
    metrics.value = {}
    crossTab.value = { stages: [], categories: [], customer_matrix: [], amount_matrix: [] }
  } finally {
    setLoading(false)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.customer-lifecycle { padding: 0; }

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

.filter-item { display: flex; align-items: center; gap: 8px; }
.filter-label { font-size: 13px; color: #606266; white-space: nowrap; }

.kpi-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.chart-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #ebeef5;
  margin-bottom: 16px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.section-card {
  background-color: #fff;
  border-radius: 6px;
  padding: 16px;
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
