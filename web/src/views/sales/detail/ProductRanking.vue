<template>
  <div class="product-ranking">
    <div class="flow-filter">
      <el-form inline :model="filterStore.salesDetail">
        <el-form-item label="日期范围">
          <el-date-picker v-model="filterStore.salesDetail.dateRange" type="daterange" range-separator="~" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 220px" />
        </el-form-item>
        <el-form-item label="大区">
          <el-select v-model="filterStore.salesDetail.region" placeholder="请选择大区" clearable filterable style="width: 150px">
            <el-option v-for="item in options.regions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户">
          <el-select v-model="filterStore.salesDetail.customer" placeholder="请选择客户" clearable filterable style="width: 180px">
            <el-option v-for="item in options.customers" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button text @click="expanded = !expanded">
            {{ expanded ? '收起' : '更多' }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
        </el-form-item>
      </el-form>
      <el-form v-show="expanded" inline :model="filterStore.salesDetail" class="more-filters">
        <el-form-item label="商品品类">
          <el-select v-model="filterStore.salesDetail.category" placeholder="请选择品类" clearable filterable style="width: 120px">
            <el-option v-for="item in options.categories" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="ABC分类">
          <el-select v-model="filterStore.salesDetail.abcClass" placeholder="请选择" clearable filterable style="width: 100px">
            <el-option v-for="item in options.abcClasses" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="物料编码">
          <el-select v-model="filterStore.salesDetail.materialCode" placeholder="请选择" clearable filterable style="width: 150px">
            <el-option v-for="item in options.materialCodes" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户经理">
          <el-select v-model="filterStore.salesDetail.manager" placeholder="请选择客户经理" clearable filterable style="width: 150px">
            <el-option v-for="item in options.managers" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <div class="chart-section">
      <v-chart ref="chartRef" :option="chartOption" style="height: 400px" autoresize />
    </div>

    <div class="section-header" style="justify-content: flex-end; margin-top: 16px;">
      <el-button type="primary" size="small" :icon="Download" @click="handleExport">导出</el-button>
    </div>

    <el-table :data="tableData" size="small" stripe border>
      <el-table-column type="index" label="排名" width="60" align="center" />
      <el-table-column prop="materialCode" label="物料编码" width="130" />
      <el-table-column prop="materialName" label="物料名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="salesAmount" label="含税金额合计（万元）" width="120" align="right">
        <template #default="{ row }">
          {{ row.salesAmount?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="yoyAmountChange" label="YoY变动额（万元）" width="120" align="right">
        <template #default="{ row }">
          {{ row.yoyAmountChange?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="momAmountChange" label="MoM变动额（万元）" width="120" align="right">
        <template #default="{ row }">
          {{ row.momAmountChange?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="yoyAmountDiff" label="金额YoY（%）" width="90" align="center">
        <template #default="{ row }">
          <span :style="{ color: row.yoyAmountDiff >= 0 ? '#f56c6c' : '#67c23a' }">
            {{ row.yoyAmountDiff > 0 ? '↑' : row.yoyAmountDiff < 0 ? '↓' : '-' }}{{ Math.abs(row.yoyAmountDiff || 0).toFixed(1) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="momAmountDiff" label="金额MoM（%）" width="90" align="center">
        <template #default="{ row }">
          <span :style="{ color: row.momAmountDiff >= 0 ? '#f56c6c' : '#67c23a' }">
            {{ row.momAmountDiff > 0 ? '↑' : row.momAmountDiff < 0 ? '↓' : '-' }}{{ Math.abs(row.momAmountDiff || 0).toFixed(1) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="marketShare" label="金额占比（%）" width="90" align="center" />
      <el-table-column prop="salesQty" label="数量合计" width="80" align="right">
        <template #default="{ row }">
          {{ Number(row.salesQty).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column prop="yoyQtyDiff" label="YoY变动量" width="80" align="right">
        <template #default="{ row }">
          {{ Number(row.yoyQtyDiff).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column prop="momQtyDiff" label="MoM变动量" width="80" align="right">
        <template #default="{ row }">
          {{ Number(row.momQtyDiff).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column prop="qtyYoyPct" label="数量YoY（%）" width="90" align="center">
        <template #default="{ row }">
          <span :style="{ color: row.qtyYoyPct >= 0 ? '#f56c6c' : '#67c23a' }">
            {{ row.qtyYoyPct > 0 ? '↑' : row.qtyYoyPct < 0 ? '↓' : '-' }}{{ Math.abs(row.qtyYoyPct || 0).toFixed(1) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="qtyMomPct" label="数量MoM（%）" width="90" align="center">
        <template #default="{ row }">
          <span :style="{ color: row.qtyMomPct >= 0 ? '#f56c6c' : '#67c23a' }">
            {{ row.qtyMomPct > 0 ? '↑' : row.qtyMomPct < 0 ? '↓' : '-' }}{{ Math.abs(row.qtyMomPct || 0).toFixed(1) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="qtyShare" label="数量占比（%）" width="90" align="center" />
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { TreemapChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { Download, ArrowDown } from '@element-plus/icons-vue'
import { useFilterStore } from '@/stores/filter'
import { getSalesDetail } from '@/api/sales'

use([CanvasRenderer, TreemapChart, TooltipComponent])

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const options = computed(() => filterStore.options)
const loading = ref(false)
const expanded = ref(false)
const chartRef = ref(null)

const tableData = ref([])
const chartOption = ref({})

function getTreemapColor(value, dataArray) {
  const values = dataArray.map(d => d.salesAmount || 0).filter(v => v > 0)
  if (values.length === 0) return '#f5f5f5'
  const max = Math.max(...values)
  const min = Math.min(...values)
  const range = max - min
  if (range === 0) return 'rgb(217,217,217)'
  const ratio = (value - min) / range
  const colors = [
    { pos: 0.0, r: 255, g: 255, b: 255 },
    { pos: 0.2, r: 240, g: 240, b: 240 },
    { pos: 0.4, r: 255, g: 200, b: 200 },
    { pos: 0.6, r: 255, g: 150, b: 150 },
    { pos: 0.8, r: 255, g: 100, b: 100 },
    { pos: 1.0, r: 255, g: 50, b: 50 }
  ]
  for (let i = 0; i < colors.length - 1; i++) {
    if (ratio >= colors[i].pos && ratio <= colors[i + 1].pos) {
      const t = (ratio - colors[i].pos) / (colors[i + 1].pos - colors[i].pos)
      const r = Math.round(colors[i].r + (colors[i + 1].r - colors[i].r) * t)
      const g = Math.round(colors[i].g + (colors[i + 1].g - colors[i].g) * t)
      const b = Math.round(colors[i].b + (colors[i + 1].b - colors[i].b) * t)
      return `rgb(${r},${g},${b})`
    }
  }
  return 'rgb(255,50,50)'
}

async function loadData() {
  loading.value = true
  setLoading(true)
  try {
    const params = {
      region: filterStore.salesDetail.region,
      manager: filterStore.salesDetail.manager,
      customer: filterStore.salesDetail.customer,
      date_from: filterStore.salesDetail.dateRange?.[0] || null,
      date_to: filterStore.salesDetail.dateRange?.[1] || null,
      group_by: 'material'
    }
    const response = await getSalesDetail(params)
    const resData = response.data || {}
    const listData = Array.isArray(resData) ? resData : (resData.data || [])

    tableData.value = listData.map(row => ({
      materialCode: row.material_code,
      materialName: row.material_name,
      salesAmount: row.tax_included_amount_sum,
      yoyAmountChange: row.yoy_amount_diff,
      momAmountChange: row.mom_amount_diff,
      yoyAmountDiff: row.amount_yoy_pct,
      momAmountDiff: row.amount_mom_pct,
      marketShare: row.amount_share_pct,
      salesQty: row.quantity_sum,
      yoyQtyDiff: row.yoy_qty_diff,
      momQtyDiff: row.mom_qty_diff,
      qtyYoyPct: row.qty_yoy_pct,
      qtyMomPct: row.qty_mom_pct,
      qtyShare: row.qty_share_pct
    }))

    buildChart()
  } catch (error) {
    console.error('加载单品出货排名失败:', error)
    tableData.value = []
  } finally {
    loading.value = false
    setLoading(false)
  }
}

function buildChart() {
  if (tableData.value.length > 0) {
    const treemapData = tableData.value.map(row => ({
      name: row.materialName || row.materialCode,
      value: row.salesAmount || 0,
      itemStyle: {
        color: getTreemapColor(row.salesAmount, tableData.value)
      }
    }))

    chartOption.value = {
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          const d = tableData.value.find(x => (x.materialName || x.materialCode) === params.name)
          if (d) {
            return `<b>${params.name}</b><br/>含税金额：${d.salesAmount?.toFixed(2)} 万元<br/>数量：${d.salesQty || 0}<br/>金额占比：${d.marketShare || 0}%`
          }
          return params.name
        }
      },
      series: [{
        type: 'treemap',
        data: treemapData,
        label: {
          show: true,
          formatter: '{b}',
          fontSize: 11,
          color: '#333'
        },
        breadcrumb: { show: false },
        levels: [
          {
            itemStyle: {
              borderColor: '#fff',
              borderWidth: 2,
              gapWidth: 2
            }
          }
        ]
      }]
    }
  } else {
    chartOption.value = {}
  }

  setTimeout(() => {
    chartRef.value?.resize()
  }, 50)
}

function resetFilters() {
  filterStore.resetSalesDetail()
  loadData()
}

function handleExport() {
  // 导出逻辑
}

onMounted(async () => {
  await filterStore.fetchAllOptions()
  loadData()
})
</script>

<style scoped>
.product-ranking {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
}

.flow-filter {
  margin-bottom: 16px;
  padding: 12px 16px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.more-filters {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #dcdfe6;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-section {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 16px;
  min-height: 400px;
  width: 100%;
  box-sizing: border-box;
}

:deep(.el-table__header th) {
  font-weight: bold !important;
  text-align: center !important;
}
</style>
