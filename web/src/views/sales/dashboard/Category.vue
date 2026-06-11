<template>
  <div class="category">
    <h3 class="section-title-main">品类分解</h3>
    <div class="chart-section">
      <v-chart :option="chartOption" style="height: 350px" autoresize />
    </div>
    <div class="table-section">
      <el-table :data="tableData" size="small" stripe border>
        <el-table-column prop="品类" label="品类" width="120" fixed />
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
import { BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { getCategoryDistribution } from '@/api/sales'

use([CanvasRenderer, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

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
    const res = await getCategoryDistribution({
      start_month: props.params.startMonth,
      end_month: props.params.endMonth,
      region: props.params.region || undefined
    })
    const data = res.data?.data || res.data || {}

    if (data.months && data.months.length > 0) {
      const categories = data.categories || {}
      chartOption.value = buildChart(data.months, categories)
      tableData.value = buildTable(data.months, categories)
    }

    emit('loaded')
  } catch (error) {
    console.error('加载品类-出货分布失败:', error)
    emit('loaded')
  }
}

function buildChart(months, categories) {
  const catNames = Object.keys(categories)
  const colors = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f', '#e5c494', '#b3b3b3']
  return {
    tooltip: { trigger: 'axis', formatter: function(params) {
      let result = params[0].name + '<br/>'
      let total = 0
      params.forEach(p => {
        total += p.value
        result += p.marker + ' ' + p.seriesName + ': ' + (p.value || 0).toFixed(2) + ' 万元<br/>'
      })
      result += '<strong>合计: ' + total.toFixed(2) + ' 万元</strong>'
      return result
    }},
    legend: { data: catNames, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '出货额(万元)', splitLine: { show: false } },
    series: catNames.map((cat, i) => ({
      name: cat,
      type: 'bar',
      stack: '总量',
      data: categories[cat].map(v => v / 10000),
      itemStyle: { color: colors[i % colors.length] }
    }))
  }
}

function buildTable(months, categories) {
  return Object.keys(categories).map(cat => {
    const row = { '品类': cat }
    categories[cat].forEach((v, i) => {
      row[months[i]] = (v / 10000).toFixed(2)
    })
    return row
  })
}
</script>

<style scoped>
.category {
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
