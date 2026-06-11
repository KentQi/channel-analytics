<template>
  <div class="wide-table">
    <div class="section-header">
      <span class="section-title">销售数据明细</span>
      <el-button type="primary" size="small" :icon="Download" @click="handleExportTable">
        导出
      </el-button>
    </div>

    <!-- Tab0筛选器 -->
    <div class="flow-filter">
      <el-form inline :model="filterStore.sales" class="filter-form-row">
        <el-form-item label="单据日期">
          <el-date-picker v-model="filterStore.sales.docDateRange" type="daterange" range-separator="~" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 220px" />
        </el-form-item>
        <el-form-item label="审核日期">
          <el-date-picker v-model="filterStore.sales.auditDateRange" type="daterange" range-separator="~" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 220px" />
        </el-form-item>
        <el-form-item label="大区">
          <el-select v-model="filterStore.sales.region" placeholder="请选择大区" clearable filterable style="width: 120px" @change="handleSalesRegionChange">
            <el-option v-for="item in options.regions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTableData">查询</el-button>
          <el-button @click="resetSalesFilters">重置</el-button>
          <el-button text @click="filterExpanded = !filterExpanded">
            {{ filterExpanded ? '收起' : '更多' }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
        </el-form-item>
      </el-form>
      <el-form v-show="filterExpanded" inline :model="filterStore.sales" class="more-filters">
        <el-form-item label="客户经理">
          <el-select v-model="filterStore.sales.manager" placeholder="请选择客户经理" clearable filterable style="width: 150px" @change="handleSalesManagerChange">
            <el-option v-for="item in options.managers" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户">
          <el-select v-model="filterStore.sales.customer" placeholder="请选择客户" clearable filterable style="width: 180px">
            <el-option v-for="item in options.customers" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="渠道">
          <el-select v-model="filterStore.sales.channel" placeholder="请选择渠道" clearable filterable style="width: 120px">
            <el-option v-for="item in options.channels" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="商品品类">
          <el-select v-model="filterStore.sales.category" placeholder="请选择品类" clearable filterable style="width: 120px">
            <el-option v-for="item in options.categories" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="ABC分类">
          <el-select v-model="filterStore.sales.abcClass" placeholder="请选择" clearable filterable style="width: 100px">
            <el-option v-for="item in options.abcClasses" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="生命周期">
          <el-select v-model="filterStore.sales.lifecycleStatus" placeholder="请选择" clearable filterable style="width: 120px">
            <el-option v-for="item in options.lifecycleStatuses" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="定制标记">
          <el-select v-model="filterStore.sales.customFlag" placeholder="请选择" clearable filterable style="width: 120px">
            <el-option v-for="item in options.customFlags" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="主推标记">
          <el-select v-model="filterStore.sales.promotedFlag" placeholder="请选择" clearable filterable style="width: 120px">
            <el-option v-for="item in options.promotedFlags" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="物料编码">
          <el-select v-model="filterStore.sales.materialCode" placeholder="请选择" clearable filterable style="width: 150px">
            <el-option v-for="item in options.materialCodes" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="物料名称">
          <el-select
            v-model="filterStore.sales.materialName"
            placeholder="输入关键词搜索"
            clearable
            filterable
            remote
            :remote-method="searchMaterialNameRemote"
            :loading="materialNameLoading"
            style="width: 180px"
          >
            <el-option v-for="item in options.materialNameOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <div class="summary-row" v-if="tableData.length > 0">
      <span class="summary-item"><strong>合计</strong></span>
      <span class="summary-item">金额：<strong>{{ formatNumber(summaryData.totalAmount) }}元</strong></span>
      <span class="summary-item">数量：<strong>{{ formatInteger(summaryData.totalQuantity) }}</strong></span>
      <span class="summary-item">进货金额：<strong>{{ formatNumber(summaryData.purchaseAmount) }}元</strong></span>
      <span class="summary-item">退货金额：<strong>{{ formatNumber(summaryData.returnAmount) }}元</strong></span>
      <span class="summary-item">进货客户数：<strong>{{ summaryData.purchaseCustomerCount }}</strong></span>
      <span class="summary-item">退货客户数：<strong>{{ summaryData.returnCustomerCount }}</strong></span>
      <span class="summary-item">进货SKU数：<strong>{{ summaryData.purchaseSkuCount }}</strong></span>
      <span class="summary-item">退货SKU数：<strong>{{ summaryData.returnSkuCount }}</strong></span>
    </div>

    <DataTable
      :data="tableData"
      :columns="tableColumns"
      :loading="loading"
      :show-pagination="true"
      :page-size="30"
      stripe
      :height="1500"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { Download, ArrowDown } from '@element-plus/icons-vue'
import DataTable from '@/components/common/DataTable.vue'
import { useFilterStore } from '@/stores/filter'
import { getSalesTable } from '@/api/sales'

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const options = computed(() => filterStore.options)
const loading = ref(false)
const filterExpanded = ref(false)

// 物料名称远程搜索
const materialNameLoading = ref(false)
let materialNameTimer = null
function searchMaterialNameRemote(keyword) {
  if (materialNameTimer) clearTimeout(materialNameTimer)
  materialNameTimer = setTimeout(async () => {
    materialNameLoading.value = true
    try {
      await filterStore.searchMaterialName(keyword)
    } finally {
      materialNameLoading.value = false
    }
  }, 300)
}

const tableData = ref([])

const summaryData = reactive({
  totalAmount: 0,
  totalQuantity: 0,
  purchaseAmount: 0,
  returnAmount: 0,
  purchaseCustomerCount: 0,
  returnCustomerCount: 0,
  purchaseSkuCount: 0,
  returnSkuCount: 0
})

const tableColumns = [
  { prop: '单据日期', label: '单据日期', width: 110 },
  { prop: '单据编号', label: '单据编号', width: 160 },
  { prop: '源头交易类型', label: '源头交易类型', width: 120 },
  { prop: '交易类型名称', label: '交易类型名称', width: 100 },
  { prop: '客户', label: '客户', minWidth: 180 },
  { prop: '客户分类', label: '客户分类', width: 100 },
  { prop: '大区经理', label: '大区经理', width: 100 },
  { prop: '仓库', label: '仓库', width: 120 },
  { prop: '物料编码', label: '物料编码', width: 130 },
  { prop: '物料名称', label: '物料名称', minWidth: 150 },
  { prop: '品牌', label: '品牌', width: 120 },
  { prop: '含税金额', label: '含税金额', width: 120, align: 'right' },
  { prop: '批次号', label: '批次号', width: 120 },
  { prop: '出货渠道', label: '出货渠道', width: 100 },
  { prop: '审核日期', label: '审核日期', width: 110 },
  { prop: '审核时间', label: '审核时间', width: 160 },
  { prop: '创建人', label: '创建人', width: 80 },
  { prop: '销售出库数量', label: '销售出库数量', width: 100, align: 'right' },
  { prop: '应发数量', label: '应发数量', width: 100, align: 'right' },
  { prop: '已开票数量', label: '已开票数量', width: 100, align: 'right' },
  { prop: '交易类型', label: '交易类型', width: 100 },
  { prop: '来源单据交易类型', label: '来源单据交易类型', width: 130 },
  { prop: '入账方式', label: '入账方式', width: 100 },
  { prop: '含税单价', label: '含税单价', width: 100, align: 'right' },
  { prop: '源头单据号', label: '源头单据号', width: 160 },
  { prop: '备注', label: '备注', minWidth: 150 },
  { prop: '商品品类', label: '商品品类', width: 100 },
  { prop: 'ABC分类', label: 'ABC分类', width: 80 },
  { prop: '生命周期状态', label: '生命周期状态', width: 100 },
  { prop: '定制标记', label: '定制标记', width: 80 },
  { prop: '主推标记', label: '主推标记', width: 80 },
  { prop: '大区', label: '大区', width: 100 },
  { prop: '客户经理', label: '客户经理', width: 100 },
  { prop: '渠道', label: '渠道', width: 100 },
  { prop: '创建时间', label: '创建时间', width: 160 }
]

function formatNumber(num) {
  return Number(num || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatInteger(num) {
  return Number(num || 0).toLocaleString('zh-CN')
}

async function loadTableData() {
  loading.value = true
  setLoading(true)
  try {
    const params = {
      region: filterStore.sales.region,
      manager: filterStore.sales.manager,
      customer: filterStore.sales.customer,
      channel: filterStore.sales.channel,
      doc_date_from: filterStore.sales.docDateRange?.[0] || null,
      doc_date_to: filterStore.sales.docDateRange?.[1] || null,
      date_from: filterStore.sales.auditDateRange?.[0] || null,
      date_to: filterStore.sales.auditDateRange?.[1] || null,
      category: filterStore.sales.category,
      abc_class: filterStore.sales.abcClass,
      lifecycle_status: filterStore.sales.lifecycleStatus,
      custom_flag: filterStore.sales.customFlag,
      promoted_flag: filterStore.sales.promotedFlag,
      material_code: filterStore.sales.materialCode,
      material_name: filterStore.sales.materialName,
      page: 1,
      page_size: 1000
    }

    let allData = []
    let totalRecords = 0
    let backendSummary = {}

    while (true) {
      const response = await getSalesTable(params)
      const pageData = response.data?.data || response.data || []

      if (params.page === 1) {
        totalRecords = response.data?.total || pageData.length || 0
        backendSummary = response.data?.summary || {}
      }

      allData = allData.concat(pageData)

      if (allData.length >= totalRecords || pageData.length === 0) {
        break
      }

      params.page++
    }

    tableData.value = allData
    Object.assign(summaryData, {
      totalAmount: backendSummary.total_amount || 0,
      totalQuantity: backendSummary.total_quantity || 0,
      purchaseAmount: backendSummary.inbound_amount || 0,
      returnAmount: backendSummary.outbound_amount || 0,
      purchaseCustomerCount: backendSummary.inbound_customer_count || 0,
      returnCustomerCount: backendSummary.outbound_customer_count || 0,
      purchaseSkuCount: backendSummary.inbound_sku_count || 0,
      returnSkuCount: backendSummary.outbound_sku_count || 0
    })
  } catch (error) {
    console.error('加载销售宽表失败:', error)
    tableData.value = []
  } finally {
    loading.value = false
    setLoading(false)
  }
}

function resetSalesFilters() {
  filterStore.resetSales()
  loadTableData()
}

function handleSalesRegionChange() {
  filterStore.sales.manager = null
  filterStore.sales.customer = null
}

function handleSalesManagerChange() {
  filterStore.sales.customer = null
}

function escapeCSV(value) {
  const str = String(value)
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    return '"' + str.replace(/"/g, '""') + '"'
  }
  return str
}

async function handleExportTable() {
  loading.value = true
  try {
    const params = {
      region: filterStore.sales.region,
      manager: filterStore.sales.manager,
      customer: filterStore.sales.customer,
      channel: filterStore.sales.channel,
      doc_date_from: filterStore.sales.docDateRange?.[0] || null,
      doc_date_to: filterStore.sales.docDateRange?.[1] || null,
      date_from: filterStore.sales.auditDateRange?.[0] || null,
      date_to: filterStore.sales.auditDateRange?.[1] || null,
      category: filterStore.sales.category,
      abc_class: filterStore.sales.abcClass,
      lifecycle_status: filterStore.sales.lifecycleStatus,
      custom_flag: filterStore.sales.customFlag,
      promoted_flag: filterStore.sales.promotedFlag,
      material_code: filterStore.sales.materialCode,
      material_name: filterStore.sales.materialName,
      page: 1,
      page_size: 1000
    }

    let allData = []
    let totalRecords = 0

    while (true) {
      const response = await getSalesTable(params)
      const pageData = response.data?.data || response.data || []

      if (params.page === 1) {
        totalRecords = response.data?.total || pageData.length || 0
      }

      allData = allData.concat(pageData)

      if (allData.length >= totalRecords || pageData.length === 0) {
        break
      }

      params.page++
    }

    const headers = tableColumns.map(col => escapeCSV(col.label || col.prop))
    const headerRow = headers.join(',')

    const rows = allData.map(row => {
      return tableColumns.map(col => {
        let value = row[col.prop]
        if (value === null || value === undefined) {
          value = ''
        } else {
          value = String(value)
        }
        return escapeCSV(value)
      }).join(',')
    })

    const BOM = '﻿'
    const csvContent = BOM + headerRow + '\n' + rows.join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `销售宽表_${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (error) {
    console.error('导出失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await filterStore.fetchAllOptions()
  loadTableData()
})
</script>

<style scoped>
.wide-table {
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

.filter-form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
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

.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.summary-row {
  display: flex;
  flex-wrap: nowrap;
  gap: 12px;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 12px;
  white-space: nowrap;
  overflow-x: auto;
}

.summary-item {
  color: #606266;
}

.summary-item strong {
  color: #303133;
}

:deep(.el-table__header th) {
  font-weight: bold !important;
  text-align: center !important;
}
</style>
