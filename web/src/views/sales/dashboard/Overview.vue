<template>
  <div class="overview">
    <h3 class="section-title-main">出货概览</h3>
    <div class="chart-section">
      <v-chart :option="chartOption" style="height: 350px" autoresize />
    </div>
    <div class="table-section">
      <el-table :data="tableData" size="small" stripe border>
        <el-table-column prop="指标" label="" width="120" fixed />
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
import { BarChart, LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { getSalesDashboard } from '@/api/sales'

use([CanvasRenderer, BarChart, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

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

    if (data.table_data && data.table_data.length > 0) {
      const salesOverview = {
        targets: data.table_data.map(d => d.target),
        amounts: data.table_data.map(d => d.amount_wan),
        completionRates: data.table_data.map(d => d.completion_rate),
        yoy: data.table_data.map(d => d.yoy),
        mom: data.table_data.map(d => d.mom)
      }
      chartOption.value = buildChart(salesOverview)
      tableData.value = buildTable(salesOverview)
    }

    // 通知父组件加载完成
    emit('loaded')
  } catch (error) {
    console.error('加载出货情况失败:', error)
    emit('loaded')
  }
}

function buildChart(data) {
  const months = props.months || []
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['完成额', '指标完成率', '同比', '环比'], bottom: 0 },
    grid: { left: '3%', right: '8%', bottom: '12%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: [
      { type: 'value', name: '完成额(万元)', splitLine: { show: false } },
      { type: 'value', name: '完成率/同比/环比(%)', splitLine: { show: false } }
    ],
    series: [
      { name: '完成额', type: 'bar', data: data.amounts || [], itemStyle: { color: '#595959' } },
      { name: '指标完成率', type: 'line', yAxisIndex: 1, data: data.completionRates || [], itemStyle: { color: '#e74c3c' } },
      { name: '同比', type: 'line', yAxisIndex: 1, data: data.yoy || [], itemStyle: { color: '#0077cc' }, symbol: 'diamond' },
      { name: '环比', type: 'line', yAxisIndex: 1, data: data.mom || [], itemStyle: { color: '#27ae60' }, symbol: 'triangle' }
    ]
  }
}

function buildTable(data) {
  const months = props.months || []
  return [{
    '指标': '指标(万元)',
    ...Object.fromEntries(months.map((m, i) => [m, data.targets?.[i]?.toFixed(2) || '-']))
  }, {
    '指标': '完成额(万元)',
    ...Object.fromEntries(months.map((m, i) => [m, data.amounts?.[i]?.toFixed(2) || '-']))
  }, {
    '指标': '完成率(%)',
    ...Object.fromEntries(months.map((m, i) => [m, data.completionRates?.[i] || '-']))
  }, {
    '指标': '同比(%)',
    ...Object.fromEntries(months.map((m, i) => [m, data.yoy?.[i] || '-']))
  }, {
    '指标': '环比(%)',
    ...Object.fromEntries(months.map((m, i) => [m, data.mom?.[i] || '-']))
  }]
}
</script>

<style scoped>
.overview {
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
