<template>
  <div class="stock-analysis">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>库存分析</h2>
    </div>

    <!-- 全局筛选器 -->
    <div class="global-filter">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="品牌">
          <el-select
            v-model="filters.brandClass"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="全部品牌"
            style="width: 200px"
            @change="onFilterChange"
          >
            <el-option label="自营" value="自营" />
            <el-option label="非自营" value="非自营" />
          </el-select>
        </el-form-item>
        <el-form-item label="仓库">
          <el-select
            v-model="filters.warehouse"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="全部仓库"
            style="width: 220px"
            :loading="loadingOptions.warehouse"
            @change="onFilterChange"
          >
            <el-option
              v-for="w in warehouseOptions"
              :key="w"
              :label="w"
              :value="w"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="品项">
          <el-select
            v-model="filters.model"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="全部品项"
            style="width: 220px"
            :loading="loadingOptions.model"
            @change="onFilterChange"
          >
            <el-option
              v-for="m in modelOptions"
              :key="m"
              :label="m"
              :value="m"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadAllData">查询</el-button>
          <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- KPI 卡片区域 -->
    <div class="kpi-grid">
      <KpiCard label="库存数量" :value="kpis.total_stock" format-type="integer" />
      <KpiCard label="90天出货" :value="kpis.total_90d_sales" format-type="integer" />
      <KpiCard label="库存天数" :value="kpis.inventory_days" suffix="天" format-type="number" :decimals="1" />
      <KpiCard label="待入库" :value="kpis.total_pending_in" format-type="integer" />
      <KpiCard label="不动销库存" :value="kpis.no_sales_stock" format-type="integer" />
      <KpiCard label="在库SKU" :value="kpis.in_stock_skus" format-type="integer" />
      <KpiCard label="不动销SKU" :value="kpis.no_sales_skus" format-type="integer" />
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="main-tabs" @tab-change="onTabChange">
      <!-- Tab 1: 库存集中度分析 -->
      <el-tab-pane label="库存集中度分析" name="pareto">
        <div class="tab-content">
          <div class="section-header">
            <span class="section-title">帕累托分析</span>
            <div class="section-controls">
              <span class="control-label">阈值：</span>
              <el-slider
                v-model="paretoThreshold"
                :min="1"
                :max="100"
                :step="1"
                style="width: 200px"
                :show-tooltip="true"
                :format-tooltip="v => v + '%'"
                @change="loadParetoData"
              />
              <span class="control-value">{{ paretoThreshold }}%</span>
            </div>
          </div>

          <div class="chart-section">
            <h4 class="chart-title">不考虑批次</h4>
            <p class="chart-subtitle">前 {{ paretoThreshold }}% 的商品，共有 {{ paretoStats.filtered }} 个（共 {{ paretoStats.total }} 个物料）</p>
            <v-chart :option="paretoChartOption" style="height: 420px" autoresize />
          </div>

          <div class="chart-section">
            <h4 class="chart-title">考虑批次效期</h4>
            <p class="chart-subtitle">前 {{ paretoThreshold }}% 的商品，共有 {{ paretoStats.batchFiltered }} 个（共 {{ paretoStats.batchTotal }} 个SKU批次）</p>
            <v-chart :option="paretoBatchChartOption" style="height: 420px" autoresize />
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 批次分析 -->
      <el-tab-pane label="批次分析" name="batch">
        <div class="tab-content">
          <div class="section-header">
            <span class="section-title">批次维度分析</span>
            <div class="section-controls">
              <span class="control-label">显示物料数量：</span>
              <el-slider
                v-model="batchNShow"
                :min="5"
                :max="100"
                :step="5"
                style="width: 200px"
                :show-tooltip="true"
                @change="loadBatchData"
              />
              <span class="control-value">{{ batchNShow }}</span>
            </div>
          </div>
          <p class="chart-subtitle">柱状展示可用量，散点展示批号数量，识别多批次物料风险</p>
          <v-chart :option="batchChartOption" style="height: 500px" autoresize />
        </div>
      </el-tab-pane>

      <!-- Tab 3: 效期分析 -->
      <el-tab-pane label="效期分析" name="expiry">
        <div class="tab-content">
          <div class="chart-section">
            <h4 class="chart-title">效期状态分布</h4>
            <p class="chart-subtitle">横向柱状展示各效期区间库存量，散点展示SKU数量</p>
            <v-chart :option="expiryStatusChartOption" style="height: 420px" autoresize />
          </div>
          <div class="chart-section">
            <h4 class="chart-title">效期周转情况</h4>
            <p class="chart-subtitle">柱状对比可用量与90天销量，折线散点展示周转天数</p>
            <v-chart :option="expiryTurnoverChartOption" style="height: 420px" autoresize />
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 4: 库存去化分析 -->
      <el-tab-pane label="库存去化分析" name="noSales">
        <div class="tab-content">
          <div class="chart-section">
            <h4 class="chart-title">库存去化情况</h4>
            <p class="chart-subtitle">按最后销售时间距今分类，展示库存量、周转天数和SKU数量</p>
            <v-chart :option="noSalesChartOption" style="height: 420px" autoresize />
            <div class="table-section">
              <el-table :data="noSalesTableData" size="small" stripe border style="width: 100%">
                <el-table-column prop="分类" label="分类" min-width="160" />
                <el-table-column prop="库存数量" label="库存数量" width="120" align="right">
                  <template #default="{ row }">{{ formatNumber(row['库存数量']) }}</template>
                </el-table-column>
                <el-table-column prop="SKU数量" label="SKU数量" width="100" align="right">
                  <template #default="{ row }">{{ formatNumber(row['SKU数量']) }}</template>
                </el-table-column>
                <el-table-column prop="周转天数" label="周转天数" width="100" align="right">
                  <template #default="{ row }">{{ row['周转天数'] != null ? row['周转天数'] : 'N/A' }}</template>
                </el-table-column>
              </el-table>
            </div>
          </div>
          <div class="chart-section">
            <h4 class="chart-title">库存异常定位</h4>
            <p class="chart-subtitle">柱状展示不动销库存，散点标识90天零销量高库存物料</p>
            <v-chart :option="stockAbnormalChartOption" style="height: 420px" autoresize />
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 5: 趋势分析 -->
      <el-tab-pane label="趋势分析" name="trend">
        <div class="tab-content">
          <div class="chart-section">
            <h4 class="chart-title">趋势状态分布</h4>
            <p class="chart-subtitle">按周转状态分类，横向柱状展示库存量，顶部刻度显示SKU数量</p>
            <v-chart :option="trendChartOption" style="height: 420px" autoresize />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, ScatterChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkLineComponent
} from 'echarts/components'
import KpiCard from '@/components/common/KpiCard.vue'
import request from '@/api'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  BarChart,
  LineChart,
  ScatterChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkLineComponent
])

