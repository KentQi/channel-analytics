<template>
  <div class="product-cluster">
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
        <span class="filter-label">聚类数</span>
        <el-select v-model="filters.n_clusters" style="width: 100px" @change="loadData">
          <el-option :value="3" label="3 类" />
          <el-option :value="4" label="4 类" />
          <el-option :value="5" label="5 类" />
          <el-option :value="6" label="6 类" />
        </el-select>
      </div>
    </div>

    <!-- KPI卡片 -->
    <div class="kpi-row">
      <KpiCard label="总SKU数" :value="metrics.total_skus || 0" format-type="integer" :show-change="false" />
      <KpiCard v-for="cluster in clusterSummary" :key="cluster.cluster_id"
        :label="cluster.cluster_label" :value="cluster.count" format-type="integer" :show-change="false" />
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">聚类散点图</div>
        <v-chart :option="scatterOption" style="height: 320px" autoresize />
      </div>
      <div class="chart-card">
        <div class="chart-title">聚类特征雷达图</div>
        <v-chart :option="radarOption" style="height: 320px" autoresize />
      </div>
    </div>

    <!-- 聚类规模柱状图 -->
    <div class="chart-card" style="margin-bottom: 16px;">
      <div class="chart-title">聚类规模分布</div>
      <v-chart :option="barOption" style="height: 200px" autoresize />
    </div>

    <!-- 表格 -->
    <div class="section-card">
      <div class="section-title">商品聚类明细</div>
      <el-table :data="tableData" stripe border size="small" max-height="400">
        <el-table-column prop="material_code" label="物料编码" width="110" fixed show-overflow-tooltip />
        <el-table-column prop="material_name" label="物料名称" min-width="140" fixed show-overflow-tooltip />
        <el-table-column prop="cluster_label" label="聚类标签" width="100" align="center">
          <template #default="{ row }">
            <span :style="{ color: getClusterColor(row.cluster_label) }">{{ row.cluster_label }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_amount" label="累计销售额" width="120" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.total_amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_qty" label="累计销量" width="100" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.total_qty) }}
          </template>
        </el-table-column>
        <el-table-column prop="avg_monthly_qty" label="月均销量" width="100" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.avg_monthly_qty) }}
          </template>
        </el-table-column>
        <el-table-column prop="customer_count" label="客户数" width="80" align="right" />
        <el-table-column prop="avg_price" label="平均单价" width="100" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.avg_price) }}
          </template>
        </el-table-column>
        <el-table-column prop="volatility" label="波动系数" width="90" align="right">
          <template #default="{ row }">
            {{ row.volatility !== null ? row.volatility.toFixed(2) : '-' }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { getProductCluster } from '@/api/advanced'
import KpiCard from '@/components/common/KpiCard.vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { ScatterChart, RadarChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, ScatterChart, RadarChart, BarChart, TitleComponent, TooltipComponent, LegendComponent])

const setLoading = inject('setLoading', () => {})

const filters = reactive({
  months: 18,
  n_clusters: 4,
})

const tableData = ref([])
const clusterSummary = ref([])
const radarData = ref([])
const featureNames = ref([])
const metrics = ref({})

const clusterColors = ['#67C23A', '#409EFF', '#E6A23C', '#F56C6C', '#909399', '#8b5cf6']

function getClusterColor(label) {
  const colors = {
    '明星商品': '#67C23A',
    '现金牛': '#409EFF',
    '问题商品': '#E6A23C',
    '瘦狗商品': '#F56C6C',
    '一般商品': '#909399',
  }
  return colors[label] || '#909399'
}

function formatNumber(val) {
  if (val === null || val === undefined) return '-'
  return Number(val).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

const scatterOption = computed(() => {
  const series = clusterSummary.value.map((cluster, idx) => ({
    name: cluster.cluster_label,
    type: 'scatter',
    data: tableData.value
      .filter(row => row.cluster_label === cluster.cluster_label)
      .map(row => [row.total_amount, row.avg_monthly_qty, row.customer_count]),
    symbolSize: (val) => Math.sqrt(val[2]) * 3,
    itemStyle: { color: clusterColors[idx % clusterColors.length], opacity: 0.7 },
  }))

  return {
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.seriesName}<br/>销售额: ${formatNumber(p.data[0])}<br/>月均销量: ${formatNumber(p.data[1])}<br/>客户数: ${p.data[2]}`
    },
    legend: { bottom: 0 },
    xAxis: { type: 'value', name: '累计销售额', scale: true },
    yAxis: { type: 'value', name: '月均销量', scale: true },
    series,
  }
})

const radarOption = computed(() => {
  const indicators = featureNames.value.map((name) => ({
    name,
    max: 1,
  }))

  const series = radarData.value.map((rd, idx) => ({
    name: rd.cluster_label,
    type: 'radar',
    data: [{ value: rd.values, name: rd.cluster_label }],
    itemStyle: { color: clusterColors[idx % clusterColors.length] },
  }))

  return {
    tooltip: {},
    legend: { bottom: 0 },
    radar: { indicator: indicators },
    series,
  }
})

const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: clusterSummary.value.map(c => c.cluster_label) },
  yAxis: { type: 'value', name: '商品数' },
  series: [{
    type: 'bar',
    data: clusterSummary.value.map((c, idx) => ({
      value: c.count,
      itemStyle: { color: clusterColors[idx % clusterColors.length] },
    })),
  }],
}))

async function loadData() {
  try {
    setLoading(true)
    const params = { months: filters.months, n_clusters: filters.n_clusters }

    const res = await getProductCluster(params)
    const data = res.data?.data || res.data || {}
    tableData.value = data.cluster_data || []
    clusterSummary.value = data.cluster_summary || []
    radarData.value = data.radar_data || []
    featureNames.value = data.feature_names || []
    metrics.value = data.metrics || {}
  } catch (e) {
    console.error('加载商品聚类数据失败:', e)
    tableData.value = []
    clusterSummary.value = []
    radarData.value = []
    metrics.value = {}
  } finally {
    setLoading(false)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.product-cluster { padding: 0; }

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
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
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
