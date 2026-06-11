<template>
  <div class="etl-page">
    <!-- 顶部状态栏 -->
    <div class="status-bar">
      <div class="status-hint">
        <el-icon class="hint-icon"><InfoFilled /></el-icon>
        <span>请设置库存计算基准日期后再执行ETL（默认当日）</span>
      </div>
      <div class="status-info">
        <el-tag :type="dbStatus.connected ? 'success' : 'danger'" size="small" class="status-tag">
          <el-icon><Coin /></el-icon>
          数据库：{{ dbStatus.connected ? `已连接（${dbStatus.table_count} 张表）` : '未连接' }}
        </el-tag>
        <el-tag :type="filesReady ? 'success' : 'warning'" size="small" class="status-tag">
          <el-icon><Document /></el-icon>
          源文件：{{ filesReady ? `${fileCount} 个文件已就绪` : '未就绪' }}
        </el-tag>
      </div>
    </div>

    <!-- 日期选择 + 执行 -->
    <div class="execute-bar">
      <div class="date-section">
        <span class="label">基准日期</span>
        <el-date-picker
          v-model="baseDate"
          type="date"
          placeholder="选择日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          :disabled="isExecuting"
          style="width: 180px"
        />
      </div>
      <el-button
        type="primary"
        size="large"
        :icon="CaretRight"
        :loading="isExecuting"
        :disabled="!filesReady"
        @click="handleExecute"
      >
        {{ isExecuting ? 'ETL 执行中...' : '执行 ETL' }}
      </el-button>
    </div>

    <!-- 执行状态 -->
    <div v-if="isExecuting" class="executing-indicator">
      <el-icon class="is-loading spinning"><Loading /></el-icon>
      <span>ETL 执行中，请稍候...</span>
      <el-progress
        :percentage="pollProgress"
        :stroke-width="6"
        :show-text="false"
        style="width: 200px; margin-left: 16px"
      />
    </div>

    <!-- 执行完成消息 -->
    <el-alert
      v-if="etlCompleted && !isExecuting"
      title="ETL 执行成功"
      type="success"
      :closable="false"
      show-icon
      class="result-alert"
    />

    <!-- ETL 摘要 KPI 卡片 -->
    <div v-if="etlCompleted && summary" class="summary-cards">
      <el-card shadow="hover" class="kpi-card">
        <template #header>
          <span class="kpi-title">效期预警</span>
        </template>
        <div class="kpi-body">
          <div class="kpi-item warning">
            <el-statistic :value="summary.expiry_warning?.预警 || 0">
              <template #title>
                <span class="kpi-label">预警</span>
              </template>
            </el-statistic>
          </div>
          <el-divider direction="vertical" />
          <div class="kpi-item normal">
            <el-statistic :value="summary.expiry_warning?.正常 || 0">
              <template #title>
                <span class="kpi-label">正常</span>
              </template>
            </el-statistic>
          </div>
        </div>
      </el-card>

      <el-card shadow="hover" class="kpi-card">
        <template #header>
          <span class="kpi-title">周转预警</span>
        </template>
        <div class="kpi-body">
          <div class="kpi-item warning">
            <el-statistic :value="summary.turnover_warning?.预警 || 0">
              <template #title>
                <span class="kpi-label">预警</span>
              </template>
            </el-statistic>
          </div>
          <el-divider direction="vertical" />
          <div class="kpi-item normal">
            <el-statistic :value="summary.turnover_warning?.正常 || 0">
              <template #title>
                <span class="kpi-label">正常</span>
              </template>
            </el-statistic>
          </div>
        </div>
      </el-card>

      <el-card shadow="hover" class="kpi-card">
        <template #header>
          <span class="kpi-title">趋势预警</span>
        </template>
        <div class="kpi-body">
          <div class="kpi-item warning">
            <el-statistic :value="summary.trend_warning?.预警 || 0">
              <template #title>
                <span class="kpi-label">预警</span>
              </template>
            </el-statistic>
          </div>
          <el-divider direction="vertical" />
          <div class="kpi-item normal">
            <el-statistic :value="summary.trend_warning?.正常 || 0">
              <template #title>
                <span class="kpi-label">正常</span>
              </template>
            </el-statistic>
          </div>
        </div>
      </el-card>

      <el-card shadow="hover" class="kpi-card">
        <template #header>
          <span class="kpi-title">综合风险</span>
        </template>
        <div class="kpi-body risk-body">
          <el-tag type="danger" size="large" effect="dark" class="risk-tag">
            高风险 {{ summary.综合风险?.高风险 || 0 }}
          </el-tag>
          <el-tag type="warning" size="large" class="risk-tag">
            中风险 {{ summary.综合风险?.中风险 || 0 }}
          </el-tag>
          <el-tag type="success" size="large" class="risk-tag">
            低风险 {{ summary.综合风险?.低风险 || 0 }}
          </el-tag>
        </div>
      </el-card>
    </div>

    <!-- STG 表预览 -->
    <div v-if="etlCompleted" class="stg-section">
      <el-collapse v-model="stgExpanded">
        <el-collapse-item title="展开查看清洗后原始表（STG）" name="stg">
          <el-tabs v-model="activeStgTab" @tab-change="handleTabChange">
            <el-tab-pane
              v-for="tab in stgTabs"
              :key="tab.key"
              :label="tab.label"
              :name="tab.key"
            >
              <div v-if="stgLoading[tab.key]" class="stg-loading">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>加载中...</span>
              </div>
              <div v-else-if="stgData[tab.key]">
                <div class="stg-meta">
                  <el-tag size="small" type="info">{{ stgData[tab.key].total_rows }} 行</el-tag>
                  <el-tag size="small" type="info">{{ stgData[tab.key].total_columns }} 列</el-tag>
                </div>
                <el-table
                  :data="stgTableRows(tab.key)"
                  stripe
                  border
                  size="small"
                  max-height="400"
                  style="width: 100%"
                >
                  <el-table-column
                    v-for="(col, idx) in stgData[tab.key].columns"
                    :key="idx"
                    :prop="String(idx)"
                    :label="col"
                    min-width="120"
                    show-overflow-tooltip
                  />
                </el-table>
              </div>
              <el-empty v-else description="暂无数据" />
            </el-tab-pane>
          </el-tabs>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  CaretRight,
  Loading,
  InfoFilled,
  Coin,
  Document,
} from '@element-plus/icons-vue'
import {
  getFileList,
  executeEtlTask,
  getTaskStatus,
  getDbStatus,
  previewStgTable,
} from '@/api/etl'