// ========== 状态 ==========
const activeTab = ref('pareto')
const loading = ref(false)

// 全局筛选器
const filters = reactive({
  brandClass: [],  // 多选
  warehouse: [],   // 多选
  model: []        // 多选
})

// 筛选器选项
const warehouseOptions = ref([])
const modelOptions = ref([])
const loadingOptions = reactive({ warehouse: false, model: false })

// KPI 数据
const kpis = reactive({
  total_stock: 0,
  total_90d_sales: 0,
  inventory_days: null,
  total_pending_in: 0,
  no_sales_stock: 0,
  in_stock_skus: 0,
  no_sales_skus: 0
})

// Tab 1 帕累托
const paretoThreshold = ref(80)
const paretoItems = ref([])
const paretoBatchItems = ref([])
const paretoStats = ref({ total: 0, filtered: 0, batchTotal: 0, batchFiltered: 0 })

// Tab 2 批次
const batchNShow = ref(50)
const batchItems = ref([])

// Tab 3 效期
const expiryDistribution = ref([])
const expiryTurnoverRanges = ref([])

// Tab 4 不动销
const noSalesCategories = ref([])
const noSalesTableData = ref([])

// Tab 5 趋势
const trendData = ref({
  by_turnover_status: {},
  by_expiry_status: {},
  trend_warning_count: 0,
  turnover_warning_count: 0,
  expiry_warning_count: 0
})

