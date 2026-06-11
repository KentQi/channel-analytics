<template>
  <div class="notification-bell" ref="bellRef">
    <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
      <el-button circle @click="togglePanel">
        <el-icon :size="20"><Bell /></el-icon>
      </el-button>
    </el-badge>

    <!-- Dropdown Panel -->
    <el-popover
      :visible="panelVisible"
      placement="bottom-end"
      :width="360"
      trigger="click"
      @update:visible="panelVisible = $event"
    >
      <template #reference>
        <span class="popover-trigger" style="display:none;"></span>
      </template>

      <div class="notification-panel">
        <div class="panel-header">
          <span class="panel-title">通知</span>
          <el-button link type="primary" @click="markAllRead" v-if="notifications.length">
            全部已读
          </el-button>
        </div>

        <div class="notification-list" v-if="notifications.length">
          <div
            v-for="notif in notifications"
            :key="notif.id"
            class="notification-item"
            :class="{ unread: !notif.is_read }"
            @click="handleNotificationClick(notif)"
          >
            <div class="notification-content">
              <p class="notification-title">{{ notif.title }}</p>
              <p class="notification-text" v-if="notif.content">{{ notif.content }}</p>
              <span class="notification-time">{{ formatTime(notif.created_at) }}</span>
            </div>
            <el-button
              v-if="!notif.is_read"
              link
              type="primary"
              size="small"
              @click.stop="handleMarkRead(notif)"
            >
              标记已读
            </el-button>
          </div>
        </div>

        <el-empty v-else description="暂无通知" :image-size="60" />

        <div class="panel-footer" v-if="notifications.length">
          <router-link to="/alerts" class="view-all" @click="panelVisible = false">
            查看全部
          </router-link>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Bell } from '@element-plus/icons-vue'
import { useAlertsStore } from '@/stores/alerts'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'

const store = useAlertsStore()
const { notifications, stats } = storeToRefs(store)

const panelVisible = ref(false)
const bellRef = ref(null)

const unreadCount = computed(() => stats.value.unread_notifications)

async function fetchNotifications() {
  await store.fetchNotifications({ is_read: false })
  await store.fetchStats()
}

async function handleMarkRead(notif) {
  await store.markAsRead(notif.id)
  await store.fetchStats()
}

async function markAllRead() {
  for (const notif of notifications.value) {
    if (!notif.is_read) {
      await store.markAsRead(notif.id)
    }
  }
  await store.fetchStats()
  ElMessage.success('全部已读')
}

function handleNotificationClick(notif) {
  if (!notif.is_read) {
    handleMarkRead(notif)
  }
  // Navigate to alerts page
  panelVisible.value = false
}

function formatTime(timeStr) {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return timeStr.substring(0, 10)
}

function togglePanel() {
  panelVisible.value = !panelVisible.value
  if (panelVisible.value) {
    fetchNotifications()
  }
}

// Close panel when clicking outside
function handleClickOutside(event) {
  if (bellRef.value && !bellRef.value.contains(event.target)) {
    panelVisible.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  // Initial fetch
  store.fetchStats()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.notification-bell {
  position: relative;
  display: inline-block;
}

.notification-panel {
  max-height: 400px;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 8px;
}

.panel-title {
  font-weight: 600;
  color: var(--text-primary);
}

.notification-list {
  max-height: 300px;
  overflow-y: auto;
}

.notification-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background 0.2s;
}

.notification-item:hover {
  background: var(--bg-card-hover);
}

.notification-item.unread {
  background: rgba(0, 217, 192, 0.05);
}

.notification-item:last-child {
  border-bottom: none;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-size: 14px;
  color: var(--text-primary);
  margin: 0 0 4px 0;
  font-weight: 500;
}

.notification-text {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0 0 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notification-time {
  font-size: 11px;
  color: var(--text-muted);
}

.panel-footer {
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
  text-align: center;
}

.view-all {
  color: var(--accent-primary);
  text-decoration: none;
  font-size: 14px;
}

.view-all:hover {
  text-decoration: underline;
}
</style>
