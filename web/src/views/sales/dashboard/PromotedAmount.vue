<template>
  <div class="promoted-amount">
    <h3 class="section-title-main">主推品出货</h3>
    <div class="chart-section">
      <v-chart :option="chartOption" style="height: 350px" autoresize />
    </div>
    <div class="table-section">
      <el-table :data="tableData" size="small" stripe border>
        <el-table-column prop="主推标记" label="主推标记" width="120" fixed />
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
import { getPromotedPenetration } from '@/api/sales'

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
    const res = await getPromotedPenetration({
      start_month: props.params.startMonth,
      end_month: props.params.endMonth,
      region: props.params.region || undefined
    })
    const data = res.data?.data || res.data || {}

    if (data.months && data.months.length > 0) {
      const amounts = data.amounts || {}
      chartOption.value = buildChart(data.months, amounts)
      tableData.value = buildTable(data.months, amounts)
    }

    emit('loaded')
  } catch (error) {
    console.error('加载主推品-出货金额分布失败:', error)
    emit('loaded')
  }
}

function getColor(flag) {
  const 红色系 = ['#722626', '#983e3e', '#b16161', '#be9191']
  const 灰色系 = ['#554343', '#856f6f', '#ada3a3']
  if (flag.includes('下午茶')) return 红色系[Math.floor(Math.random() * 红色系.length)]
  if (flag.includes('小狗')) return 灰色系[Math.floor(Math.random() * 灰色系.length)]
  return '#333333'
}

function buildChart(months, amounts) {
  const flags = Object.keys(amounts)
  const colorMap = {}
  flags.forEach(flag => { colorMap[flag] = getColor(flag) })

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
    legend: { data: flags, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '出货额(万元)', splitLine: { show: false } },
    series: flags.map(flag => ({
      name: flag,
      type: 'line',
      stack: '总量',
      areaStyle: {},
      data: amounts[flag].map(v => v / 10000),
      lineStyle: { width: 0.5, color: colorMap[flag] },
      itemStyle: { color: colorMap[flag] },
      emphasis: { focus: 'series' }
    }))
  }
}

function buildTable(months, amounts) {
  return Object.keys(amounts).map(flag => {
    const row = { '主推标记': flag }
    amounts[flag].forEach((v, i) => {
      row[months[i]] = (v / 10000).toFixed(2)
    })
    return row
  })
}
</script>

<style scoped>
.promoted-amount {
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
