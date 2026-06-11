<template>
  <div class="promoted-penetration">
    <h3 class="section-title-main">主推品渗透</h3>
    <div class="chart-section">
      <v-chart :option="chartOption" style="height: 350px" autoresize />
    </div>
    <div class="table-section">
      <el-table :data="tableData" size="small" stripe border>
        <el-table-column prop="分组" label="分组" width="100" fixed />
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
import { getPromotedPenetration } from '@/api/sales'

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
    const res = await getPromotedPenetration({
      start_month: props.params.startMonth,
      end_month: props.params.endMonth,
      region: props.params.region || undefined
    })
    const data = res.data?.data || res.data || {}

    if (data.months && data.months.length > 0) {
      const customers = data.customers || {}
      const penetration = data.penetration || {}
      chartOption.value = buildChart(data.months, customers, penetration)
      tableData.value = buildTable(data.months, customers)
    }

    emit('loaded')
  } catch (error) {
    console.error('加载主推品-渗透情况失败:', error)
    emit('loaded')
  }
}

function getColor(flag) {
  if (flag.includes('下午茶')) return '#983e3e'
  if (flag.includes('小狗')) return '#856f6f'
  return '#333333'
}

function buildChart(months, customers, penetration) {
  const flags = Object.keys(customers)
  const barSeries = flags.map(flag => ({
    name: flag,
    type: 'bar',
    data: customers[flag],
    itemStyle: { color: getColor(flag) }
  }))
  const lineFlags = flags.filter(f => f.includes('下午茶') || f.includes('小狗'))
  const lineSeries = lineFlags.map(flag => ({
    name: flag + '渗透率',
    type: 'line',
    yAxisIndex: 1,
    data: penetration[flag] || [],
    lineStyle: { color: getColor(flag), width: 2 },
    symbol: 'circle',
    symbolSize: 6
  }))
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: [...flags, ...lineFlags.map(f => f + '渗透率')], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: [
      { type: 'value', name: '客户数', splitLine: { show: false } },
      { type: 'value', name: '渗透率(%)', splitLine: { show: false }, max: 105 }
    ],
    series: [...barSeries, ...lineSeries]
  }
}

function buildTable(months, customers) {
  return Object.keys(customers).map(flag => {
    const row = { '分组': flag }
    customers[flag].forEach((v, i) => {
      row[months[i]] = v
    })
    return row
  })
}
</script>

<style scoped>
.promoted-penetration {
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
