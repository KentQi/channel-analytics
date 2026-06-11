<template>
  <div class="alert-history">
    <!-- Header -->
    <div class="page-header">
      <h2 class="page-title">预警历史</h2>
    </div>

    <!-- Filter -->
    <div class="filter-bar">
      <el-select v-model="filterRuleId" placeholder="规则" clearable @change="fetchHistory">
        <el-option
          v-for="rule in rules"
          :key="rule.id"
          :label="rule.name"
          :value="rule.id"
        />
      </el-select>
      <el-select v-model="filterAcknowledged" placeholder="状态" clearable @change="fetchHistory">
        <el-option label="未确认" :value="false" />
        <el-option label="已确认" :value="true" />
      </el-select>
      <el-button @click="fetchHistory">刷新</el-button>
    </div>

    <!-- History Table -->
    <el-table :data="history" v-loading="loading" stripe>
      <el-table-column prop="alert_level" label="级别" width="100">
        <template #default="{ row }">
          <el-tag :type="getLevelTagType(row.alert_level)">{{ getLevelLabel(row.alert_level) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="预警标题" min-width="200" />
      <el-table-column prop="rule_name" label="规则" width="150">
        <template #default="{ row }">
          <span v-if="row.rule_name">{{ row.rule_name }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="triggered_count" label="触发数量" width="100" />
      <el-table-column prop="is_acknowledged" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_acknowledged ? 'success' : 'danger'" size="small">
            {{ row.is_acknowledged ? '已确认' : '未确认' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="acknowledged_by" label="确认人" width="100">
        <template #default="{ row }">
          {{ row.acknowledged_by || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="触发时间" width="160">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="showDetail(row)">详情</el-button>
          <el-button
            v-if="!row.is_acknowledged"
            link type="success"
            @click="handleAcknowledge(row)"
          >
            确认
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailDialogVisible" title="预警详情" width="700px">
      <div v-if="selectedHistory">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="预警标题">{{ selectedHistory.title }}</el-descriptions-item>
          <el-descriptions-item label="预警级别">
            <el-tag :type="getLevelTagType(selectedHistory.alert_level)">
              {{ getLevelLabel(selectedHistory.alert_level) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="关联规则">{{ selectedHistory.rule_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="触发数量">{{ selectedHistory.triggered_count }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedHistory.is_acknowledged ? 'success' : 'danger'">
              {{ selectedHistory.is_acknowledged ? '已确认' : '未确认' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="确认人">{{ selectedHistory.acknowledged_by || '-' }}</el-descriptions-item>
          <el-descriptions-item label="触发时间">{{ formatDate(selectedHistory.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="selectedHistory.content" class="mt-md">
          <h4>预警内容</h4>
          <p>{{ selectedHistory.content }}</p>
        </div>

        <div v-if="selectedHistory.detail_data && selectedHistory.detail_data.length" class="mt-md">
          <h4>触发详情</h4>
          <el-table :data="selectedHistory.detail_data" size="small" max-height="300">
            <el-table-column
              v-for="col in detailColumns"
              :key="col"
              :prop="col"
              :label="col"
            />
          </el-table>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button
          v-if="selectedHistory && !selectedHistory.is_acknowledged"
          type="primary"
          @click="handleAcknowledge(selectedHistory)"
        >
          确认预警
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAlertsStore } from '@/stores/alerts'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const store = useAlertsStore()
const authStore = useAuthStore()
const { history, rules, loading } = storeToRefs(store)

const filterRuleId = ref('')
const filterAcknowledged = ref('')
const detailDialogVisible = ref(false)
const selectedHistory = ref(null)

const levelLabels = {
  info: '提示',
  warning: '警告',
  critical: '严重',
}

const levelTagTypes = {
  info: 'info',
  warning: 'warning',
  critical: 'danger',
}

function getLevelLabel(level) {
  return levelLabels[level] || level
}

function getLevelTagType(level) {
  return levelTagTypes[level] || 'info'
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return dateStr.substring(0, 16)
}

const detailColumns = computed(() => {
  if (!selectedHistory.value?.detail_data?.length) return []
  return Object.keys(selectedHistory.value.detail_data[0])
})

async function fetchHistory() {
  const params = {}
  if (filterRuleId.value) params.rule_id = filterRuleId.value
  if (filterAcknowledged.value !== '') params.is_acknowledged = filterAcknowledged.value
  await store.fetchHistory(params)
}

function showDetail(row) {
  selectedHistory.value = row
  detailDialogVisible.value = true
}

async function handleAcknowledge(row) {
  try {
    await ElMessageBox.confirm('确认此预警？', '确认预警', {
      type: 'info',
    })
    const username = authStore.user?.username || 'system'
    await store.acknowledgeAlert(row.id, username)
    ElMessage.success('确认成功')
    detailDialogVisible.value = false
    fetchHistory()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('确认失败')
    }
  }
}

onMounted(async () => {
  await store.fetchRules()
  fetchHistory()
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

.text-muted {
  color: var(--text-muted);
}

.mt-md {
  margin-top: 16px;
}

h4 {
  margin-bottom: 8px;
  color: var(--text-primary);
}
</style>