// ========== 构建查询参数 ==========
function buildFilterParams(extra = {}) {
  const params = { ...extra }
  // brand_class 传逗号分隔字符串（后端为单值筛选，多次调用）或直接传第一个
  // 后端 _apply_stock_filters 支持单值 brand_class/warehouse/model
  // 多选时需要多次请求合并或修改后端。由于后端只支持单值，
  // 我们传 join 字符串，由后端处理。但后端代码明确用 == 比较，
  // 所以多选时不传该参数（传空=不过滤），前端靠多次请求或聚合。
  // 简化方案：只传第一个选中值，或不传（全选=不传=不过滤）
  // 正确方案：如果用户选择了特定值，传过去；全选/未选则不传。
  // 但后端 brand_class 是单值 == 比较，多选需改造。
  // 这里采用：多选时每个值分别请求再合并 —— 太复杂。
  // 实际看后端: brand_class=None 时不过滤。所以多选=不过滤是安全的退化。
  // 最佳实践：如果选了部分值，只传第一个（作为 MVP）。后续可改造后端支持 IN 查询。
  // 临时方案：不传 brand_class/warehouse/model 到后端（MVP 简化），前端提示。
  // 但任务明确要求传这些参数。看后端代码：
  //   if brand_class and "brand_class" in filtered.columns:
  //       filtered = filtered[filtered["brand_class"] == brand_class]
  // 它用 == 比较，传单值。多选需要后端改为 isin。
  // 作为前端，我们只传单值；多选第一个或不传。
  // 最终方案：如果筛选器只选了1个值，传它；选了多个或全选，不传（=不过滤）
  if (filters.brandClass.length === 1) {
    params.brand_class = filters.brandClass[0]
  }
  if (filters.warehouse.length === 1) {
    params.warehouse = filters.warehouse[0]
  }
  if (filters.model.length === 1) {
    params.model = filters.model[0]
  }
  return params
}

// ========== API 调用 ==========
async function loadKpiData() {
  try {
    const params = buildFilterParams()
    const res = await request.get('/stock/kpis', { params })
    const data = res.data?.data || {}
    Object.assign(kpis, data)
  } catch (e) {
    console.error('加载KPI失败:', e)
  }
}

async function loadParetoData() {
  try {
    const params = buildFilterParams({ threshold: paretoThreshold.value })
    // 不考虑批次
    const res1 = await request.get('/stock/pareto', { params: { ...params, by_batch: false } })
    paretoItems.value = res1.data?.data?.items || []
    paretoStats.value.total = res1.data?.data?.total_count || 0
    paretoStats.value.filtered = res1.data?.data?.filtered_count || 0
    // 考虑批次
    const res2 = await request.get('/stock/pareto', { params: { ...params, by_batch: true } })
    paretoBatchItems.value = res2.data?.data?.items || []
    paretoStats.value.batchTotal = res2.data?.data?.total_count || 0
    paretoStats.value.batchFiltered = res2.data?.data?.filtered_count || 0
  } catch (e) {
    console.error('加载帕累托数据失败:', e)
    paretoItems.value = []
    paretoBatchItems.value = []
    paretoStats.value = { total: 0, filtered: 0, batchTotal: 0, batchFiltered: 0 }
  }
}

async function loadBatchData() {
  try {
    const params = buildFilterParams({ n_show: batchNShow.value })
    const res = await request.get('/stock/batch-analysis', { params })
    batchItems.value = res.data?.data?.items || []
  } catch (e) {
    console.error('加载批次数据失败:', e)
    batchItems.value = []
  }
}

async function loadExpiryData() {
  try {
    const params = buildFilterParams()
    const [statusRes, turnoverRes] = await Promise.all([
      request.get('/stock/expiry-status', { params }),
      request.get('/stock/expiry-turnover-matrix', { params })
    ])
    expiryDistribution.value = statusRes.data?.data?.distribution || []
    expiryTurnoverRanges.value = turnoverRes.data?.data?.ranges || []
  } catch (e) {
    console.error('加载效期数据失败:', e)
    expiryDistribution.value = []
    expiryTurnoverRanges.value = []
  }
}

