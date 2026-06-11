<template>
  <div class="status-bar">
    <div class="status-item">
      <el-icon><Monitor /></el-icon>
      <span>Context:</span>
      <span class="value">{{ tokenStore.formattedContextLength }}/{{ tokenStore.formattedMaxContext }}</span>
      <div class="mini-progress">
        <div
          class="mini-progress-bar"
          :class="getProgressClass(tokenStore.contextUsagePercent)"
          :style="{ width: tokenStore.contextUsagePercent + '%' }"
        />
      </div>
      <span class="percent">{{ tokenStore.contextUsagePercent }}%</span>
    </div>

    <div class="status-divider" />

    <div class="status-item">
      <el-icon><Tickets /></el-icon>
      <span>Tokens:</span>
      <span class="value">
        <span class="token-type input">In: {{ tokenStore.formattedInputTokens }}</span>
        <span class="token-type output">Out: {{ tokenStore.formattedOutputTokens }}</span>
        <span class="token-type total">Total: {{ tokenStore.formattedTotalTokens }}</span>
      </span>
    </div>

    <div class="status-divider" />

    <div class="status-item time">
      <el-icon><Clock /></el-icon>
      <span class="value">{{ currentTime }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useTokenStore } from '@/stores/token'
import { Monitor, Tickets, Clock } from '@element-plus/icons-vue'

const tokenStore = useTokenStore()
const currentTime = ref('')
let timeInterval = null

function getProgressClass(percent) {
  if (percent >= 90) return 'danger'
  if (percent >= 70) return 'warning'
  return 'normal'
}

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

onMounted(() => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})
</script>

<style scoped>
.status-bar {
  height: 28px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: linear-gradient(180deg, rgba(26, 31, 46, 0.98) 0%, rgba(26, 31, 46, 0.92) 100%);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 12px;
  color: #94a3b8;
  gap: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-item .el-icon {
  font-size: 14px;
  color: #64748b;
}

.status-item span {
  white-space: nowrap;
}

.status-item .value {
  color: #e2e8f0;
  font-weight: 500;
}

.mini-progress {
  width: 50px;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
  margin-left: 4px;
}

.mini-progress-bar {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 2px;
}

.mini-progress-bar.normal {
  background: linear-gradient(90deg, #00d9c0, #00b8a9);
}

.mini-progress-bar.warning {
  background: linear-gradient(90deg, #f59e0b, #d97706);
}

.mini-progress-bar.danger {
  background: linear-gradient(90deg, #ef4444, #dc2626);
}

.percent {
  font-size: 11px;
  min-width: 30px;
  text-align: right;
}

.token-type {
  margin-right: 8px;
}

.token-type.input {
  color: #60a5fa;
}

.token-type.output {
  color: #f472b6;
}

.token-type.total {
  color: #00d9c0;
}

.status-divider {
  width: 1px;
  height: 16px;
  background: rgba(255, 255, 255, 0.1);
}

.status-item.time .value {
  font-variant-numeric: tabular-nums;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 11px;
}

/* Mobile responsive */
@media (max-width: 767px) {
  .status-bar {
    padding: 0 10px;
    font-size: 11px;
    gap: 8px;
  }

  .mini-progress {
    display: none;
  }

  .token-type {
    margin-right: 4px;
  }
}
</style>