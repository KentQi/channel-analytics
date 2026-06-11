<template>
  <div class="region-progress">
    <h3 class="section-title-main">区域分解</h3>
    <div class="chart-section">
      <v-chart :option="chartOption" style="height: 350px" autoresize />
    </div>
    <div class="table-section">
      <el-table :data="tableData" size="small" stripe border>
        <el-table-column prop="系列" label="系列" width="150" fixed />
        <el-table-column v-for="month in months" :key="month" :prop="month" :label="month" align="center" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { getSalesDashboard } from '@/api/sales'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const props = defineProps({
  months: {
    type: Array,
    default: () => []
  },
  params: {
    type: Object,
    default: () => ({ startMonth: null, endMonth: null })
  }
})

const emit = defineEmits(['loaded'])

const chartOption = ref({})
const tableData = ref([])

watch([() => props.months, () => props.params], ([newMonths, newParams]) => {
  if (newMonths && newMonths.length > 0) {
    loadData()
  }
}, { immediate: true })

async function loadData() {
  try {
    const res = await getSalesDashboard({
      start_year_month: props.params.startMonth,
      end_year_month: props.params.endMonth,
      region: props.params.region || undefined
    })
    const data = res.data?.data || res.data || {}

    if (data.region_data && data.region_data.length > 0) {
      const progress = buildProgressData(data.region_data, props.months)
      chartOption.value = buildChart(progress)
      tableData.value = buildTable(progress)
    }

    emit('loaded')
  } catch (error) {
    console.error('加载分大区出货进度失败:', error)
    emit('loaded')
  }
}

function buildProgressData(rawData, months) {
  if (!rawData || !rawData.length) return { names: [], series: [] }
  const regionNames = [...new Set(rawData.map(d => d.region).filter(Boolean))].slice(0, 10)
  const monthRegionMap = {}
  rawData.forEach(d => {
    if (!monthRegionMap[d.year_month]) {
      monthRegionMap[d.year_month] = {}
    }
    if (d.region && d.amount) {
      monthRegionMap[d.year_month][d.region] = (monthRegionMap[d.year_month][d.region] || 0) + d.amount
    }
  })
  const series = regionNames.map(name => ({
    name: name,
    data: months.map(m => monthRegionMap[m]?.[name] || 0)
  }))
  return { names: regionNames, series }
}

function buildChart(data) {
  const months = props.months || []
  const colors = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f', '#e5c494', '#b3b3b3']
  return {
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        let total = 0
        let result = params[0].name + '<br/>'
        params.forEach(p => {
          total += (p.value || 0)
          result += p.marker + ' ' + p.seriesName + ': ' + (p.value || 0).toFixed(2) + ' 万元<br/>'
        })
        result += '<strong>合计: ' + total.toFixed(2) + ' 万元</strong><br/>'
        return result
      }
    },
    legend: { data: data.names || [], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '出货额(万元)', splitLine: { show: false } },
    series: data.series.map((s, i) => ({
      name: s.name,
      type: 'line',
      stack: '总量',
      areaStyle: {},
      data: s.data.map(v => v / 10000),
      lineStyle: { color: colors[i % colors.length] },
      itemStyle: { color: colors[i % colors.length] }
    }))
  }
}

function buildTable(data) {
  const months = props.months || []
  return (data.series || []).map(s => ({
    '系列': s.name,
    ...Object.fromEntries(months.map((m, i) => [m, ((s.data?.[i] || 0) / 10000).toFixed(2)]))
  }))
}
</script>

<style scoped>
.region-progress {
  padding: 16px;
}

.section-title-main {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.chart-section {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 16px;
  min-height: 350px;
  width: 100%;
  box-sizing: border-box;
}

.table-section {
  margin-bottom: 24px;
}

.table-section :deep(.el-table) {
  font-size: 12px;
}

.table-section :deep(.el-table__header) {
  font-weight: 600;
}
</style>
