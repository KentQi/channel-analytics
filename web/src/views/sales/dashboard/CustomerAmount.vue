<template>
  <div class="customer-amount">
    <h3 class="section-title-main">客户分层</h3>
    <div class="chart-section">
      <v-chart :option="chartOption" style="height: 350px" autoresize />
    </div>
    <div class="table-section">
      <el-table :data="tableData" size="small" stripe border>
        <el-table-column prop="等级" label="等级" width="100" fixed />
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
import { getCustomerTier } from '@/api/sales'

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
    const res = await getCustomerTier({
      start_year_month: props.params.startMonth,
      end_year_month: props.params.endMonth,
      region: props.params.region || undefined
    })
    const data = res.data?.data || res.data || {}

    if (data.tier_by_month && Object.keys(data.tier_by_month).length > 0) {
      const tierByMonth = data.tier_by_month
      const monthData = tierByMonth.amount_data || {}
      const tiers = data.tier_order || ['<5万', '5-10万', '10-20万', '20-50万', '50-100万', '>=100万']
      chartOption.value = buildChart(tiers, monthData)
      tableData.value = buildTable(tiers, monthData)
    }

    emit('loaded')
  } catch (error) {
    console.error('加载客户分层-出货金额分布失败:', error)
    emit('loaded')
  }
}

function buildChart(tiers, dataMap) {
  const months = props.months || []
  const colors = ['#d1c6c6', '#c4a0a0', '#bd7474', '#bd4141', '#a52626', '#851313']
  return {
    tooltip: { trigger: 'axis', formatter: function(params) {
      let total = 0
      let result = params[0].name + '<br/>'
      params.forEach(p => {
        total += (p.value || 0)
        result += p.marker + ' ' + p.seriesName + ': ' + (p.value || 0).toFixed(2) + ' 万元<br/>'
      })
      result += '<strong>合计: ' + total.toFixed(2) + ' 万元</strong><br/>'
      return result
    }},
    legend: { data: tiers, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '出货额(万元)', splitLine: { show: false } },
    series: tiers.map((tier, i) => ({
      name: tier,
      type: 'line',
      stack: '总量',
      areaStyle: {},
      data: (dataMap[tier] || []),
      itemStyle: { color: colors[i] }
    }))
  }
}

function buildTable(tiers, dataMap) {
  const months = props.months || []
  return tiers.map(tier => ({
    '等级': tier,
    ...Object.fromEntries(months.map((m, i) => [m, ((dataMap[tier]?.[i] || 0)).toFixed(2)]))
  }))
}
</script>

<style scoped>
.customer-amount {
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
