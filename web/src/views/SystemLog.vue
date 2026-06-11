<template>
  <div class="system-log-page">
    <div class="page-header">
      <h2>系统日志</h2>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs" @tab-change="handleTabChange">
      <!-- Tab 1: 安全日志 -->
      <el-tab-pane label="安全日志" name="audit">
        <div class="tab-content">
          <div class="filter-bar">
            <el-select
              v-model="auditFilters.type_filter"
              placeholder="事件类型"
              clearable
              style="flex: 1"
              @change="loadAuditLogs"
            >
              <el-option
                v-for="opt in auditTypeOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-select
              v-model="auditFilters.level_filter"
              placeholder="级别"
              clearable
              style="flex: 1"
              @change="loadAuditLogs"
            >
              <el-option label="全部" value="" />
              <el-option label="INFO" value="INFO" />
              <el-option label="WARN" value="WARN" />
              <el-option label="ERROR" value="ERROR" />
            </el-select>
            <el-input
              v-model="auditFilters.user_filter"
              placeholder="用户名"
              clearable
              style="flex: 1"
              @change="loadAuditLogs"
            />
            <el-input
              v-model="auditFilters.keyword"
              placeholder="关键词"
              clearable
              style="flex: 1"
              @change="loadAuditLogs"
            />
            <el-select
              v-model="auditFilters.limit"
              style="flex: 1"
              @change="loadAuditLogs"
            >
              <el-option :value="50" label="50条" />
              <el-option :value="100" label="100条" />
              <el-option :value="200" label="200条" />
              <el-option :value="500" label="500条" />
            </el-select>
          </div>
          <DataTable
            :data="auditLogs"
            :columns="logColumns"
            :loading="auditLoading"
            :show-pagination="true"
            :page-size="20"
            stripe
          >
            <template #level="{ row }">
              <span
                class="level-tag"
                :class="levelClass(row.level)"
              >
                {{ row.level }}
              </span>
            </template>
          </DataTable>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 业务日志 -->
      <el-tab-pane label="业务日志" name="business">
        <div class="tab-content">
          <div class="filter-bar">
            <el-select
              v-model="businessFilters.type_filter"
              placeholder="事件类型"
              clearable
              style="flex: 1"
              @change="loadBusinessLogs"
            >
              <el-option
                v-for="opt in businessTypeOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-select
              v-model="businessFilters.level_filter"
              placeholder="级别"
              clearable
              style="flex: 1"
              @change="loadBusinessLogs"
            >
              <el-option label="全部" value="" />
              <el-option label="INFO" value="INFO" />
              <el-option label="WARN" value="WARN" />
              <el-option label="ERROR" value="ERROR" />
            </el-select>
            <el-input
              v-model="businessFilters.user_filter"
              placeholder="用户名"
              clearable
              style="flex: 1"
              @change="loadBusinessLogs"
            />
            <el-input
              v-model="businessFilters.keyword"
              placeholder="关键词"
              clearable
              style="flex: 1"
              @change="loadBusinessLogs"
            />
            <el-select
              v-model="businessFilters.limit"
              style="flex: 1"
              @change="loadBusinessLogs"
            >
              <el-option :value="50" label="50条" />
              <el-option :value="100" label="100条" />
              <el-option :value="200" label="200条" />
              <el-option :value="500" label="500条" />
            </el-select>
          </div>
          <DataTable
            :data="businessLogs"
            :columns="logColumns"
            :loading="businessLoading"
            :show-pagination="true"
            :page-size="20"
            stripe
          >
            <template #level="{ row }">
              <span
                class="level-tag"
                :class="levelClass(row.level)"
              >
                {{ row.level }}
              </span>
            </template>
          </DataTable>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 错误日志 -->
      <el-tab-pane label="错误日志" name="error">
        <div class="tab-content">
          <div class="filter-bar">
            <el-select
              v-model="errorFilters.type_filter"
              placeholder="事件类型"
              clearable
              style="flex: 1"
              @change="loadErrorLogs"
            >
              <el-option
                v-for="opt in errorTypeOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-select
              v-model="errorFilters.level_filter"
              placeholder="级别"
              clearable
              style="flex: 1"
              @change="loadErrorLogs"
            >
              <el-option label="全部" value="" />
              <el-option label="INFO" value="INFO" />
              <el-option label="WARN" value="WARN" />
              <el-option label="ERROR" value="ERROR" />
            </el-select>
            <el-input
              v-model="errorFilters.user_filter"
              placeholder="用户名"
              clearable
              style="flex: 1"
              @change="loadErrorLogs"
            />
            <el-input
              v-model="errorFilters.keyword"
              placeholder="关键词"
              clearable
              style="flex: 1"
              @change="loadErrorLogs"
            />
            <el-select
              v-model="errorFilters.limit"
              style="flex: 1"
              @change="loadErrorLogs"
            >
              <el-option :value="50" label="50条" />
              <el-option :value="100" label="100条" />
              <el-option :value="200" label="200条" />
              <el-option :value="500" label="500条" />
            </el-select>
          </div>
          <DataTable
            :data="errorLogs"
            :columns="logColumns"
            :loading="errorLoading"
            :show-pagination="true"
            :page-size="20"
            stripe
          >
            <template #level="{ row }">
              <span
                class="level-tag"
                :class="levelClass(row.level)"
              >
                {{ row.level }}
              </span>
            </template>
          </DataTable>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import { getAuditLogs, getBusinessLogs, getErrorLogs } from '@/api/logs'

