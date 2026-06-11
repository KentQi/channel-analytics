<template>
  <div class="alert-rules">
    <!-- Header -->
    <div class="page-header">
      <h2 class="page-title">预警规则</h2>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon> 新建规则
      </el-button>
    </div>

    <!-- Filter -->
    <div class="filter-bar">
      <el-select v-model="filterType" placeholder="预警类型" clearable @change="fetchRules">
        <el-option label="销售下滑" value="sales_decline" />
        <el-option label="库存积压" value="inventory_overstock" />
        <el-option label="客户流失" value="customer_churn" />
        <el-option label="效期预警" value="expiry_warning" />
      </el-select>
      <el-select v-model="filterEnabled" placeholder="状态" clearable @change="fetchRules">
        <el-option label="已启用" :value="true" />
        <el-option label="已禁用" :value="false" />
      </el-select>
    </div>

    <!-- Rules Table -->
    <el-table :data="rules" v-loading="loading" stripe>
      <el-table-column prop="name" label="规则名称" min-width="150" />
      <el-table-column prop="alert_type" label="类型" width="140">
        <template #default="{ row }">
          <el-tag :type="getTypeTagType(row.alert_type)">{{ getTypeLabel(row.alert_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="check_interval" label="检测频率" width="100">
        <template #default="{ row }">
          {{ getIntervalLabel(row.check_interval) }}
        </template>
      </el-table-column>
      <el-table-column prop="is_enabled" label="状态" width="80">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_enabled"
            @change="handleToggle(row)"
          />
        </template>
      </el-table-column>
      <el-table-column prop="notify_channels" label="通知渠道" width="140">
        <template #default="{ row }">
          <span v-if="row.notify_channels && row.notify_channels.length">
            {{ row.notify_channels.join(', ') }}
          </span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
          <el-button link type="warning" @click="handleTest(row)">测试</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建预警规则' : '编辑预警规则'"
      width="600px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入规则名称" />
        </el-form-item>

        <el-form-item label="预警类型" prop="alert_type">
          <el-select v-model="form.alert_type" placeholder="请选择预警类型" :disabled="dialogMode === 'edit'">
            <el-option label="销售下滑" value="sales_decline" />
            <el-option label="库存积压" value="inventory_overstock" />
            <el-option label="客户流失" value="customer_churn" />
            <el-option label="效期预警" value="expiry_warning" />
          </el-select>
        </el-form-item>

        <!-- Config fields based on type -->
        <template v-if="form.alert_type === 'sales_decline'">
          <el-form-item label="连续下滑月数">
            <el-input-number v-model="form.config.consecutive_months" :min="2" :max="12" />
          </el-form-item>
          <el-form-item label="下滑阈值">
            <el-input-number v-model="form.config.decline_threshold" :min="0.01" :max="1" :step="0.05" :precision="2" />
            <span class="form-tip">（如0.2表示下滑超过20%）</span>
          </el-form-item>
        </template>

        <template v-if="form.alert_type === 'inventory_overstock'">
          <el-form-item label="周转天数阈值">
            <el-input-number v-model="form.config.turnover_days_threshold" :min="30" :max="365" />
          </el-form-item>
          <el-form-item label="库存金额阈值">
            <el-input-number v-model="form.config.inventory_amount_threshold" :min="10000" :step="10000" />
          </el-form-item>
        </template>

        <template v-if="form.alert_type === 'customer_churn'">
          <el-form-item label="最近购买天数">
            <el-input-number v-model="form.config.recency_days_threshold" :min="30" :max="180" />
          </el-form-item>
          <el-form-item label="最低购买次数">
            <el-input-number v-model="form.config.min_frequency" :min="1" :max="10" />
          </el-form-item>
        </template>

        <template v-if="form.alert_type === 'expiry_warning'">
          <el-form-item label="效期预警天数">
            <el-input-number v-model="form.config.expiry_days_threshold" :min="7" :max="90" />
          </el-form-item>
        </template>

        <el-form-item label="检测频率" prop="check_interval">
          <el-select v-model="form.check_interval">
            <el-option label="每小时" value="hourly" />
            <el-option label="每天" value="daily" />
            <el-option label="每周" value="weekly" />
          </el-select>
        </el-form-item>

        <el-form-item label="通知渠道">
          <el-checkbox-group v-model="form.notify_channels">
            <el-checkbox label="in_app">站内通知</el-checkbox>
            <el-checkbox label="email">邮件</el-checkbox>
            <el-checkbox label="webhook">Webhook</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="大区筛选">
          <el-input v-model="form.config.region" placeholder="留空表示全部大区" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Test Result Dialog -->
    <el-dialog v-model="testDialogVisible" title="测试结果" width="600px">
      <div v-if="testResult">
        <p>触发数量: <strong>{{ testResult.triggered_count }}</strong></p>
        <el-divider />
        <div v-if="testResult.results && testResult.results.length">
          <p class="mb-sm">前10条触发详情:</p>
          <el-table :data="testResult.results" size="small" max-height="300">
            <el-table-column
              v-for="col in testResultColumns"
              :key="col"
              :prop="col"
              :label="col"
            />
          </el-table>
        </div>
        <el-empty v-else description="暂无触发数据" />
      </div>
      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAlertsStore } from '@/stores/alerts'
import { storeToRefs } from 'pinia'

const store = useAlertsStore()
const { rules, loading } = storeToRefs(store)

const filterType = ref('')
const filterEnabled = ref('')
const dialogVisible = ref(false)
const dialogMode = ref('create')
const submitting = ref(false)
const testDialogVisible = ref(false)
const testResult = ref(null)

const formRef = ref(null)

const form = reactive({
  name: '',
  alert_type: 'sales_decline',
  config: {
    consecutive_months: 2,
    decline_threshold: 0.2,
    turnover_days_threshold: 180,
    inventory_amount_threshold: 100000,
    recency_days_threshold: 90,
    min_frequency: 2,
    expiry_days_threshold: 30,
    region: null,
  },
  check_interval: 'daily',
  notify_channels: ['in_app'],
})

const formRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  alert_type: [{ required: true, message: '请选择预警类型', trigger: 'change' }],
  check_interval: [{ required: true, message: '请选择检测频率', trigger: 'change' }],
}

const typeLabels = {
  sales_decline: '销售下滑',
  inventory_overstock: '库存积压',
  customer_churn: '客户流失',
  expiry_warning: '效期预警',
}

const typeTagTypes = {
  sales_decline: 'danger',
  inventory_overstock: 'warning',
  customer_churn: 'info',
  expiry_warning: 'success',
}

const intervalLabels = {
  hourly: '每小时',
  daily: '每天',
  weekly: '每周',
}

function getTypeLabel(type) {
  return typeLabels[type] || type
}

function getTypeTagType(type) {
  return typeTagTypes[type] || 'info'
}

function getIntervalLabel(interval) {
  return intervalLabels[interval] || interval
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return dateStr.substring(0, 16)
}

const testResultColumns = computed(() => {
  if (!testResult.value?.results?.length) return []
  return Object.keys(testResult.value.results[0])
})

async function fetchRules() {
  const params = {}
  if (filterType.value) params.alert_type = filterType.value
  if (filterEnabled.value !== '') params.is_enabled = filterEnabled.value
  await store.fetchRules(params)
}

function openCreateDialog() {
  dialogMode.value = 'create'
  dialogVisible.value = true
}

function openEditDialog(row) {
  dialogMode.value = 'edit'
  dialogVisible.value = true
  form.name = row.name
  form.alert_type = row.alert_type
  form.check_interval = row.check_interval
  form.notify_channels = row.notify_channels || ['in_app']
  // Deep merge config
  if (row.config) {
    Object.keys(row.config).forEach(key => {
      if (form.config.hasOwnProperty(key)) {
        form.config[key] = row.config[key]
      }
    })
  }
}

function resetForm() {
  form.name = ''
  form.alert_type = 'sales_decline'
  form.check_interval = 'daily'
  form.notify_channels = ['in_app']
  form.config = {
    consecutive_months: 2,
    decline_threshold: 0.2,
    turnover_days_threshold: 180,
    inventory_amount_threshold: 100000,
    recency_days_threshold: 90,
    min_frequency: 2,
    expiry_days_threshold: 30,
    region: null,
  }
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = {
      name: form.name,
      alert_type: form.alert_type,
      config: { ...form.config },
      check_interval: form.check_interval,
      notify_channels: form.notify_channels,
    }

    if (dialogMode.value === 'create') {
      await store.createRule(payload)
      ElMessage.success('创建成功')
    } else {
      // Find the rule id from rules list
      const rule = rules.value.find(r => r.name === form.name)
      if (rule) {
        await store.updateRule(rule.id, payload)
        ElMessage.success('保存成功')
      }
    }
    dialogVisible.value = false
    fetchRules()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleToggle(row) {
  try {
    await store.updateRule(row.id, { is_enabled: row.is_enabled })
    ElMessage.success(row.is_enabled ? '已启用' : '已禁用')
  } catch (e) {
    // Revert
    row.is_enabled = !row.is_enabled
    ElMessage.error('操作失败')
  }
}

async function handleTest(row) {
  try {
    testResult.value = await store.testRule(row.id)
    testDialogVisible.value = true
  } catch (e) {
    ElMessage.error('测试执行失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除规则 "${row.name}" 吗？`, '确认删除', {
      type: 'warning',
    })
    await store.deleteRule(row.id)
    ElMessage.success('删除成功')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  fetchRules()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.form-tip {
  margin-left: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.text-muted {
  color: var(--text-muted);
}

.mb-sm {
  margin-bottom: 8px;
}
</style>