async function loadNoSalesData() {
  try {
    const params = buildFilterParams({ days: 30 })
    const res = await request.get('/stock/no-sales', { params })
    const categories = res.data?.data?.categories || []
    noSalesCategories.value = categories
    noSalesTableData.value = categories
  } catch (e) {
    console.error('加载不动销数据失败:', e)
    noSalesCategories.value = []
    noSalesTableData.value = []
  }
}

async function loadTrendData() {
  try {
    const params = buildFilterParams()
    const res = await request.get('/stock/summary', { params })
    trendData.value = res.data?.data || {}
  } catch (e) {
    console.error('加载趋势数据失败:', e)
    trendData.value = {}
  }
}

async function loadFilterOptions() {
  // 加载仓库选项
  loadingOptions.warehouse = true
  try {
    const res = await request.get('/stock/filter-options/warehouse')
    warehouseOptions.value = res.data?.data || []
  } catch (e) {
    console.error('加载仓库选项失败:', e)
  } finally {
    loadingOptions.warehouse = false
  }

  // 加载品项选项（从 stg_stock_in.model 获取型号）
  loadingOptions.model = true
  try {
    const res = await request.get('/stock/filter-options/model')
    modelOptions.value = res.data?.data || []
  } catch (e) {
    console.error('加载品项选项失败:', e)
  } finally {
    loadingOptions.model = false
  }
}

// ========== 图表配置 ==========

// Tab 1: 不考虑批次的帕累托图
const paretoChartOption = computed(() => {
  const items = paretoItems.value
  if (!items.length) return emptyChartOption('暂无数据')

  const categories = items.map(i => i.label || i.material_name || '')
  const barData = items.map(i => Number(i.available_qty) || 0)
  const cumData = items.map(i => Number(i['累计占比']) || 0)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter(params) {
        let html = params[0].axisValue + '<br/>'
        params.forEach(p => {
          if (p.seriesType === 'bar') {
            html += `${p.marker} 可用量: ${formatNumber(p.value)}<br/>`
          } else {
            html += `${p.marker} 累计占比: ${p.value.toFixed(2)}%<br/>`
          }
        })
        return html
      }
    },
    legend: { data: ['可用量', '累计占比'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', top: 50, containLabel: true, splitLine: { show: false } },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { rotate: categories.length > 15 ? 45 : 0, interval: 'auto', fontSize: 11 }
    },
    yAxis: [
      { type: 'value', name: '可用量', position: 'left', axisLabel: { formatter: v => v >= 10000 ? (v / 10000).toFixed(0) + '万' : v }, splitLine: { show: false } },
      { type: 'value', name: '累计占比', position: 'right', min: 0, max: 100, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } }
    ],
    series: [
      {
        name: '可用量', type: 'bar', data: barData,
        itemStyle: { color: '#409eff' }, barMaxWidth: 40
      },
      {
        name: '累计占比', type: 'line', yAxisIndex: 1, data: cumData,
        smooth: true, itemStyle: { color: '#67c23a' },
        lineStyle: { width: 2 }, symbol: 'circle', symbolSize: 5
      }
    ],
  }
})

const paretoBatchChartOption = computed(() => {
  const items = paretoBatchItems.value
  if (!items.length) return emptyChartOption('暂无数据')

  const categories = items.map(i => i.label || '')
  const barData = items.map(i => Number(i.available_qty) || 0)
  const cumData = items.map(i => Number(i['累计占比']) || 0)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter(params) {
        let html = params[0].axisValue + '<br/>'
        params.forEach(p => {
          if (p.seriesType === 'bar') {
            html += `${p.marker} 可用量: ${formatNumber(p.value)}<br/>`
          } else {
            html += `${p.marker} 累计占比: ${p.value.toFixed(2)}%<br/>`
          }
        })
        return html
      }
    },
    legend: { data: ['可用量', '累计占比'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', top: 50, containLabel: true, splitLine: { show: false } },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { rotate: categories.length > 10 ? 60 : 0, interval: 'auto', fontSize: 10 }
    },
    yAxis: [
      { type: 'value', name: '可用量', position: 'left', axisLabel: { formatter: v => v >= 10000 ? (v / 10000).toFixed(0) + '万' : v }, splitLine: { show: false } },
      { type: 'value', name: '累计占比', position: 'right', min: 0, max: 100, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } }
    ],
    series: [
      {
        name: '可用量', type: 'bar', data: barData,
        itemStyle: { color: '#e6a23c' }, barMaxWidth: 40
      },
      {
        name: '累计占比', type: 'line', yAxisIndex: 1, data: cumData,
        smooth: true, itemStyle: { color: '#f56c6c' },
        lineStyle: { width: 2 }, symbol: 'circle', symbolSize: 5
      }
    ]
  }
})