// ========== 事件类型映射 ==========
const eventTypeLabels = {
  AUTH_LOGIN: '登录成功',
  AUTH_LOGIN_FAIL: '登录失败',
  AUTH_LOGOUT: '退出登录',
  PERM_CHANGE: '权限变更',
  PWD_CHANGE: '密码修改',
  ETL_START: 'ETL开始',
  ETL_DONE: 'ETL成功',
  ETL_FAIL: 'ETL失败',
  DATA_IMPORT: '数据导入',
  PAGE_CRASH: '页面崩溃',
}

const auditTypeOptions = [
  { label: '登录成功', value: 'AUTH_LOGIN' },
  { label: '登录失败', value: 'AUTH_LOGIN_FAIL' },
  { label: '退出登录', value: 'AUTH_LOGOUT' },
  { label: '权限变更', value: 'PERM_CHANGE' },
  { label: '密码修改', value: 'PWD_CHANGE' },
]

const businessTypeOptions = [
  { label: 'ETL开始', value: 'ETL_START' },
  { label: 'ETL成功', value: 'ETL_DONE' },
  { label: 'ETL失败', value: 'ETL_FAIL' },
  { label: '数据导入', value: 'DATA_IMPORT' },
]

const errorTypeOptions = [
  { label: '页面崩溃', value: 'PAGE_CRASH' },
  { label: 'ETL失败', value: 'ETL_FAIL' },
]

// ========== Tab 状态 ==========
const activeTab = ref('audit')

// ========== 筛选条件 ==========
const defaultFilters = () => ({
  type_filter: '',
  level_filter: '',
  user_filter: '',
  keyword: '',
  limit: 200,
})

const auditFilters = reactive(defaultFilters())
const businessFilters = reactive(defaultFilters())
const errorFilters = reactive(defaultFilters())

// ========== 日志数据 ==========
const auditLogs = ref([])
const businessLogs = ref([])
const errorLogs = ref([])

const auditLoading = ref(false)
const businessLoading = ref(false)
const errorLoading = ref(false)

// ========== 表格列定义 ==========
const logColumns = [
  { prop: 'timestamp', label: '时间', width: 190 },
  { prop: 'level', label: '级别', width: 80, slot: true },
  {
    prop: 'event',
    label: '事件',
    width: 120,
    formatter: (row) => eventTypeLabels[row.event] || row.event || '-',
  },
  { prop: 'user', label: '用户', width: 120 },
  { prop: 'role', label: '角色', width: 100 },
  { prop: 'ip', label: 'IP', width: 140 },
  { prop: 'message', label: '消息', minWidth: 200 },
]

// ========== 级别样式 ==========
function levelClass(level) {
  if (level === 'ERROR') return 'level-error'
  if (level === 'WARN') return 'level-warn'
  return 'level-info'
}

// ========== 加载数据 ==========
async function loadAuditLogs() {
  auditLoading.value = true
  try {
    const res = await getAuditLogs({
      type_filter: auditFilters.type_filter,
      level_filter: auditFilters.level_filter,
      user_filter: auditFilters.user_filter,
      keyword: auditFilters.keyword,
      limit: auditFilters.limit,
    })
    auditLogs.value = res.data?.items || []
  } catch {
    auditLogs.value = []
  } finally {
    auditLoading.value = false
  }
}

async function loadBusinessLogs() {
  businessLoading.value = true
  try {
    const res = await getBusinessLogs({
      type_filter: businessFilters.type_filter,
      level_filter: businessFilters.level_filter,
      user_filter: businessFilters.user_filter,
      keyword: businessFilters.keyword,
      limit: businessFilters.limit,
    })
    businessLogs.value = res.data?.items || []
  } catch {
    businessLogs.value = []
  } finally {
    businessLoading.value = false
  }
}

async function loadErrorLogs() {
  errorLoading.value = true
  try {
    const res = await getErrorLogs({
      type_filter: errorFilters.type_filter,
      level_filter: errorFilters.level_filter,
      user_filter: errorFilters.user_filter,
      keyword: errorFilters.keyword,
      limit: errorFilters.limit,
    })
    errorLogs.value = res.data?.items || []
  } catch {
    errorLogs.value = []
  } finally {
    errorLoading.value = false
  }
}

function handleTabChange(tab) {
  if (tab === 'audit') loadAuditLogs()
  else if (tab === 'business') loadBusinessLogs()
  else if (tab === 'error') loadErrorLogs()
}

// ========== 初始化 ==========
onMounted(() => {
  loadAuditLogs()
})
</script>

<style scoped>
.system-log-page {
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

.main-tabs {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
}

.tab-content {
  padding: 16px 0;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.level-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.level-error {
  background-color: #fef0f0;
  color: #f56c6c;
}

.level-warn {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.level-info {
  background-color: #f4f4f5;
  color: #909399;
}
</style>
