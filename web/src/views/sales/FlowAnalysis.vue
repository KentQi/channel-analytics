<template>
  <div class="flow-analysis">
    <div class="flow-filter">
      <el-form inline :model="flowFilter">
        <el-form-item label="大区">
          <el-select
            v-model="flowFilter.region"
            placeholder="请选择大区"
            clearable
            filterable
            style="width: 140px"
            @change="loadFlowData"
          >
            <el-option
              v-for="item in options.regions"
              :key="item.value || item"
              :label="item.label || item"
              :value="item.value || item"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="flowDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            clearable
            style="width: 220px"
            @change="handleFlowDateRangeChange"
          />
        </el-form-item>
        <el-form-item label="批次号">
          <el-input
            v-model="flowFilter.batchNo"
            placeholder="请输入批次号"
            clearable
            style="width: 120px"
            @change="loadFlowData"
          />
        </el-form-item>
        <el-form-item label="客户">
          <el-select
            v-model="flowFilter.customer"
            placeholder="请选择客户"
            clearable
            filterable
            style="width: 140px"
            @change="loadFlowData"
          >
            <el-option
              v-for="item in options.customers"
              :key="item.value || item.id"
              :label="item.label || item.name"
              :value="item.value || item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="物料编码">
          <el-input
            v-model="flowFilter.materialCode"
            placeholder="请输入物料编码"
            clearable
            style="width: 120px"
            @change="loadFlowData"
          />
        </el-form-item>
        <el-form-item>
          <el-button text @click="flowExpanded = !flowExpanded">
            {{ flowExpanded ? '收起' : '更多' }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
        </el-form-item>
      </el-form>
      <el-form v-show="flowExpanded" inline :model="flowFilter" class="more-filters">
        <el-form-item label="交易类型">
          <el-select v-model="flowFilter.txType" placeholder="请选择" clearable style="width: 120px" @change="loadFlowData">
            <el-option label="全部" value="" />
            <el-option label="销售出库" value="销售出库" />
            <el-option label="退货入库" value="退货入库" />
            <el-option label="销售退货" value="销售退货" />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <v-chart :option="flowTrendOption" style="height: 300px; margin-top: 16px" autoresize />

    <DataTable
      :data="flowData"
      :columns="flowColumns"
      :loading="loading"
      :show-pagination="true"
      :page-size="20"
      stripe
      :height="1200"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, inject, computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import DataTable from '@/components/common/DataTable.vue'
import { useFilterStore } from '@/stores/filter'
import { getProductFlow } from '@/api/sales'
import { ArrowDown } from '@element-plus/icons-vue'

use([CanvasRenderer, BarChart, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const options = computed(() => filterStore.options)
const loading = ref(false)
const flowExpanded = ref(false)

const flowFilter = reactive({
  region: null,
  txType: '',
  customer: null,
  materialCode: '',
  batchNo: ''
})

const flowDateRange = ref([])
const flowData = ref([])

const flowTrendOption = ref({})

const flowColumns = [
  { prop: '单据编号', label: '单据编号', width: 160 },
  { prop: '已开票数量', label: '已开票数量', width: 100 },
  { prop: '源头交易类型', label: '源头交易类型', width: 100 },
  { prop: '交易类型', label: '交易类型', width: 100 },
  { prop: '客户', label: '客户', minWidth: 180 },
  { prop: '客户分类', label: '客户分类', width: 100 },
  { prop: '仓库', label: '仓库', width: 100 },
  { prop: '审核日期', label: '审核日期', width: 110 },
  { prop: '物料编码', label: '物料编码', width: 130 },
  { prop: '物料名称', label: '物料名称', minWidth: 150, showOverflowTooltip: true },
  { prop: '批次号', label: '批次号', width: 120 },
  { prop: '含税金额合计', label: '含税金额合计', width: 120, align: 'right' },
  { prop: '销售出库数量合计', label: '销售出库数量合计', width: 120, align: 'right' }
]

function handleFlowDateRangeChange(value) {
  if (value && value.length === 2) {
    flowFilter.dateFrom = value[0]
    flowFilter.dateTo = value[1]
  } else {
    flowFilter.dateFrom = null
    flowFilter.dateTo = null
  }
  loadFlowData()
}

async function loadFlowData() {
  loading.value = true
  setLoading(true)
  try {
    const params = {
      region: flowFilter.region,
      tx_type: flowFilter.txType,
      customer_id: flowFilter.customer,
      material_code: flowFilter.materialCode,
      batch_no: flowFilter.batchNo,
      date_from: flowFilter.dateFrom,
      date_to: flowFilter.dateTo
    }
    const response = await getProductFlow(params)
    const data = response.data?.data || response.data || {}

    flowData.value = data.items || data.list || []

    flowTrendOption.value = {
      tooltip: { trigger: 'axis' },
      legend: { data: ['入库', '出库'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true, splitLine: { show: false } },
      xAxis: {
        type: 'category',
        data: data.dates || []
      },
      yAxis: { type: 'value', splitLine: { show: false } },
      series: [
        {
          name: '入库',
          type: 'bar',
          data: data.inbounds || [],
          itemStyle: { color: '#67c23a' }
        },
        {
          name: '出库',
          type: 'bar',
          data: data.outbounds || [],
          itemStyle: { color: '#f56c6c' }
        }
      ]
    }
  } catch (error) {
    console.error('加载货流数据失败:', error)
    flowData.value = []
  } finally {
    loading.value = false
    setLoading(false)
  }
}

onMounted(async () => {
  await filterStore.fetchRegions()
  await filterStore.fetchCustomers()
  loadFlowData()
})
</script>

<style scoped>
.flow-analysis {
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
</style>