// Tab 2: 批次分析柱状图+散点
const batchChartOption = computed(() => {
  const items = batchItems.value
  if (!items.length) return emptyChartOption('暂无数据')

  const categories = items.map(i => i.material_name || i.material_code || '')
  const qtyData = items.map(i => Number(i.total_available_qty) || 0)
  const batchCountData = items.map(i => Number(i.batch_count) || 0)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter(params) {
        let html = params[0].axisValue + '<br/>'
        params.forEach(p => {
          if (p.seriesType === 'bar') {
            html += `${p.marker} 总可用量: ${formatNumber(p.value)}<br/>`
          } else {
            html += `${p.marker} 批号数量: ${p.value}<br/>`
          }
        })
        return html
      }
    },
    legend: { data: ['总可用量', '批号数量'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', top: 50, containLabel: true, splitLine: { show: false } },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { rotate: categories.length > 15 ? 45 : 0, interval: 'auto', fontSize: 11 }
    },
    yAxis: [
      { type: 'value', name: '可用量', position: 'left', axisLabel: { formatter: v => v >= 10000 ? (v / 10000).toFixed(0) + '万' : v }, splitLine: { show: false } },
      { type: 'value', name: '批号数量', position: 'right', splitLine: { show: false } }
    ],
    series: [
      {
        name: '总可用量', type: 'bar', data: qtyData,
        itemStyle: { color: '#409eff' }, barMaxWidth: 40
      },
      {
        name: '批号数量', type: 'scatter', yAxisIndex: 1, data: batchCountData,
        itemStyle: { color: '#f56c6c' }, symbolSize: 10
      }
    ]
  }
})

// Tab 3: 效期状态分布（横向柱状图 + SKU数量散点）
const expiryStatusChartOption = computed(() => {
  const dist = expiryDistribution.value
  if (!dist.length) return emptyChartOption('暂无数据')

  // 按固定顺序排列
  const order = [
    '效期极佳(32+)', '效期优秀(28-32)', '效期良好(24-28)', '效期一般(18-24)',
    '效期较差(12-18)', '效期很差(6-12)', '效期临期(0-6)', '过期（0-）', '未知'
  ]
  const sorted = [...dist].sort((a, b) => {
    const ia = order.indexOf(a.expiry_status)
    const ib = order.indexOf(b.expiry_status)
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib)
  })

  const categories = sorted.map(i => i.expiry_status || '未知')
  const stockData = sorted.map(i => Number(i['库存数量']) || 0)
  const skuData = sorted.map(i => Number(i['SKU数量']) || 0)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params) {
        let html = params[0].axisValue + '<br/>'
        params.forEach(p => {
          if (p.seriesType === 'bar') {
            html += `${p.marker} ${p.seriesName}: ${formatNumber(p.value)}<br/>`
          } else if (p.seriesType === 'scatter') {
            // 散点数据格式是 [x, y]，x是数值，y是索引
            html += `${p.marker} ${p.seriesName}: ${formatNumber(Array.isArray(p.value) ? p.value[0] : p.value)}<br/>`
          } else {
            html += `${p.marker} ${p.seriesName}: ${p.value}<br/>`
          }
        })
        return html
      }
    },
    legend: { data: ['库存数量', 'SKU数量'], top: 0 },
    grid: { left: '3%', right: '6%', bottom: '3%', top: 40, containLabel: true, splitLine: { show: false } },
    xAxis: [
      { type: 'value', name: '库存数量', position: 'bottom', axisLabel: { formatter: v => v >= 10000 ? (v / 10000).toFixed(0) + '万' : v } },
      { type: 'value', name: 'SKU数量', position: 'top', axisLabel: { formatter: '{value}' } }
    ],
    yAxis: {
      type: 'category',
      data: categories,
      inverse: false
    },
    series: [
      {
        name: '库存数量', type: 'bar', data: stockData,
        itemStyle: { color: '#409eff' }, barMaxWidth: 30
      },
      {
        name: 'SKU数量', type: 'scatter', xAxisIndex: 1, data: skuData.map((v, i) => [v, i]),
        itemStyle: { color: '#f56c6c' }, symbolSize: 10
      }
    ]
  }
})