// ==================== 状态 ====================
const baseDate = ref(new Date().toISOString().slice(0, 10))
const isExecuting = ref(false)
const etlCompleted = ref(false)
const currentTaskId = ref(null)
const summary = ref(null)
const pollProgress = ref(0)
let pollTimer = null

// 文件 & 数据库状态
const fileCount = ref(0)
const fileIds = ref([])
const filesReady = computed(() => fileCount.value > 0)
const dbStatus = reactive({ connected: false, table_count: 0 })

// STG 表预览
const stgExpanded = ref([])
const activeStgTab = ref('stg_purchase_req')
const stgTabs = [
  { key: 'stg_purchase_req', label: '请购单' },
  { key: 'stg_purchase_order', label: '采购单' },
  { key: 'stg_stock_in', label: '入库单' },
  { key: 'stg_sales_out', label: '销售出库单' },
  { key: 'stg_stock_current', label: '现存量' },
]
const stgData = reactive({})
const stgLoading = reactive({})

// ==================== 数据加载 ====================
async function loadFileList() {
  try {
    const res = await getFileList()
    const data = res.data || {}
    const files = data.files || []
    fileCount.value = files.length
    fileIds.value = files.map(f => f.file_id)
  } catch {
    fileCount.value = 0
    fileIds.value = []
  }
}

async function loadDbStatus() {
  try {
    const res = await getDbStatus()
    const data = res.data || {}
    dbStatus.connected = data.connected || false
    dbStatus.table_count = data.table_count || 0

    // 检查 STG 表是否有数据
    const stgTables = data.stg_tables || []
    const hasStgData = stgTables.some(t => t.rows > 0)
    if (hasStgData) {
      etlCompleted.value = true
      // 预加载所有 STG 表数据
      for (const tab of stgTabs) {
        await loadStgTable(tab.key)
      }
    }
  } catch {
    dbStatus.connected = false
    dbStatus.table_count = 0
  }
}

