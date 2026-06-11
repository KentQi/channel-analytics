<template>
  <div class="rpa-management">
    <!-- 顶部状态卡片 -->
    <el-row :gutter="16" class="status-cards">
      <el-col :span="6">
        <el-card shadow="hover" body-style="padding: 16px; height: 72px; display: flex; align-items: center; justify-content: center">
          <div class="stat-item">
            <div class="stat-label">任务总数</div>
            <div class="stat-value">{{ stats.total_tasks || 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" body-style="padding: 16px; height: 72px; display: flex; align-items: center; justify-content: center">
          <div class="stat-item">
            <div class="stat-label">运行正常</div>
            <div class="stat-value success">{{ stats.last_success || 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" body-style="padding: 16px; height: 72px; display: flex; align-items: center; justify-content: center">
          <div class="stat-item">
            <div class="stat-label">异常</div>
            <div class="stat-value danger">{{ stats.last_failed || 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" body-style="padding: 16px; height: 72px; display: flex; align-items: center; justify-content: center">
          <div class="stat-item">
            <div class="stat-label">上次执行</div>
            <div class="stat-value small">{{ stats.last_run_at || '暂无' }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务配置表 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>采集任务配置</span>
          <div style="display: flex; gap: 8px">
            <el-button @click="rpaConfigVisible = true">
              <el-icon><Setting /></el-icon> RPA配置
            </el-button>
            <el-button type="success" @click="handleRunAll" :loading="runAllLoading">
              <el-icon><VideoPlay /></el-icon> 临时采集
            </el-button>
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon> 新增任务
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="tasks" v-loading="loading" stripe>
        <el-table-column prop="name" label="任务名称" min-width="140" />
        <el-table-column prop="module_name" label="采集模块" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.module_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="定时计划" min-width="180">
          <template #default="{ row }">
            <div>{{ formatSchedule(row.schedule_times, row.schedule_days) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '运行中' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上次结果" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.last_run_status === 'success'" class="text-success">成功</span>
            <span v-else-if="row.last_run_status === 'failed'" class="text-danger">失败</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="下次执行" width="160">
          <template #default="{ row }">
            {{ row.next_run_at ? formatTime(row.next_run_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" align="center">
          <template #default="{ row }">
            <el-button link type="success" size="small" @click="handleRunTask(row)">运行</el-button>
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="viewLogs(row)">日志</el-button>
            <el-button link :type="row.enabled ? 'warning' : 'success'" size="small" @click="handleToggle(row)">
              {{ row.enabled ? '禁用' : '启用' }}
            </el-button>
            <el-popconfirm title="确定删除此任务？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 最近执行日志 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>执行日志</span>
          <el-button text @click="loadLogs">刷新</el-button>
        </div>
      </template>

      <el-table :data="logs" v-loading="logsLoading" stripe size="small"
        :row-class-name="logRowClass">
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="类型" width="86" align="center">
          <template #default="{ row }">
            <el-tag :type="logKindTag(row).type" size="small">{{ logKindTag(row).label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="任务" min-width="160">
          <template #default="{ row }">
            <span>{{ row.task_name || row.task_real_name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="80">
          <template #default="{ row }">{{ row.duration_sec ? `${row.duration_sec}s` : '-' }}</template>
        </el-table-column>
        <el-table-column label="说明" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.log_kind === 'etl' || (!row.log_kind && row.task_id === 0)" :class="row.status === 'success' ? 'text-success' : 'text-danger'">
              {{ row.error_msg || '-' }}
            </span>
            <span v-else-if="row.file_path" class="text-muted">文件: {{ row.file_path.split(/[/\\]/).pop() }}</span>
            <span v-else-if="row.error_msg" class="text-danger" style="font-size: 12px">{{ row.error_msg.substring(0, 80) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 任务编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑任务' : '新增任务'" width="700px" destroy-on-close>
      <el-form :model="form" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="任务名称" required>
              <el-input v-model="form.name" placeholder="如：每日采购入库采集" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="采集模块" required>
              <el-select v-model="form.module_name" placeholder="选择模块" style="width: 100%" @change="onModuleChange">
                <el-option v-for="m in modules" :key="m.name" :label="m.name" :value="m.name" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="定时时间" required>
          <div class="schedule-times">
            <div v-for="(time, idx) in form.schedule_times" :key="idx" class="time-tag">
              <el-time-picker v-model="form.schedule_times[idx]" format="HH:mm" value-format="HH:mm"
                placeholder="选择时间" style="width: 120px" />
              <el-button link type="danger" @click="form.schedule_times.splice(idx, 1)"
                :disabled="form.schedule_times.length <= 1">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-button @click="form.schedule_times.push('09:00')" :disabled="form.schedule_times.length >= 6">
              + 添加时间点
            </el-button>
          </div>
          <div class="quick-times">
            <el-button size="small" @click="setQuickTime(['09:00'])">每天 09:00</el-button>
            <el-button size="small" @click="setQuickTime(['09:00', '18:00'])">09:00 + 18:00</el-button>
            <el-button size="small" @click="setQuickTime(['08:00', '12:00', '18:00'])">三班制</el-button>
          </div>
        </el-form-item>

        <el-form-item label="执行日期">
          <el-radio-group v-model="form.schedule_days">
            <el-radio-button value="daily">每天</el-radio-button>
            <el-radio-button value="weekdays">工作日</el-radio-button>
            <el-radio-button value="weekend">周末</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-divider />

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="失败重试">
              <el-input-number v-model="form.max_retries" :min="0" :max="10" />
              <span style="margin-left: 8px">次</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="重试间隔">
              <el-input-number v-model="form.retry_interval" :min="1" :max="60" />
              <span style="margin-left: 8px">分钟</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="验证码策略">
          <el-radio-group v-model="form.captcha_strategy">
            <el-radio value="skip">跳过本次</el-radio>
            <el-radio value="notify">通知人工介入</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="超时时间">
          <el-input-number v-model="form.timeout_seconds" :min="60" :max="1800" :step="60" />
          <span style="margin-left: 8px">秒</span>
          <span style="margin-left: 12px; color: #909399; font-size: 12px">
            (现存量90s，采购入库180s，销售出库600s)
          </span>
        </el-form-item>

        <el-form-item label="通知收件人">
          <el-input v-model="form.notify_targets" placeholder="留空则使用全局默认收件人，多个用逗号分隔" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- RPA配置弹窗（登录 + 邮件通知） -->
    <el-dialog v-model="rpaConfigVisible" title="RPA配置" width="560px" destroy-on-close>
      <el-tabs v-model="rpaConfigTab">
        <el-tab-pane label="登录信息" name="login">
          <el-form :model="loginConfig" label-width="100px" style="margin-top: 8px">
            <el-form-item label="登录地址">
              <el-input v-model="loginConfig.rpa_erp_url" placeholder="https://erp.example.com" />
            </el-form-item>
            <el-form-item label="账号">
              <el-input v-model="loginConfig.rpa_erp_username" placeholder="手机号/邮箱" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="loginConfig.rpa_erp_password" type="password" show-password placeholder="密码" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="邮件通知" name="email">
          <el-form :model="emailConfig" label-width="100px" style="margin-top: 8px">
            <el-form-item label="SMTP服务器">
              <el-input v-model="emailConfig.smtp_host" placeholder="smtp.qq.com" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input-number v-model="emailConfig.smtp_port" :min="1" :max="65535" style="width: 120px" />
              <el-radio-group v-model="emailConfig.smtp_port" style="margin-left: 12px">
                <el-radio-button :value="465">465 SSL</el-radio-button>
                <el-radio-button :value="587">587 TLS</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="发件人邮箱">
              <el-input v-model="emailConfig.smtp_user" placeholder="sender@qq.com" />
            </el-form-item>
            <el-form-item label="授权码/密码">
              <el-input v-model="emailConfig.smtp_password" type="password" show-password placeholder="SMTP授权码" />
            </el-form-item>
            <el-form-item label="默认收件人">
              <el-input v-model="emailConfig.smtp_default_to" placeholder="多个用逗号分隔，如 a@x.com, b@x.com" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="rpaConfigVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRpaConfig" :loading="rpaConfigSaving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 采集预览弹窗 -->
    <el-dialog v-model="previewVisible" title="临时采集确认" width="520px">
      <div style="margin-bottom: 16px; color: #606266; font-size: 14px">
        以下任务将按顺序执行采集，预计总耗时约 5~8 分钟：
      </div>
      <el-table :data="tasks.filter(t => t.enabled)" stripe size="small" :show-header="true">
        <el-table-column label="采集模块" min-width="140">
          <template #default="{ row }">
            <el-tag size="small">{{ row.module_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上次执行" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.last_run_status === 'success'" class="text-success">成功</span>
            <span v-else-if="row.last_run_status === 'failed'" class="text-danger">失败</span>
            <span v-else class="text-muted">未执行</span>
          </template>
        </el-table-column>
        <el-table-column label="上次时间" width="140">
          <template #default="{ row }">
            {{ row.last_run_at ? formatTime(row.last_run_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="超时" width="80" align="center">
          <template #default="{ row }">
            {{ formatTimeout(row.timeout_seconds) }}
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 16px; padding: 12px; background: #f0f9eb; border-radius: 6px; font-size: 13px; color: #67c23a">
        💡 采集完成后系统将自动检查 5 张表是否齐全，齐全后自动执行 ETL 数据导入。
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">取消</el-button>
        <el-button type="success" @click="confirmRunAll" :loading="runAllLoading">
          <el-icon><VideoPlay /></el-icon> 确认采集
        </el-button>
      </template>
    </el-dialog>

    <!-- 采集进度弹窗 -->
    <el-dialog v-model="progressVisible" title="采集进度" width="520px" :close-on-click-modal="false"
      :close-on-press-escape="false" :show-close="progressAllDone">
      <div class="progress-list">
        <div v-for="item in progressItems" :key="item.moduleId" class="progress-item">
          <div class="progress-item-header">
            <span class="progress-name">{{ item.name }}</span>
            <div style="display: flex; align-items: center; gap: 10px">
              <span v-if="item.status === 'running'" class="timer-running">
                {{ formatElapsed(elapsedMap[item.moduleId] || 0) }}
              </span>
              <span v-else-if="item.status === 'waiting'" class="timer-waiting">等待中</span>
              <span v-else class="timer-done">{{ formatDuration(item.duration) }}</span>
              <el-tag :type="progressTagType(item.status)" size="small">
                {{ progressStatusText(item.status) }}
              </el-tag>
            </div>
          </div>
          <div v-if="item.status === 'running'" class="progress-bar-bg">
            <div class="progress-bar-running"></div>
          </div>
          <div v-if="item.file" class="progress-detail">
            文件: {{ item.file }}
          </div>
          <div v-if="item.error" class="progress-error">{{ item.error }}</div>
        </div>
      </div>
      <div v-if="!progressAllDone" style="text-align: center; margin-top: 12px; color: #909399; font-size: 13px">
        正在采集中，请勿关闭页面...
      </div>
      <div v-if="progressAllDone" style="text-align: center; margin-top: 12px">
        <el-tag :type="progressSummary.type" size="large">{{ progressSummary.text }}</el-tag>
      </div>
      <template #footer>
        <div style="display: flex; gap: 8px; justify-content: flex-end">
          <el-button v-if="!progressAllDone" type="danger" @click="handleStopAll" :loading="stopLoading">
            ⏹ 停止采集
          </el-button>
          <el-button v-if="progressAllDone" type="primary" @click="progressVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Plus, Delete, VideoPlay, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getRpaStats, getRpaTasks, getRpaModules, getRpaLogs,
  createRpaTask, updateRpaTask, deleteRpaTask, toggleRpaTask,
  runRpaTask, runAllRpaTasks, stopRpaTasks,
  getRpaLoginConfig, updateRpaLoginConfig,
  getRpaEmailConfig, updateRpaEmailConfig
} from '@/api/rpa'

const loading = ref(false)
const logsLoading = ref(false)
const saving = ref(false)
const tasks = ref([])
const logs = ref([])
const modules = ref([])
const stats = ref({})
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)

const defaultForm = {
  name: '',
  module_name: '',
  schedule_times: ['09:00'],
  schedule_days: 'daily',
  max_retries: 3,
  retry_interval: 5,
  timeout_seconds: 180,
  captcha_strategy: 'skip',
  notify_channels: [],
  notify_targets: '',
}
const form = ref({ ...defaultForm })

// RPA配置弹窗（登录 + 邮件通知）
const rpaConfigVisible = ref(false)
const rpaConfigTab = ref('login')
const rpaConfigSaving = ref(false)
const loginConfig = ref({ rpa_erp_url: '', rpa_erp_username: '', rpa_erp_password: '' })
const emailConfig = ref({ smtp_host: '', smtp_port: 465, smtp_user: '', smtp_password: '', smtp_default_to: '' })
const runAllLoading = ref(false)
const stopLoading = ref(false)

// 采集进度
const previewVisible = ref(false)
const progressVisible = ref(false)
const progressItems = ref([])  // [{moduleId, name, status, duration, file, error}]
const progressAllDone = ref(false)
let progressTimer = null
let elapsedTimer = null
const elapsedMap = ref({})   // {moduleId: seconds}
const taskStartMap = {}       // {moduleId: startTimestamp}
let progressTriggeredAt = null  // 触发时间戳，用于区分新旧日志
let etlWaitPolls = 0            // ETL 等待轮询计数（超时则标记跳过）

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  if (progressTimer) clearInterval(progressTimer)
  if (elapsedTimer) clearInterval(elapsedTimer)
})

async function loadData() {
  loading.value = true
  try {
    const [tasksRes, statsRes, modulesRes] = await Promise.all([
      getRpaTasks(),
      getRpaStats(),
      getRpaModules(),
    ])
    tasks.value = tasksRes.data || tasksRes
    stats.value = statsRes.data || statsRes
    modules.value = modulesRes.data || modulesRes
    await Promise.all([loadLogs(), loadLoginConfig(), loadEmailConfig()])
  } catch (e) {
    console.error('加载RPA数据失败:', e)
  } finally {
    loading.value = false
  }
}

async function loadLogs() {
  logsLoading.value = true
  try {
    const res = await getRpaLogs({ limit: 20 })
    logs.value = res.data || res
  } catch (e) {
    console.error('加载日志失败:', e)
  } finally {
    logsLoading.value = false
  }
}

function openCreateDialog() {
  isEdit.value = false
  editingId.value = null
  form.value = { ...defaultForm, schedule_times: ['09:00'] }
  dialogVisible.value = true
}

function openEditDialog(task) {
  isEdit.value = true
  editingId.value = task.id
  let times = task.schedule_times
  if (typeof times === 'string') times = JSON.parse(times)
  form.value = {
    name: task.name,
    module_name: task.module_name,
    schedule_times: times || ['09:00'],
    schedule_days: task.schedule_days || 'daily',
    max_retries: task.max_retries ?? 3,
    retry_interval: task.retry_interval ?? 5,
    timeout_seconds: task.timeout_seconds ?? 180,
    captcha_strategy: task.captcha_strategy || 'skip',
    notify_channels: task.notify_channels || [],
    notify_targets: task.notify_targets || '',
  }
  dialogVisible.value = true
}

function setQuickTime(times) {
  form.value.schedule_times = [...times]
}

// 模块切换时自动设置默认超时
function onModuleChange(val) {
  const timeoutMap = { '采购入库': 180, '销售出库': 600, '现存量查询': 90 }
  if (timeoutMap[val] && !isEdit.value) {
    form.value.timeout_seconds = timeoutMap[val]
  }
}

async function handleSave() {
  if (!form.value.name || !form.value.module_name) {
    ElMessage.warning('请填写任务名称和采集模块')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await updateRpaTask(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createRpaTask(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function handleToggle(task) {
  try {
    await toggleRpaTask(task.id)
    ElMessage.success(task.enabled ? '已禁用' : '已启用')
    await loadData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function handleDelete(id) {
  try {
    await deleteRpaTask(id)
    ElMessage.success('已删除')
    await loadData()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

function viewLogs(task) {
  // 筛选该任务的日志
  getRpaLogs({ task_id: task.id, limit: 50 }).then(res => {
    logs.value = res.data || res
  })
}

function formatSchedule(times, days) {
  if (!times) return '-'
  let t = typeof times === 'string' ? JSON.parse(times) : times
  const dayMap = { daily: '每天', weekdays: '工作日', weekend: '周末' }
  const dayText = dayMap[days] || days || '每天'
  return `${dayText} ${t.join(', ')}`
}

function formatTime(t) {
  if (!t) return '-'
  const d = new Date(t)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}-${dd} ${hh}:${mi}`
}

// 单个任务运行
async function handleRunTask(task) {
  try {
    const res = await runRpaTask(task.id)
    ElMessage.success(res.data?.message || `任务 '${task.name}' 已触发`)
  } catch (e) {
    ElMessage.error('触发失败: ' + (e.response?.data?.detail || e.message))
  }
}

// 临时采集：先预览
async function handleRunAll() {
  previewVisible.value = true
}

// 确认采集：执行并显示进度（按模块粒度）
async function confirmRunAll() {
  previewVisible.value = false
  runAllLoading.value = true
  try {
    const res = await runAllRpaTasks()
    const triggered = res.data?.tasks || []

    // 解析任务包含的模块列表
    const allModules = []
    for (const t of triggered) {
      try {
        const mods = typeof t.module_name === 'string' ? JSON.parse(t.module_name) : t.module_name
        if (Array.isArray(mods)) allModules.push(...mods)
      } catch {
        if (t.module_name) allModules.push(t.module_name)
      }
    }

    progressTriggeredAt = Date.now()
    etlWaitPolls = 0
    elapsedMap.value = {}
    Object.keys(taskStartMap).forEach(k => delete taskStartMap[k])

    // 按模块初始化进度列表
    progressItems.value = allModules.map((mod, idx) => ({
      moduleId: mod,
      name: mod,
      status: idx === 0 ? 'running' : 'waiting',
      duration: null,
      file: null,
      error: null,
      logId: null,
    }))

    // 追加 ETL 进度项（所有采集模块完成后自动触发）
    progressItems.value.push({
      moduleId: 'ETL 数据导入',
      name: 'ETL 数据导入',
      status: 'waiting',
      duration: null,
      file: null,
      error: null,
      logId: null,
    })

    // 第一个模块开始计时
    if (allModules.length > 0) {
      taskStartMap[allModules[0]] = Date.now()
      elapsedMap.value[allModules[0]] = 0
    }

    progressAllDone.value = false
    progressVisible.value = true

    startElapsedTimer()
    startProgressPolling()
    ElMessage.success(res.data?.message || '已触发全部任务')
  } catch (e) {
    ElMessage.error('触发失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    runAllLoading.value = false
  }
}

function startElapsedTimer() {
  if (elapsedTimer) clearInterval(elapsedTimer)
  elapsedTimer = setInterval(() => {
    for (const item of progressItems.value) {
      if (item.status === 'running' && taskStartMap[item.moduleId]) {
        elapsedMap.value[item.moduleId] = Math.floor((Date.now() - taskStartMap[item.moduleId]) / 1000)
      }
    }
  }, 1000)
}

function stopElapsedTimer() {
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
}

function startNextTask(finishedIdx) {
  const items = progressItems.value
  for (let i = finishedIdx + 1; i < items.length; i++) {
    if (items[i].status === 'waiting') {
      items[i].status = 'running'
      taskStartMap[items[i].moduleId] = Date.now()
      elapsedMap.value[items[i].moduleId] = 0
      return
    }
  }
}

function startProgressPolling() {
  if (progressTimer) clearInterval(progressTimer)
  progressTimer = setInterval(async () => {
    try {
      const res = await getRpaLogs({ limit: 50 })
      const logs = res.data || res

      let allDone = true
      for (let idx = 0; idx < progressItems.value.length; idx++) {
        const item = progressItems.value[idx]
        if (item.status !== 'running') {
          if (item.status === 'waiting') allDone = false
          continue
        }

        // ETL 特殊处理：匹配 task_name='ETL 数据导入' 且 task_id=0
        let match = null
        if (item.moduleId === 'ETL 数据导入') {
          match = logs.find(l =>
            l.task_name === 'ETL 数据导入' &&
            l.task_id === 0 &&
            l.status !== 'running' &&
            new Date(l.started_at).getTime() >= progressTriggeredAt &&
            !progressItems.value.some(p => p.logId === l.id && p.moduleId !== item.moduleId)
          )
          // ETL 超时：轮询超过 20 次（60秒）仍无任何 ETL 日志，标记为跳过
          if (!match) {
            const etlLogExists = logs.some(l =>
              l.task_name === 'ETL 数据导入' &&
              l.task_id === 0 &&
              new Date(l.started_at).getTime() >= progressTriggeredAt
            )
            if (!etlLogExists) {
              etlWaitPolls++
              if (etlWaitPolls > 20) {
                item.status = 'skipped'
                item.error = '未触发 ETL（数据表不齐全）'
                loadLogs()
                continue
              }
            }
          }
        } else {
          // 按 task_name（模块名）匹配，找到该模块已完成的日志
          match = logs.find(l =>
            l.task_name === item.moduleId &&
            l.status !== 'running' &&
            new Date(l.started_at).getTime() >= progressTriggeredAt &&
            !progressItems.value.some(p => p.logId === l.id && p.moduleId !== item.moduleId)
          )
        }

        if (match) {
          item.status = match.status
          item.duration = match.duration_sec
          item.file = match.file_path ? match.file_path.split(/[/\\]/).pop() : null
          item.error = match.error_msg
          item.logId = match.id
          loadLogs()
          startNextTask(idx)
        } else {
          allDone = false
        }
      }

      if (allDone) {
        clearInterval(progressTimer)
        progressTimer = null
        stopElapsedTimer()
        progressAllDone.value = true
        loadData()  // 刷新任务列表和日志
      }
    } catch (e) {
      console.error('轮询进度失败:', e)
    }
  }, 3000)
}

function formatElapsed(seconds) {
  if (!seconds || seconds < 0) return '00:00'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds >= 60) {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return s ? `${m}分${s}秒` : `${m}分钟`
  }
  return `${seconds}秒`
}

function progressTagType(status) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'skipped') return 'info'
  if (status === 'waiting') return 'info'
  return 'warning'
}

const LOG_KIND_TAGS = {
  etl:    { type: 'warning', label: 'ETL' },
  main:   { type: 'primary', label: '主任务' },
  module: { type: 'info', label: '模块' },
}
function logKindTag(row) {
  // 兼容历史数据：后端未返回 log_kind 时按 task_id 推断
  const k = row.log_kind || (row.task_id === 0 ? 'etl' : 'main')
  return LOG_KIND_TAGS[k] || { type: 'info', label: '-' }
}
function logRowClass({ row }) {
  const k = row.log_kind || (row.task_id === 0 ? 'etl' : null)
  if (k === 'etl') return 'etl-row'
  if (k === 'main') return 'main-row'
  return ''
}

function progressStatusText(status) {
  if (status === 'success') return '完成'
  if (status === 'failed') return '失败'
  if (status === 'skipped') return '跳过'
  if (status === 'waiting') return '等待中'
  return '采集中'
}

// 停止采集
async function handleStopAll() {
  stopLoading.value = true
  try {
    const res = await stopRpaTasks()
    ElMessage.warning(res.data?.message || '已停止')
    // 将仍在 running/waiting 的任务标记为 stopped
    for (const item of progressItems.value) {
      if (item.status === 'running' || item.status === 'waiting') {
        const wasWaiting = item.status === 'waiting'
        item.status = 'failed'
        item.error = wasWaiting ? '已取消' : '用户手动停止'
      }
    }
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    stopElapsedTimer()
    progressAllDone.value = true
    loadData()
  } catch (e) {
    ElMessage.error('停止失败')
  } finally {
    stopLoading.value = false
  }
}

const progressSummary = computed(() => {
  const items = progressItems.value
  const successCount = items.filter(i => i.status === 'success').length
  const skipCount = items.filter(i => i.status === 'skipped').length
  const failCount = items.filter(i => i.status === 'failed').length
  const doneCount = successCount + skipCount
  const summary = skipCount > 0 ? `（含${skipCount}项跳过）` : ''
  if (failCount === 0) return { type: 'success', text: `全部完成 ✅ ${doneCount}/${items.length}${summary}` }
  if (doneCount === 0) return { type: 'danger', text: `全部失败 ❌ ${failCount}/${items.length}` }
  return { type: 'warning', text: `部分完成 ⚠️ 成功${doneCount} 失败${failCount}` }
})

// RPA配置（登录 + 邮件通知）
async function loadLoginConfig() {
  try {
    const res = await getRpaLoginConfig()
    loginConfig.value = res.data || res
  } catch (e) {
    console.error('加载登录配置失败:', e)
  }
}

async function loadEmailConfig() {
  try {
    const res = await getRpaEmailConfig()
    emailConfig.value = res.data || res
  } catch (e) {
    console.error('加载邮件配置失败:', e)
  }
}

async function saveRpaConfig() {
  rpaConfigSaving.value = true
  try {
    await Promise.all([
      updateRpaLoginConfig(loginConfig.value),
      updateRpaEmailConfig(emailConfig.value),
    ])
    ElMessage.success('RPA配置已保存')
    rpaConfigVisible.value = false
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    rpaConfigSaving.value = false
  }
}

function formatTimeout(seconds) {
  if (!seconds) return '-'
  if (seconds >= 60) return `${Math.floor(seconds / 60)}分${seconds % 60 ? seconds % 60 + '秒' : ''}`
  return `${seconds}秒`
}
</script>

<style scoped>
.rpa-management {
  padding: 16px;
}
.status-cards {
  margin-bottom: 16px;
}
.stat-item {
  text-align: center;
}
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}
.stat-value.success { color: #67c23a; }
.stat-value.danger { color: #f56c6c; }
.stat-value.small { font-size: 16px; margin-top: 4px; }
.section-card {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.text-success { color: #67c23a; }
.text-danger { color: #f56c6c; }
.text-muted { color: #c0c4cc; }
.schedule-times {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.time-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}
.quick-times {
  margin-top: 8px;
}
.progress-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.progress-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}
.progress-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.progress-name {
  font-weight: 500;
  font-size: 14px;
}
.timer-running {
  font-family: 'Courier New', monospace;
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
  letter-spacing: 1px;
}
.timer-waiting {
  font-size: 13px;
  color: #c0c4cc;
}
.timer-done {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  color: #909399;
}
.progress-bar-bg {
  height: 4px;
  background: #e4e7ed;
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}
.progress-bar-running {
  width: 30%;
  height: 100%;
  background: #409eff;
  border-radius: 2px;
  animation: progress-slide 1.5s ease-in-out infinite;
}
@keyframes progress-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(433%); }
}
.progress-detail {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.progress-error {
  font-size: 12px;
  color: #f56c6c;
  margin-top: 4px;
  word-break: break-all;
}
:deep(.etl-row) {
  background-color: #fdf6ec !important;
}
:deep(.etl-row:hover > td) {
  background-color: #faecd8 !important;
}
:deep(.main-row td:first-child) {
  box-shadow: inset 3px 0 0 #409EFF;
}
:deep(.main-row:hover > td) {
  background-color: #ecf5ff !important;
}
</style>
