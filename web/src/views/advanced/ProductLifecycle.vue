<template>
  <div class="product-lifecycle">
    <!-- 筛选器 -->
    <div class="filter-bar">
      <div class="filter-item">
        <span class="filter-label">追溯周期</span>
        <el-tooltip content="从物料首批入库时间往后看的月数。例如 18 = 首批入库后 18 个月内的销售数据" placement="top">
          <el-select v-model="filters.months" style="width: 120px" @change="loadData">
            <el-option :value="6" label="6 月" />
            <el-option :value="12" label="12 月" />
            <el-option :value="18" label="18 月" />
            <el-option :value="24" label="24 月" />
            <el-option :value="36" label="36 月" />
          </el-select>
        </el-tooltip>
      </div>
      <div class="filter-item">
        <span class="filter-label">品牌类型</span>
        <el-select v-model="filters.brand_class" clearable style="width: 120px" @change="loadData">
          <el-option value="自营" label="自营" />
          <el-option value="非自营" label="非自营" />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">ABC分类</span>
        <el-select v-model="filters.abc_class" clearable style="width: 120px" @change="loadData">
          <el-option value="A" label="A" />
          <el-option value="B" label="B" />
          <el-option value="C" label="C" />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">生命周期状态</span>
        <el-select v-model="filters.lifecycle_status" clearable style="width: 140px" @change="loadData">
          <el-option value="新品" label="新品" />
          <el-option value="持续销售" label="持续销售" />
          <el-option value="售完即止" label="售完即止" />
          <el-option value="重新上架" label="重新上架" />
          <el-option value="淘汰" label="淘汰" />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">PLC阶段</span>
        <el-select v-model="filters.plc_stage" clearable style="width: 120px" @change="filterTable">
          <el-option value="导入期" label="导入期" />
          <el-option value="成长期" label="成长期" />
          <el-option value="成熟期" label="成熟期" />
          <el-option value="衰退期" label="衰退期" />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">物料编码</span>
        <el-input v-model="filters.material_code" clearable style="width: 160px" placeholder="输入物料编码" @clear="loadData" @keyup.enter="loadData" />
      </div>
    </div>

    <!-- KPI卡片 - 双栏布局 -->
    <div class="kpi-dual-row">
      <div class="kpi-dual-col">
        <div class="kpi-section-title">PLC阶段分布（销售趋势）</div>
        <div class="kpi-row">
          <KpiCard label="总商品数" :value="metrics.total_products || 0" format-type="integer" :show-change="false" />
          <KpiCard label="导入期" :value="metrics.intro_count || 0" format-type="integer" :show-change="false" />
          <KpiCard label="成长期" :value="metrics.growth_count || 0" format-type="integer" :show-change="false" />
          <KpiCard label="成熟期" :value="metrics.mature_count || 0" format-type="integer" :show-change="false" />
          <KpiCard label="衰退期" :value="metrics.decline_count || 0" format-type="integer" :show-change="false" />
        </div>
      </div>
      <div class="kpi-dual-col">
        <div class="kpi-section-title">生命周期状态（库存管理）</div>
        <div class="kpi-row">
          <KpiCard label="新品" :value="metrics.new_product_count || 0" format-type="integer" :show-change="false" />
          <KpiCard label="持续销售" :value="metrics.sustained_count || 0" format-type="integer" :show-change="false" />
          <KpiCard label="售完即止" :value="metrics.one_time_count || 0" format-type="integer" :show-change="false" />
          <KpiCard label="淘汰" :value="metrics.discontinued_count || 0" format-type="integer" :show-change="false" />
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">PLC阶段分布</div>
        <v-chart :option="pieOption" style="height: 300px" autoresize />
      </div>
      <div class="chart-card">
        <div class="chart-title">累计出库量 vs 增长率（散点图）</div>
        <v-chart :option="scatterOption" style="height: 300px" autoresize />
      </div>
    </div>

    <!-- 新品S曲线进度 -->
    <div class="charts-row single" v-if="metrics.new_product_count > 0">
      <div class="chart-card">
        <div class="chart-title">新品S曲线进度分布</div>
        <v-chart :option="newProductBarOption" style="height: 250px" autoresize />
      </div>
    </div>

    <!-- 表格 -->
    <div class="section-card">
      <div class="section-title">
        商品生命周期明细
        <span class="record-count">共 {{ filteredTableData.length }} 条</span>
      </div>
      <el-table :data="filteredTableData" stripe border size="small" max-height="500" @sort-change="handleSortChange">
        <el-table-column prop="material_code" label="物料编码" width="110" fixed show-overflow-tooltip>
          <template #default="{ row }">
            <span class="link-text" @click="showCustomerCohort(row)">{{ row.material_code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="material_name" label="物料名称" min-width="140" fixed show-overflow-tooltip />
        <el-table-column prop="lifecycle_status" label="生命周期状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.lifecycle_status)" size="small">
              {{ row.lifecycle_status || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="plc_stage" label="PLC阶段" width="90" align="center">
          <template #default="{ row }">
            <span class="stage-badge" :style="{ backgroundColor: getStageColor(row.plc_stage) }">
              {{ row.plc_stage }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="sub_stage" label="子阶段" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getSubStageTagType(row.plc_stage)" size="small" effect="plain">
              {{ row.sub_stage }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="abc_class" label="ABC" width="55" align="center" />
        <el-table-column prop="first_stock_in_date" label="首批入库" width="100" align="center" />
        <el-table-column prop="days_since_launch" label="上市天数" width="85" align="right" sortable="custom" />
        <el-table-column prop="current_stock_qty" label="在库量" width="90" align="right" sortable="custom">
          <template #default="{ row }">
            {{ formatNumber(row.current_stock_qty) }}
          </template>
        </el-table-column>
        <el-table-column prop="cumulative_out_qty" label="累计出库" width="100" align="right" sortable="custom">
          <template #default="{ row }">
            {{ formatNumber(row.cumulative_out_qty) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_amount" label="累计销售额" width="110" align="right" sortable="custom">
          <template #default="{ row }">
            {{ formatNumber(row.total_amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="avg_monthly_qty" label="月均销量" width="90" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.avg_monthly_qty) }}
          </template>
        </el-table-column>
        <el-table-column prop="customer_count" label="客户数" width="70" align="right" />
        <el-table-column prop="customer_penetration" label="渗透率" width="80" align="right">
          <template #default="{ row }">
            {{ row.customer_penetration !== null ? (row.customer_penetration * 100).toFixed(1) + '%' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="growth_rate" label="增长率" width="85" align="right" sortable="custom">
          <template #header>
            <el-tooltip content="近3个月月度增长率的平均值。月度增长率 = (本月销售额 - 上月销售额) / 上月销售额" placement="top">
              <span>增长率 <el-icon style="vertical-align: middle"><QuestionFilled /></el-icon></span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span :style="{ color: row.growth_rate >= 0 ? '#67C23A' : '#F56C6C', fontWeight: 600 }">
              {{ row.growth_rate !== null ? (row.growth_rate * 100).toFixed(1) + '%' : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="sales_acceleration" label="加速度" width="80" align="right">
          <template #header>
            <el-tooltip content="增长率的变化速度 = 最近一个月增长率 - 上一个月增长率。正值表示增长加速，负值表示增长减速" placement="top">
              <span>加速度 <el-icon style="vertical-align: middle"><QuestionFilled /></el-icon></span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span :style="{ color: row.sales_acceleration >= 0 ? '#67C23A' : '#F56C6C' }">
              {{ row.sales_acceleration !== null ? row.sales_acceleration.toFixed(2) : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="cv" label="需求稳定性" width="95" align="right">
          <template #header>
            <el-tooltip content="变异系数CV = 标准差/均值，越低越稳定（<0.3稳定，>1.0剧烈波动）" placement="top">
              <span>需求稳定性 <el-icon style="vertical-align: middle"><QuestionFilled /></el-icon></span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span :style="{ color: getCvColor(row.cv) }">
              {{ row.cv !== null ? row.cv.toFixed(2) : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="decline_score" label="衰退置信度" width="95" align="center" sortable="custom">
          <template #header>
            <el-tooltip content="三重信号评分：趋势线斜率(40%)+Mann-Kendall(30%)+EMA交叉(15%)+连续下降(15%)，≥70确认衰退" placement="top">
              <span>衰退置信度 <el-icon style="vertical-align: middle"><QuestionFilled /></el-icon></span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <el-tooltip v-if="row.decline_score > 0" :content="row.decline_reasons || '无'" placement="top">
              <span :style="{ color: getDeclineScoreColor(row.decline_score), fontWeight: 600 }">
                {{ row.decline_score }}分
              </span>
            </el-tooltip>
            <span v-else style="color: #C0C4CC">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="trend_normalized_slope" label="趋势斜率" width="90" align="right">
          <template #header>
            <el-tooltip content="线性回归归一化斜率(%/月)，<-5%为中度下降，<-10%为严重下降" placement="top">
              <span>趋势斜率 <el-icon style="vertical-align: middle"><QuestionFilled /></el-icon></span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span :style="{ color: row.trend_normalized_slope < -5 ? '#F56C6C' : row.trend_normalized_slope < -2 ? '#E6A23C' : '#67C23A' }">
              {{ row.trend_normalized_slope !== null ? row.trend_normalized_slope.toFixed(1) + '%' : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="trend_r_squared" label="R²" width="60" align="right">
          <template #header>
            <el-tooltip content="趋势线拟合度R²，>0.4表示趋势可信" placement="top">
              <span>R² <el-icon style="vertical-align: middle"><QuestionFilled /></el-icon></span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span :style="{ color: row.trend_r_squared >= 0.4 ? '#67C23A' : '#909399' }">
              {{ row.trend_r_squared !== null ? row.trend_r_squared.toFixed(2) : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="action_recommendation" label="处理建议" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="advice-cell">
              <span class="advice-text">{{ row.action_recommendation }}</span>
              <el-button
                type="primary"
                size="small"
                link
                :loading="adviceLoading[row.material_code]"
                @click="generateLlmAdvice(row)"
              >
                AI建议
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- LLM建议弹窗 -->
    <el-dialog v-model="adviceDialogVisible" title="AI 运营建议" width="680px" :close-on-click-modal="false" destroy-on-close>
      <div v-if="adviceDialogData" class="advice-dialog">
        <div class="advice-product-info">
          <strong>{{ adviceDialogData.material_name }}</strong>（{{ adviceDialogData.material_code }}）
          <el-tag :type="getSubStageTagType(adviceDialogData.plc_stage)" size="small" style="margin-left: 8px">
            {{ adviceDialogData.plc_stage }} - {{ adviceDialogData.sub_stage }}
          </el-tag>
        </div>
        <el-divider />
        <div class="advice-content" v-loading="adviceDialogLoading">
          <div v-if="adviceDialogText" class="advice-text-block" v-html="formatAdvice(adviceDialogText)"></div>
          <div v-else-if="!adviceDialogLoading" style="color: #909399">暂无建议</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="adviceDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="regenerateAdvice" :loading="adviceDialogLoading">重新生成</el-button>
      </template>
    </el-dialog>

    <!-- 客户返单商品数量 Cohort 弹窗 -->
    <el-dialog v-model="cohortDialogVisible" :title="cohortDialogTitle" width="1200px" style="height: 80vh" destroy-on-close>
      <el-table v-if="cohortData.length > 0" :data="cohortData" stripe border size="small" max-height="520" table-layout="fixed" :default-sort="{ prop: 'first_order_date', order: 'ascending' }">
        <el-table-column prop="customer" label="客户名称" min-width="150" fixed show-overflow-tooltip />
        <el-table-column prop="material_code" label="物料编码" width="120" show-overflow-tooltip />
        <el-table-column prop="material_name" label="物料名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="first_order_date" label="首次下单时间" width="120" align="center" />
        <el-table-column
          v-for="(col, idx) in cohortMonthColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="getCohortColumnLabel(idx)"
          width="70"
          align="center"
        >
          <template #default="{ row }">
            <span :style="{ color: row[col.prop] > 0 ? '#2171b5' : '#c6dbef' }">{{ row[col.prop] || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty-tip" style="text-align: center; color: #909399; padding: 40px 0;">暂无数据</div>
      <template #footer>
        <el-button @click="toggleCohortViewMode">
          {{ isCohortDynamicView ? '切换: 偏移模式' : '切换: 动态日期' }}
        </el-button>
        <el-button v-if="cohortData.length > 0" type="success" @click="downloadCohortMatrix">
          {{ isCohortDynamicView ? '下载(动态日期)' : '下载(偏移模式)' }}
        </el-button>
        <el-button @click="cohortDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { getProductLifecycle, getLlmLifecycleAdvice } from '@/api/advanced'
import { getProductCustomerCohort } from '@/api/repurchase'
import KpiCard from '@/components/common/KpiCard.vue'
import { QuestionFilled } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, ScatterChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, MarkLineComponent } from 'echarts/components'

use([CanvasRenderer, PieChart, ScatterChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, MarkLineComponent])

const setLoading = inject('setLoading', () => {})

const filters = reactive({
  months: 18,
  brand_class: null,
  abc_class: null,
  lifecycle_status: null,
  material_code: null,
  plc_stage: null,
})

const tableData = ref([])
const filteredTableData = ref([])
const metrics = ref({})
const adviceLoading = reactive({})

// LLM建议弹窗
const adviceDialogVisible = ref(false)
const adviceDialogData = ref(null)
const adviceDialogText = ref('')
const adviceDialogLoading = ref(false)

// Cohort返单弹窗
const cohortDialogVisible = ref(false)
const selectedMaterial = ref('')
const selectedMaterialName = ref('')
const cohortData = ref([])
const cohortMonthColumns = ref([])
const isCohortDynamicView = ref(false)

const cohortDialogTitle = computed(() => {
  return selectedMaterial.value + ' - ' + selectedMaterialName.value + ' - 客户返单商品数量'
})

// ──────────────────────────────────────────────
// 数据加载
// ──────────────────────────────────────────────
async function loadData() {
  try {
    setLoading(true)
    const params = { months: filters.months }
    if (filters.brand_class) params.brand_class = filters.brand_class
    if (filters.abc_class) params.abc_class = filters.abc_class
    if (filters.lifecycle_status) params.lifecycle_status = filters.lifecycle_status
    if (filters.material_code) params.material_code = filters.material_code

    const res = await getProductLifecycle(params)
    const data = res.data?.data || res.data || {}
    tableData.value = data.lifecycle_data || []
    metrics.value = data.metrics || {}
    filterTable()
  } catch (e) {
    console.error('加载商品生命周期数据失败:', e)
    tableData.value = []
    filteredTableData.value = []
    metrics.value = {}
  } finally {
    setLoading(false)
  }
}

function filterTable() {
  if (filters.plc_stage) {
    filteredTableData.value = tableData.value.filter(r => r.plc_stage === filters.plc_stage)
  } else {
    filteredTableData.value = [...tableData.value]
  }
}

function handleSortChange({ prop, order }) {
  if (!prop || !order) {
    filterTable()
    return
  }
  const sorted = [...filteredTableData.value]
  sorted.sort((a, b) => {
    const va = a[prop] ?? 0
    const vb = b[prop] ?? 0
    return order === 'ascending' ? va - vb : vb - va
  })
  filteredTableData.value = sorted
}

// ──────────────────────────────────────────────
// LLM建议
// ──────────────────────────────────────────────
async function generateLlmAdvice(row) {
  adviceDialogData.value = row
  adviceDialogText.value = ''
  adviceDialogVisible.value = true
  adviceDialogLoading.value = true
  adviceLoading[row.material_code] = true

  try {
    const payload = {
      material_name: row.material_name,
      material_code: row.material_code,
      plc_stage: row.plc_stage,
      sub_stage: row.sub_stage,
      cumulative_out_qty: row.cumulative_out_qty,
      total_amount: row.total_amount,
      growth_rate: row.growth_rate,
      sales_acceleration: row.sales_acceleration,
      customer_penetration: row.customer_penetration,
      cv: row.cv,
      days_since_launch: row.days_since_launch || 0,
      abc_class: row.abc_class || '',
      consecutive_negative_months: row.consecutive_negative_months,
      avg_monthly_qty: row.avg_monthly_qty,
    }
    const res = await getLlmLifecycleAdvice(payload)
    adviceDialogText.value = res.data?.data?.advice || res.data?.advice || '暂无建议'
  } catch (e) {
    console.error('LLM建议生成失败:', e)
    adviceDialogText.value = '建议生成失败: ' + (e.response?.data?.detail || e.message || '未知错误')
  } finally {
    adviceDialogLoading.value = false
    adviceLoading[row.material_code] = false
  }
}

async function regenerateAdvice() {
  if (adviceDialogData.value) {
    await generateLlmAdvice(adviceDialogData.value)
  }
}

function formatAdvice(text) {
  if (!text) return ''
  // 先转 markdown 风格(markdown -> HTML),再用 DOMPurify 净化防止 XSS
  // 防止 LLM 输出中含 <script> / <img onerror=...> 等危险 HTML
  const html = text
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  return purifyAdviceHtml(html)
}

// 净化建议文本(LLM 输出),只允许安全标签
// 内部缓存 DOMPurify 实例,首次调用时按需加载
let _purifier = null
function purifyAdviceHtml(html) {
  if (!_purifier && typeof window !== 'undefined' && window.DOMPurify) {
    _purifier = window.DOMPurify
  }
  if (!_purifier) {
    // DOMPurify 不可用时,采取保守转义策略(只允许 <br> 和 <strong>)
    // 这避免了引入 v-html 的 XSS 风险
    return html.replace(/<(?!\/?(br|strong)\b)[^>]*>/gi, '&lt;$&gt;')
  }
  return _purifier.sanitize(html, {
    ALLOWED_TAGS: ['br', 'strong', 'em', 'p', 'ul', 'ol', 'li', 'code', 'pre'],
    ALLOWED_ATTR: []
  })
}

// ──────────────────────────────────────────────
// Cohort 返单弹窗
// ──────────────────────────────────────────────
async function showCustomerCohort(row) {
  try {
    selectedMaterial.value = row.material_code
    selectedMaterialName.value = row.material_name || ''
    cohortDialogVisible.value = true
    const params = {
      material_code: row.material_code,
      months: filters.months,
      view_mode: isCohortDynamicView.value ? 'absolute' : 'offset'
    }
    const res = await getProductCustomerCohort(params)
    const data = res.data?.data || res.data || {}
    const materialName = data.material_name || row.material_name || ''
    selectedMaterialName.value = materialName
    cohortData.value = (data.cohort_data || []).map(item => ({
      ...item,
      material_code: row.material_code,
      material_name: materialName
    }))
    cohortMonthColumns.value = (data.month_columns || []).map(col => ({ prop: col, label: col }))
  } catch (e) {
    console.error('加载客户返单详情失败:', e)
    cohortData.value = []
  }
}

function getCohortColumnLabel(idx) {
  if (!isCohortDynamicView.value) {
    const labels = ['首月', '+1月', '+2月', '+3月', '+4月', '+5月', '+6月', '+7月', '+8月', '+9月', '+10月', '+11月']
    return labels[idx] || `+${idx}月`
  }
  return cohortMonthColumns.value[idx]?.label || ''
}

function toggleCohortViewMode() {
  isCohortDynamicView.value = !isCohortDynamicView.value
  showCustomerCohort({ material_code: selectedMaterial.value, material_name: selectedMaterialName.value })
}

function downloadCohortMatrix() {
  if (cohortData.value.length === 0) return
  const labels = cohortMonthColumns.value.map(c => c.label)
  const headers = ['客户名称', '物料编码', '物料名称', '首次下单时间', ...labels]
  const rows = cohortData.value.map(row => [
    row.customer, row.material_code, row.material_name, row.first_order_date,
    ...cohortMonthColumns.value.map(c => row[c.prop] ?? 0)
  ])
  const csvContent = [headers, ...rows].map(r => r.join(',')).join('\n')
  const BOM = '﻿'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${selectedMaterial.value}_${selectedMaterialName.value}_客户返单${isCohortDynamicView.value ? '(动态日期)' : '(偏移模式)'}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

// ──────────────────────────────────────────────
// 格式化和颜色工具
// ──────────────────────────────────────────────
function getStageColor(stage) {
  const colors = {
    '导入期': '#E6A23C',
    '成长期': '#67C23A',
    '成熟期': '#409EFF',
    '衰退期': '#F56C6C',
  }
  return colors[stage] || '#909399'
}

function getCvColor(cv) {
  if (cv === null || cv === undefined) return '#909399'
  if (cv < 0.3) return '#67C23A'   // 稳定 - 绿色
  if (cv < 0.5) return '#E6A23C'   // 较稳定 - 橙色
  if (cv < 1.0) return '#F56C6C'   // 波动大 - 红色
  return '#F56C6C'                  // 剧烈波动 - 红色
}

function getDeclineScoreColor(score) {
  if (score >= 70) return '#F56C6C'  // 确认衰退 - 红色
  if (score >= 40) return '#E6A23C'  // 疑似衰退 - 橙色
  return '#67C23A'                    // 正常 - 绿色
}

function getStatusTagType(status) {
  const types = {
    '新品': 'warning',
    '持续销售': 'success',
    '售完即止': 'info',
    '重新上架': '',
    '淘汰': 'danger',
  }
  return types[status] || 'info'
}

function getSubStageTagType(stage) {
  const types = {
    '导入期': 'warning',
    '成长期': 'success',
    '成熟期': '',
    '衰退期': 'danger',
  }
  return types[stage] || 'info'
}

function formatNumber(val) {
  if (val === null || val === undefined) return '-'
  return Number(val).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

// ──────────────────────────────────────────────
// 图表配置
// ──────────────────────────────────────────────
const pieOption = computed(() => {
  const data = [
    { name: '导入期', value: metrics.value.intro_count || 0 },
    { name: '成长期', value: metrics.value.growth_count || 0 },
    { name: '成熟期', value: metrics.value.mature_count || 0 },
    { name: '衰退期', value: metrics.value.decline_count || 0 },
  ].filter(d => d.value > 0)

  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 10, left: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}: {c}' },
      data,
      color: ['#E6A23C', '#67C23A', '#409EFF', '#F56C6C'],
    }],
  }
})

const scatterOption = computed(() => {
  const stageColors = {
    '导入期': '#E6A23C',
    '成长期': '#67C23A',
    '成熟期': '#409EFF',
    '衰退期': '#F56C6C',
  }

  const stages = ['导入期', '成长期', '成熟期', '衰退期']
  const series = stages.map(stage => {
    const items = tableData.value.filter(r => r.plc_stage === stage)
    return {
      name: stage,
      type: 'scatter',
      data: items.map(r => [
        r.cumulative_out_qty,
        r.growth_rate * 100,
        r.total_amount,
        r.material_name,
      ]),
      symbolSize: val => Math.max(6, Math.min(30, Math.sqrt(val[2] / 1000))),
      itemStyle: { color: stageColors[stage] },
    }
  })

  return {
    tooltip: {
      trigger: 'item',
      formatter: params => {
        const d = params.data
        return `${d[3]}<br/>累计出库: ${d[0].toLocaleString()}<br/>增长率: ${d[1].toFixed(1)}%<br/>销售额: ${d[2].toLocaleString()}`
      },
    },
    legend: { bottom: 0 },
    xAxis: {
      type: 'value',
      name: '累计出库量',
      nameLocation: 'middle',
      nameGap: 30,
    },
    yAxis: {
      type: 'value',
      name: '增长率(%)',
      nameLocation: 'middle',
      nameGap: 40,
    },
    series,
  }
})

const newProductBarOption = computed(() => {
  const subStages = ['试销期', '爬坡期', '稳定期']
  const newProducts = tableData.value.filter(r => r.is_new_product)
  const counts = subStages.map(s => newProducts.filter(r => r.sub_stage === s).length)

  return {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: subStages,
    },
    yAxis: {
      type: 'value',
      name: '商品数',
    },
    series: [{
      type: 'bar',
      data: counts,
      barWidth: '40%',
      itemStyle: {
        color: (params) => {
          const colors = ['#E6A23C', '#67C23A', '#409EFF']
          return colors[params.dataIndex]
        },
        borderRadius: [4, 4, 0, 0],
      },
      label: {
        show: true,
        position: 'top',
        formatter: '{c}',
      },
    }],
  }
})

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.product-lifecycle { padding: 0; }

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background-color: #f5f7fa;
  border-radius: 6px;
}

.filter-item { display: flex; align-items: center; gap: 8px; }
.filter-label { font-size: 13px; color: #606266; white-space: nowrap; }

.link-text {
  color: #409EFF;
  cursor: pointer;
}
.link-text:hover {
  text-decoration: underline;
}

.kpi-dual-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.kpi-dual-col {
  background: #fff;
  border-radius: 8px;
  padding: 14px 16px;
  border: 1px solid #ebeef5;
}

.kpi-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
  padding-left: 4px;
}

.kpi-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 16px;
  margin-bottom: 16px;
}

.charts-row.single {
  grid-template-columns: 1fr;
}

.chart-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #ebeef5;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.section-card {
  background-color: #fff;
  border-radius: 6px;
  padding: 16px;
  border: 1px solid #ebeef5;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.record-count {
  font-size: 12px;
  font-weight: 400;
  color: #909399;
}

.stage-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
}

.advice-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.advice-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #606266;
}

.advice-dialog .advice-product-info {
  font-size: 15px;
  color: #303133;
}

.advice-dialog .advice-content {
  min-height: 100px;
  max-height: 60vh;
  overflow-y: auto;
}

.advice-dialog .advice-text-block {
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