// ==================== 执行 ETL ====================
async function handleExecute() {
  if (!filesReady.value) {
    ElMessage.warning('请先上传源文件')
    return
  }

  isExecuting.value = true
  etlCompleted.value = false
  summary.value = null
  pollProgress.value = 0

  try {
    const res = await executeEtlTask(fileIds.value)
    const data = res.data || {}
    currentTaskId.value = data.task_id

    if (data.task_id) {
      startPolling(data.task_id)
    } else {
      // 同步返回结果
      handleResult(data)
    }
  } catch (error) {
    isExecuting.value = false
    ElMessage.error('ETL 执行启动失败')
  }
}

function startPolling(taskId) {
  pollTimer = setInterval(async () => {
    try {
      const res = await getTaskStatus(taskId)
      const data = res.data || {}

      if (data.status === 'completed') {
        handleResult(data)
        stopPolling()
      } else if (data.status === 'failed') {
        isExecuting.value = false
        ElMessage.error(data.error || data.message || 'ETL 执行失败')
        stopPolling()
      } else {
        // 进行中，更新进度条
        pollProgress.value = Math.min(pollProgress.value + 8, 90)
      }
    } catch {
      // 网络错误，继续轮询
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function handleResult(data) {
  isExecuting.value = false
  pollProgress.value = 100
  etlCompleted.value = true

  const result = data.summary || data.result?.summary || null
  if (result) {
    summary.value = normalizeSummary(result)
  }

  ElMessage.success('ETL 执行成功')
  // 刷新数据库状态
  loadDbStatus()
}

function normalizeSummary(raw) {
  // Backend returns counts directly, e.g. { expiry_warning: { "预警": 10, "正常": 50 } }
  // Make sure all keys exist
  const empty = { 预警: 0, 正常: 0 }
  return {
    expiry_warning: raw.expiry_warning || empty,
    turnover_warning: raw.turnover_warning || empty,
    trend_warning: raw.trend_warning || empty,
    综合风险: raw.综合风险 || { 高风险: 0, 中风险: 0, 低风险: 0 },
  }
}

// ==================== STG 表预览 ====================
async function handleTabChange(tabKey) {
  if (stgData[tabKey]) return
  await loadStgTable(tabKey)
}

async function loadStgTable(tableKey) {
  stgLoading[tableKey] = true
  try {
    const res = await previewStgTable(tableKey, 100)
    const data = res.data || {}
    stgData[tableKey] = {
      table_name: data.table_name,
      total_rows: data.total_rows || 0,
      total_columns: data.total_columns || 0,
      columns: data.columns || [],
      data: data.data || [],
    }
  } catch {
    stgData[tableKey] = null
  } finally {
    stgLoading[tableKey] = false
  }
}

function stgTableRows(tabKey) {
  const d = stgData[tabKey]
  if (!d || !d.data) return []
  return d.data.map(row => {
    const obj = {}
    d.columns.forEach((_, idx) => {
      obj[String(idx)] = row[idx] != null ? String(row[idx]) : ''
    })
    return obj
  })
}

// ==================== 生命周期 ====================
onMounted(() => {
  loadFileList()
  loadDbStatus()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.etl-page {
  padding: 20px;
}

/* 顶部状态栏 */
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.status-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
}

.hint-icon {
  color: #409eff;
  font-size: 16px;
}

.status-info {
  display: flex;
  gap: 12px;
}

.status-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 执行栏 */
.execute-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 0;
  margin-bottom: 20px;
}

.date-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

/* 执行中指示器 */
.executing-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fdf6ec;
  border-radius: 8px;
  margin-bottom: 20px;
  color: #e6a23c;
  font-size: 14px;
}

.spinning {
  font-size: 20px;
}

/* 结果提示 */
.result-alert {
  margin-bottom: 20px;
}

/* 摘要卡片 */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.kpi-card :deep(.el-card__header) {
  padding: 10px 16px;
  background: #fafafa;
}

.kpi-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.kpi-body {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 4px 0;
}

.kpi-item {
  text-align: center;
}

.kpi-label {
  font-size: 12px;
  color: #909399;
}

.kpi-item.warning :deep(.el-statistic__number) {
  color: #e6a23c;
}

.kpi-item.normal :deep(.el-statistic__number) {
  color: #67c23a;
}

.risk-body {
  flex-wrap: wrap;
  gap: 8px;
}

.risk-tag {
  margin: 0;
}

/* STG 预览区 */
.stg-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
}

.stg-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.stg-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 0;
  color: #909399;
}

/* 响应式 */
@media (max-width: 1200px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .status-bar {
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }

  .execute-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-cards {
    grid-template-columns: 1fr;
  }
}
</style>
