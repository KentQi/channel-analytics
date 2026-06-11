<template>
  <div>
    <!-- Overlay -->
    <transition name="fade">
      <div
        v-if="visible"
        class="mobile-sidebar-overlay"
        @click="close"
      />
    </transition>

    <!-- Drawer -->
    <transition name="slide">
      <div v-if="visible" class="mobile-sidebar-drawer">
        <div class="mobile-sidebar-header">
          <div class="logo-area">
            <svg class="logo-icon" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="8" fill="#00d9c0"/>
              <path d="M12 28V12h8v16h-8zm4-12v8h4v-8h-4zm8 12V16h4v12h-4z" fill="#0f1419"/>
            </svg>
            <span class="logo-text">Channel Analytics</span>
          </div>
          <el-button
            :icon="Close"
            text
            class="close-btn"
            @click="close"
          />
        </div>

        <el-menu
          :default-active="activeMenu"
          class="mobile-sidebar-menu"
          @select="handleSelect"
        >
          <el-sub-menu index="sales">
            <template #title>
              <el-icon><TrendCharts /></el-icon>
              <span>销售分析</span>
            </template>
            <el-menu-item index="/sales-analysis/wide-table">销售宽表</el-menu-item>
            <el-menu-item index="/sales-analysis/dashboard">出货仪表盘</el-menu-item>
            <el-menu-item index="/sales-analysis/indicator">指标进度</el-menu-item>
            <el-menu-item index="/sales-analysis/detail">销售明细</el-menu-item>
            <el-menu-item index="/sales-analysis/flow">货流明细</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="repurchase">
            <template #title>
              <el-icon><Refresh /></el-icon>
              <span>返单分析</span>
            </template>
            <el-menu-item index="/repurchase/customer">客户返单</el-menu-item>
            <el-menu-item index="/repurchase/product">商品返单</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="stock">
            <template #title>
              <el-icon><Box /></el-icon>
              <span>库存分析</span>
            </template>
            <el-menu-item index="/stock-analysis/overview">库存概览</el-menu-item>
            <el-menu-item index="/stock-analysis/turnover">周转分析</el-menu-item>
            <el-menu-item index="/stock-analysis/expiry">效期分析</el-menu-item>
            <el-menu-item index="/stock-analysis/trend">趋势分析</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="advanced">
            <template #title>
              <el-icon><Histogram /></el-icon>
              <span>高级分析</span>
            </template>
            <el-menu-item index="/advanced/product-lifecycle">商品生命周期</el-menu-item>
            <el-menu-item index="/advanced/customer-lifecycle">客户生命周期</el-menu-item>
            <el-menu-item index="/advanced/product-cluster">商品聚类</el-menu-item>
            <el-menu-item index="/advanced/customer-cluster">客户聚类</el-menu-item>
          </el-sub-menu>

          <el-menu-item index="/data-import">
            <el-icon><Upload /></el-icon>
            <span>数据导入</span>
          </el-menu-item>

          <el-menu-item index="/data-management">
            <el-icon><Management /></el-icon>
            <span>数据管理</span>
          </el-menu-item>

          <el-sub-menu index="system">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统</span>
            </template>
            <el-menu-item index="/permissions">权限管理</el-menu-item>
            <el-menu-item index="/logs">系统日志</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Close, TrendCharts, Refresh, Box, Histogram, Upload, Management, Setting } from '@element-plus/icons-vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const router = useRouter()
const route = useRoute()

const activeMenu = computed(() => route.path)

function close() {
  emit('close')
}

function handleSelect(index) {
  close()
  router.push(index)
}
</script>

<style scoped>
.mobile-sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 2000;
}

.mobile-sidebar-drawer {
  position: fixed;
  top: 0;
  left: 0;
  width: 280px;
  height: 100vh;
  background-color: #0f1419;
  z-index: 2001;
  overflow-y: auto;
}

.mobile-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  width: 32px;
  height: 32px;
}

.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  color: #909399;
}

.close-btn:hover {
  color: #fff;
}

.mobile-sidebar-menu {
  background-color: transparent;
  border-right: none;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
}
</style>
