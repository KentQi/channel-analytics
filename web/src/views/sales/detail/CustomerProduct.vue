<template>
  <div class="customer-product">
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
        </el-form-item>
      </el-form>
    </div>

    <div class="section-header">
      <span class="section-title">客户×单品出货排名</span>
    </div>

    <el-table :data="tableData" size="small" stripe border>
      <el-table-column type="index" label="排名" width="60" align="center" />
      <el-table-column prop="customer" label="客户" min-width="150" show-overflow-tooltip />
      <el-table-column prop="materialCode" label="物料编码" width="130" />
      <el-table-column prop="materialName" label="商品名称" min-width="150" show-overflow-tooltip />
      <el-table-column prop="salesAmount" label="含税金额(万元)" width="120" align="right">
        <template #default="{ row }">
          {{ row.salesAmount?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="salesQty" label="数量" width="80" align="right" />
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useFilterStore } from '@/stores/filter'
import { getSalesDetail } from '@/api/sales'

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const options = computed(() => filterStore.options)
const loading = ref(false)

const tableData = ref([])

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
      group_by: 'customer_material'
    }
    const response = await getSalesDetail(params)
    const resData = response.data || {}
    const listData = Array.isArray(resData) ? resData : (resData.data || [])

    tableData.value = listData.map(row => ({
      customer: row.customer,
      materialCode: row.material_code,
      materialName: row.material_name,
      salesAmount: row.tax_included_amount_sum,
      salesQty: row.quantity_sum
    }))
  } catch (error) {
    console.error('加载客户×单品出货排名失败:', error)
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
.customer-product {
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
</style>