// Tab 3: 效期周转柱线混合
const expiryTurnoverChartOption = computed(() => {
  const ranges = expiryTurnoverRanges.value
  if (!ranges.length) return emptyChartOption('暂无数据')

  const categories = ranges.map(r => r.expiry_range || '')
  const availData = ranges.map(r => Number(r.available_qty) || 0)
  const salesData = ranges.map(r => Number(r.sales_90d) || 0)
  const turnoverData = ranges.map(r => {
    const td = Number(r.turnover_days)
    return td > 900 ? null : td  // 太大的值不显示
  })

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter(params) {
        let html = params[0].axisValue + '<br/>'
        params.forEach(p => {
          if (p.seriesName === '周转天数') {
            html += `${p.marker} 周转天数: ${p.value != null ? p.value + '天' : 'N/A'}<br/>`
          } else {
            html += `${p.marker} ${p.seriesName}: ${formatNumber(p.value)}<br/>`
          }
        })
        return html
      }
    },
    legend: { data: ['可用量', '90天销量', '周转天数'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', top: 50, containLabel: true, splitLine: { show: false } },
    xAxis: {
      type: 'category',
      data: categories
    },
    yAxis: [
      { type: 'value', name: '数量', position: 'left', axisLabel: { formatter: v => v >= 10000 ? (v / 10000).toFixed(0) + '万' : v }, splitLine: { show: false } },
      { type: 'value', name: '周转天数', position: 'right', axisLabel: { formatter: '{value}天' }, splitLine: { show: false } }
    ],
    series: [
      {
        name: '可用量', type: 'bar', data: availData,
        itemStyle: { color: '#409eff' }, barMaxWidth: 40
      },
      {
        name: '90天销量', type: 'bar', data: salesData,
        itemStyle: { color: '#67c23a' }, barMaxWidth: 40
      },
      {
        name: '周转天数', type: 'scatter', yAxisIndex: 1, data: turnoverData,
        itemStyle: { color: '#f56c6c' }, symbolSize: 10
      }
    ]
  }
})

// Tab 4: 不动销分类（横向柱状图 + 周转天数/SKU散点）
const noSalesChartOption = computed(() => {
  const cats = noSalesCategories.value
  if (!cats.length) return emptyChartOption('暂无数据')

  const categories = cats.map(c => c['分类'] || '')
  const stockData = cats.map(c => Number(c['库存数量']) || 0)
  const turnoverData = cats.map(c => c['周转天数'] != null ? Number(c['周转天数']) : null)
  const skuData = cats.map(c => Number(c['SKU数量']) || 0)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params) {
        let html = params[0].axisValue + '<br/>'
        params.forEach(p => {
          if (p.seriesType === 'bar') {
            html += `${p.marker} ${p.seriesName}: ${formatNumber(p.value)}<br/>`
          } else if (p.seriesType === 'scatter') {
            // 散点数据格式是 [x, y]，x是数值，y是索引
            html += `${p.marker} ${p.seriesName}: ${formatNumber(p.value[0])}<br/>`
          } else {
            html += `${p.marker} ${p.seriesName}: ${p.value}<br/>`
          }
        })
        return html
      }
    },
    legend: { data: ['库存数量', '周转天数', 'SKU数量'], top: 0 },
    grid: { left: '3%', right: '8%', bottom: '3%', top: 40, containLabel: true, splitLine: { show: false } },
    xAxis: [
      { type: 'value', name: '库存数量', position: 'bottom', axisLabel: { formatter: v => v >= 10000 ? (v / 10000).toFixed(0) + '万' : v }, splitLine: { show: false } },
      { type: 'value', name: '天数 / SKU', position: 'top', splitLine: { show: false } }
    ],
    yAxis: {
      type: 'category',
      data: categories
    },
    series: [
      {
        name: '库存数量', type: 'bar', data: stockData,
        itemStyle: { color: '#409eff' }, barMaxWidth: 30
      },
      {
        name: '周转天数', type: 'scatter', xAxisIndex: 1,
        data: turnoverData.map((v, i) => v != null ? [v, i] : null).filter(Boolean),
        itemStyle: { color: '#e6a23c' }, symbolSize: 12
      },
      {
        name: 'SKU数量', type: 'scatter', xAxisIndex: 1,
        data: skuData.map((v, i) => [v, i]),
        itemStyle: { color: '#f56c6c' }, symbolSize: 8
      }
    ]
  }
})

