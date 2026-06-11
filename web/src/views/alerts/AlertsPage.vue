<template>
  <div class="alerts-page">
    <el-tabs v-model="activeTab" class="alerts-tabs">
      <el-tab-pane label="预警规则" name="rules">
        <AlertRules />
      </el-tab-pane>
      <el-tab-pane label="预警历史" name="history">
        <AlertHistory />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AlertRules from './AlertRules.vue'
import AlertHistory from './AlertHistory.vue'

const activeTab = ref('rules')
</script>

<style scoped>
.alerts-page {
  height: 100%;
  padding: 20px;
}

.alerts-tabs {
  height: 100%;
}

.alerts-tabs :deep(.el-tabs__content) {
  height: calc(100% - 40px);
  overflow-y: auto;
}
</style>
