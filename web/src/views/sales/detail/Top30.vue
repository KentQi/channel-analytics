<template>
  <div class="top30">
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
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="section-header">
      <span class="section-title">TOP30商品</span>
    </div>

    <el-table :data="tableData" size="small" stripe border class="top30-table">
      <el-table-column type="index" label="排名" width="60" align="center" fixed />
      <el-table-column prop="materialName" label="商品名称" min-width="200" fixed show-overflow-tooltip>
        <template #default="{ row }">
          <div class="mat-name">{{ row.materialName }}</div>
          <div class="mat-code">{{ row.materialCode }}</div>
        </template>
      </el-table-column>
      <el-table-column label="销售额" align="center" width="140">
        <template #default="{ row }">
          <div class="abs-val">{{ formatNumber(row.salesAmount) }}</div>
          <div class="yoy-val" :style="{ color: row.yoyAmount >= 0 ? '#E02020' : '#00B578' }">
            同比: {{ row.yoyAmount !== null ? (row.yoyAmount > 0 ? '▲' : '▼') : '--' }}{{ row.yoyAmount !== null ? Math.abs(row.yoyAmount).toFixed(2) + '%' : '' }}
          </div>
          <div class="yoy-val" :style="{ color: row.momAmount >= 0 ? '#E02020' : '#00B578' }">
            环比: {{ row.momAmount !== null ? (row.momAmount > 0 ? '▲' : '▼') : '--' }}{{ row.momAmount !== null ? Math.abs(row.momAmount).toFixed(2) + '%' : '' }}
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="marketShare" label="出货金额占比(%)" width="120" align="center">
        <template #default="{ row }">
          {{ row.marketShare !== null ? row.marketShare.toFixed(2) + '%' : '--' }}
        </template>
      </el-table-column>
      <el-table-column label="销量" align="center" width="120">
        <template #default="{ row }">
          <div class="abs-val">{{ formatInteger(row.salesQty) }}</div>
          <div class="yoy-val" :style="{ color: row.yoyQty >= 0 ? '#E02020' : '#00B578' }">
            同比: {{ row.yoyQty !== null ? (row.yoyQty > 0 ? '▲' : '▼') : '--' }}{{ row.yoyQty !== null ? Math.abs(row.yoyQty).toFixed(2) + '%' : '' }}
          </div>
          <div class="yoy-val" :style="{ color: row.momQty >= 0 ? '#E02020' : '#00B578' }">
            环比: {{ row.momQty !== null ? (row.momQty > 0 ? '▲' : '▼') : '--' }}{{ row.momQty !== null ? Math.abs(row.momQty).toFixed(2) + '%' : '' }}
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="orderCount" label="订单数" width="80" align="right" />
      <el-table-column label="平均出货单价" width="100" align="right">
        <template #default="{ row }">
          {{ row.unitPrice !== null ? row.unitPrice.toFixed(2) : '--' }}
        </template>
      </el-table-column>
      <el-table-column label="单均件数" width="80" align="right">
        <template #default="{ row }">
          {{ row.avgUnitsPerOrder !== null ? row.avgUnitsPerOrder.toFixed(2) : '--' }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useFilterStore } from '@/stores/filter'
import { getStarProducts } from '@/api/sales'

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const options = computed(() => filterStore.options)
const loading = ref(false)

const tableData = ref([])

function formatNumber(num) {
  return Number(num || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatInteger(num) {
  return Number(num || 0).toLocaleString('zh-CN')
}

async function loadData() {
  loading.value = true
  setLoading(true)
  try {
    const params = {
      region: filterStore.salesDetail.region,
      manager: filterStore.salesDetail.manager,
      date_from: filterStore.salesDetail.dateRange?.[0] || null,
      date_to: filterStore.salesDetail.dateRange?.[1] || null,
      top_n: 30
    }
    const response = await getStarProducts(params)
    const starData = response.data?.data || response.data || {}
    const products = starData.products || []

    tableData.value = products.map(row => ({
      materialCode: row.material_code,
      materialName: row.material_name,
      brand: row.brand,
      salesAmount: row.sales_amount_wan,
      salesQty: row.sales_qty,
      orderCount: row.order_count,
      marketShare: row.market_share,
      unitPrice: row.unit_price,
      avgUnitsPerOrder: row.avg_units_per_order,
      yoyAmount: row.yoy_amount,
      yoyQty: row.yoy_qty,
      momAmount: row.mom_amount,
      momQty: row.mom_qty
    }))
  } catch (error) {
    console.error('加载TOP30商品失败:', error)
    tableData.value = []
  } finally {
    loading.value = false
    setLoading(false)
  }
}

function resetFilters() {
  filterStore.resetSalesDetail()
  loadData()
}

onMounted(async () => {
  await filterStore.fetchAllOptions()
  loadData()
})
</script>

<style scoped>
.top30 {
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

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

:deep(.el-table__header th) {
  font-weight: bold !important;
  text-align: center !important;
}

.top30-table .mat-name {
  font-weight: 600;
  font-size: 13px;
  color: #333;
  margin-bottom: 2px;
}

.top30-table .mat-code {
  font-size: 11px;
  color: #999;
}

.top30-table .abs-val {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.top30-table .yoy-val {
  font-size: 11px;
  margin-top: 2px;
}
</style>