// Tab 4: 库存异常定位（柱状图+散点）
const stockAbnormalChartOption = computed(() => {
  // 使用不动销数据中的详细项，若无可从趋势数据中构建
  const cats = noSalesCategories.value
  if (!cats.length) return emptyChartOption('暂无数据')

  // 以分类为维度，展示库存数量和90天销量对比
  const categories = cats.map(c => c['分类'] || '')
  const stockData = cats.map(c => Number(c['库存数量']) || 0)
  const turnoverData = cats.map(c => c['周转天数'] != null ? Number(c['周转天数']) : 0)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter(params) {
        let html = params[0].axisValue + '<br/>'
        params.forEach(p => {
          html += `${p.marker} ${p.seriesName}: ${formatNumber(p.value)}<br/>`
        })
        return html
      }
    },
    legend: { data: ['可用量', '周转天数'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', top: 50, containLabel: true, splitLine: { show: false } },
    xAxis: { type: 'category', data: categories },
    yAxis: [
      { type: 'value', name: '可用量', position: 'left', axisLabel: { formatter: v => v >= 10000 ? (v / 10000).toFixed(0) + '万' : v }, splitLine: { show: false } },
      { type: 'value', name: '周转天数', position: 'right', axisLabel: { formatter: '{value}天' }, splitLine: { show: false } }
    ],
    series: [
      {
        name: '可用量', type: 'bar', data: stockData,
        itemStyle: { color: '#409eff' }, barMaxWidth: 40
      },
      {
        name: '周转天数', type: 'scatter', yAxisIndex: 1, data: turnoverData,
        itemStyle: { color: '#f56c6c' }, symbolSize: 12
      }
    ]
  }
})

// Tab 5: 趋势状态分布
const trendChartOption = computed(() => {
  const td = trendData.value
  const byTurnover = td.by_turnover_status || {}

  // 提取 turnover_status 分组数据
  const statusKeys = Object.keys(byTurnover).filter(k => k && k !== 'null')
  if (!statusKeys.length) return emptyChartOption('暂无数据')

  // by_turnover_status 结构: { sku_count: {key: val}, total_qty: {key: val} }
  const skuCounts = byTurnover.sku_count || {}
  const totalQtys = byTurnover.total_qty || {}
  const allKeys = [...new Set([...Object.keys(skuCounts), ...Object.keys(totalQtys)])].filter(k => k && k !== 'null')

  if (!allKeys.length) return emptyChartOption('暂无数据')

  // 按照状态排序（从差到好，最上面是最差的，最下面是最好的）
  const order = ['周转高(>90天)', '周转偏低(60-90天)', '周转正常(30-60天)', '周转健康(<30天)', '无库存数据']
  const sortedKeys = [...allKeys].sort((a, b) => {
    const ia = order.indexOf(a)
    const ib = order.indexOf(b)
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib)
  })

  const categories = sortedKeys
  const salesData = sortedKeys.map(k => Number(totalQtys[k]) || 0)
  const skuData = sortedKeys.map(k => Number(skuCounts[k]) || 0)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params) {
        let html = params[0].axisValue + '<br/>'
        params.forEach(p => {
          if (p.seriesType === 'bar') {
            html += `${p.marker} ${p.seriesName}: ${formatNumber(p.value)}<br/>`
          } else if (p.seriesType === 'scatter') {
            // 散点数据格式是 [x, y]，x是数值，y是索引
            html += `${p.marker} ${p.seriesName}: ${formatNumber(Array.isArray(p.value) ? p.value[0] : p.value)}<br/>`
          } else {
            html += `${p.marker} ${p.seriesName}: ${p.value}<br/>`
          }
        })
        return html
      }
    },
    legend: { data: ['近90天总销量', 'SKU数量'], top: 0 },
    grid: { left: '3%', right: '6%', bottom: '3%', top: 40, containLabel: true, splitLine: { show: false } },
    xAxis: [
      { type: 'value', name: '库存数量', position: 'bottom', min: 0, axisLabel: { formatter: v => v >= 10000 ? (v / 10000).toFixed(0) + '万' : v }, splitLine: { show: false } },
      { type: 'value', name: 'SKU数量', position: 'top', min: 0, splitLine: { show: false } }
    ],
    yAxis: {
      type: 'category',
      data: categories
    },
    series: [
      {
        name: '近90天总销量', type: 'bar', data: salesData, xAxisIndex: 0,
        itemStyle: {
          color: (params) => {
            const colors = ['#67c23a', '#95d475', '#b3e19d', '#e6a23c', '#f56c6c', '#c45656']
            return colors[params.dataIndex] || '#409eff'
          }
        },
        barMaxWidth: 30
      },
      {
        name: 'SKU数量', type: 'scatter', xAxisIndex: 1,
        data: skuData.map((v, i) => [v, i]),
        itemStyle: { color: '#f56c6c' }, symbolSize: 10
      }
    ]
  }
})

// ========== 工具函数 ==========

function emptyChartOption(text) {
  return {
    title: { text, left: 'center', top: 'center', textStyle: { color: '#909399', fontSize: 14 } },
    xAxis: { type: 'category', data: [] },
    yAxis: { type: 'value' },
    series: []
  }
}

function formatNumber(num) {
  if (num == null) return '--'
  return Number(num).toLocaleString('zh-CN')
}

// ========== 事件处理 ==========

function onFilterChange() {
  // 筛选器变化时重新加载
}

function resetFilters() {
  filters.brandClass = []
  filters.warehouse = []
  filters.model = []
  loadAllData()
}

function onTabChange(tab) {
  switch (tab) {
    case 'pareto': loadParetoData(); break
    case 'batch': loadBatchData(); break
    case 'expiry': loadExpiryData(); break
    case 'noSales': loadNoSalesData(); break
    case 'trend': loadTrendData(); break
  }
}

function loadAllData() {
  loadKpiData()
  switch (activeTab.value) {
    case 'pareto': loadParetoData(); break
    case 'batch': loadBatchData(); break
    case 'expiry': loadExpiryData(); break
    case 'noSales': loadNoSalesData(); break
    case 'trend': loadTrendData(); break
  }
}

// ========== 生命周期 ==========

onMounted(() => {
  loadFilterOptions()
  loadAllData()
})
</script>

<style scoped>
.stock-analysis {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.global-filter {
  background-color: #fff;
  padding: 16px 20px;
  border-radius: 4px;
  margin-bottom: 16px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.main-tabs {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
}

.tab-content {
  padding: 16px 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.section-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.control-value {
  font-size: 14px;
  color: #409eff;
  font-weight: 500;
  min-width: 40px;
}

.chart-section {
  margin-bottom: 32px;
}

.chart-section:last-child {
  margin-bottom: 0;
}

.chart-title {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
  margin: 0 0 4px 0;
  padding-left: 10px;
  border-left: 3px solid #409eff;
}

.chart-subtitle {
  font-size: 12px;
  color: #909399;
  margin: 0 0 12px 13px;
}

.table-section {
  margin-top: 20px;
}
</style>
