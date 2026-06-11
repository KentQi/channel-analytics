<template>
  <div class="sidebar-wrapper">
    <div class="logo">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 3v18h18"/>
          <path d="M18 9l-5 5-4-4-3 3"/>
        </svg>
      </div>
      <span class="logo-text">销售分析</span>
    </div>

    <div class="sidebar-scroll">
      <el-menu
        :default-active="activeMenu"
        class="sidebar-menu"
        :collapse="isCollapse"
        background-color="transparent"
        text-color="#8b9199"
        active-text-color="#ffffff"
        :router="true"
      >
        <el-menu-item v-if="can('待办事项')" index="/todo">
          <el-icon><Clock /></el-icon>
          <template #title>待办事项</template>
        </el-menu-item>

        <el-sub-menu v-if="can('数据导入') || can('RPA采集')" index="data-collection">
          <template #title>
            <el-icon><Download /></el-icon>
            <span>数据采集</span>
          </template>
          <el-menu-item v-if="can('数据导入')" index="/data-import">
            <el-icon><Upload /></el-icon>
            <template #title>手动导入</template>
          </el-menu-item>
          <el-menu-item v-if="can('RPA采集')" index="/rpa">
            <el-icon><Monitor /></el-icon>
            <template #title>RPA采集</template>
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item v-if="can('ETL执行')" index="/etl">
          <el-icon><Lightning /></el-icon>
          <template #title>ETL执行</template>
        </el-menu-item>

        <div v-if="can('基础分析') || can('库存分析') || can('销售分析') || can('返单分析') || can('高级分析') || can('自定义报表')" class="menu-divider">
          <span>分析模块</span>
        </div>

        <el-menu-item v-if="can('基础分析')" index="/basis-analysis">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>基础分析</template>
        </el-menu-item>

        <el-menu-item v-if="can('库存分析')" index="/stock-analysis">
          <el-icon><Box /></el-icon>
          <template #title>库存分析</template>
        </el-menu-item>

        <el-sub-menu v-if="can('销售分析')" index="sales-analysis">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>销售分析</span>
          </template>
          <el-menu-item index="/sales-analysis/wide-table">销售宽表</el-menu-item>
          <el-menu-item index="/sales-analysis/dashboard">出货仪表盘</el-menu-item>
          <el-menu-item index="/sales-analysis/indicator">指标达成进度</el-menu-item>
          <el-menu-item index="/sales-analysis/detail">销售出库明细</el-menu-item>
          <el-menu-item index="/sales-analysis/flow">货流分析</el-menu-item>
        </el-sub-menu>

        <!-- 返单分析子菜单 -->
        <el-sub-menu v-if="can('返单分析')" index="repurchase">
          <template #title>
            <el-icon><Refresh /></el-icon>
            <span>返单分析</span>
          </template>

          <el-menu-item index="/repurchase/customer">客户返单</el-menu-item>
          <el-menu-item index="/repurchase/product">商品返单</el-menu-item>
        </el-sub-menu>

        <!-- 高级分析子菜单 -->
        <el-sub-menu v-if="can('高级分析')" index="advanced">
          <template #title>
            <el-icon><Histogram /></el-icon>
            <span>高级分析</span>
          </template>
          <el-menu-item index="/advanced/product-lifecycle">商品生命周期</el-menu-item>
          <el-menu-item index="/advanced/customer-lifecycle">客户生命周期</el-menu-item>
          <el-menu-item index="/advanced/product-cluster">商品聚类</el-menu-item>
          <el-menu-item index="/advanced/customer-cluster">客户聚类</el-menu-item>
        </el-sub-menu>

        <!-- 自定义分析 -->
        <el-menu-item v-if="can('自定义报表')" index="/reports">
          <el-icon><DataBoard /></el-icon>
          <template #title>自定义分析</template>
        </el-menu-item>

        <div v-if="can('预警通知') || can('信息维护')" class="menu-divider">
          <span>系统</span>
        </div>

        <el-menu-item v-if="can('预警通知')" index="/alerts">
          <el-icon><Bell /></el-icon>
          <template #title>预警通知</template>
        </el-menu-item>

        <el-menu-item v-if="can('信息维护')" index="/data-management">
          <el-icon><Setting /></el-icon>
          <template #title>信息维护</template>
        </el-menu-item>

        <!-- API配置子菜单 -->
        <el-sub-menu v-if="['admin', '创建人'].includes(authStore.role)" index="settings">
          <template #title>
            <el-icon><Connection /></el-icon>
            <span>API配置</span>
          </template>
          <el-menu-item index="/settings/llm-config">大模型API配置</el-menu-item>
        </el-sub-menu>

        <el-menu-item v-if="['admin', '创建人'].includes(authStore.role)" index="/permissions">
          <el-icon><Lock /></el-icon>
          <template #title>权限配置</template>
        </el-menu-item>

        <el-menu-item v-if="['admin', '创建人'].includes(authStore.role)" index="/system-log">
          <el-icon><Document /></el-icon>
          <template #title>系统日志</template>
        </el-menu-item>
      </el-menu>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  Clock,
  Upload,
  Lightning,
  DataAnalysis,
  Box,
  TrendCharts,
  Refresh,
  Setting,
  Lock,
  Document,
  Histogram,
  Bell,
  DataBoard,
  Connection,
  Download,
  Monitor
} from '@element-plus/icons-vue'

const route = useRoute()
const authStore = useAuthStore()
const isCollapse = false

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/')) {
    return path
  }
  return ''
})

// 模块权限判断（admin/创建人 = 全通过；其他角色按 modules 数组过滤）
const can = (moduleName) => authStore.hasModule(moduleName)
</script>

<style scoped>
/* CSS Variables for consistent theming */
:root {
  --sidebar-bg-start: #0f1419;
  --sidebar-bg-end: #1a1f2e;
  --accent-primary: #00d9c0;
  --accent-secondary: #8b5cf6;
  --accent-glow: rgba(0, 217, 192, 0.15);
  --text-primary: #e2e8f0;
  --text-muted: #64748b;
  --border-subtle: rgba(255, 255, 255, 0.06);
}

.sidebar-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, var(--sidebar-bg-start) 0%, var(--sidebar-bg-end) 100%);
  border-right: 1px solid var(--border-subtle);
  position: relative;
  overflow: hidden;
}

/* Subtle glow effect at top */
.sidebar-wrapper::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 200px;
  background: radial-gradient(ellipse at 50% 0%, var(--accent-glow) 0%, transparent 70%);
  pointer-events: none;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
  background: linear-gradient(180deg, rgba(26, 31, 46, 0.95) 0%, rgba(26, 31, 46, 0.88) 100%);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: relative;
  z-index: 1;
}

.logo-icon {
  width: 32px;
  height: 32px;
  color: var(--accent-primary);
  opacity: 1;
  filter: drop-shadow(0 0 8px var(--accent-primary));
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.logo-text {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  background: transparent;
  padding: 8px 0;
  position: relative;
  z-index: 1;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 220px;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  margin: 2px 12px;
  padding: 0 12px !important;
  border-radius: 8px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background: rgba(0, 217, 192, 0.08) !important;
  color: var(--accent-primary);
}

:deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(0, 217, 192, 0.18) 0%, rgba(0, 217, 192, 0.06) 100%) !important;
  color: var(--accent-primary);
}

:deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  background: var(--accent-primary);
  border-radius: 0 3px 3px 0;
  box-shadow: 0 0 12px var(--accent-primary);
}

.menu-divider {
  padding: 16px 24px 8px;
  position: relative;
}

.menu-divider::before {
  content: '';
  position: absolute;
  top: 24px;
  left: 24px;
  right: 24px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.06), transparent);
}

.menu-divider span {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1.5px;
}

:deep(.el-sub-menu .el-menu-item) {
  height: 36px;
  line-height: 36px;
  margin: 2px 0;
  padding: 0 12px 0 44px !important;
  font-size: 13px;
}

:deep(.el-sub-menu .el-menu-item:hover) {
  background: rgba(0, 217, 192, 0.06) !important;
  color: var(--accent-primary);
}

:deep(.el-sub-menu .el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(0, 217, 192, 0.12) 0%, rgba(0, 217, 192, 0.03) 100%) !important;
  color: var(--accent-primary);
}

:deep(.el-sub-menu .el-menu-item-group__title) {
  padding: 8px 12px 4px 44px;
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

:deep(.el-icon) {
  font-size: 16px;
}

/* ===== 子菜单样式增强 ===== */

/* 强制显示 el-sub-menu 的展开箭头 */
:deep(.el-sub-menu .el-sub-menu__icon-arrow) {
  font-size: 12px;
  color: var(--text-muted);
  transition: transform 0.3s;
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
}

/* 父级菜单标题样式 */
:deep(.el-sub-menu__title) {
  font-weight: 500;
  margin: 4px 12px;
  padding-right: 32px !important;
  position: relative;
}

/* 父级菜单 hover 时更明显 */
:deep(.el-sub-menu.is-opened > .el-sub-menu__title) {
  background: rgba(0, 217, 192, 0.12) !important;
  color: var(--accent-primary);
}

/* 子菜单项增加左侧小圆点指示器 */
:deep(.el-sub-menu .el-menu-item) {
  position: relative;
  margin: 2px 12px 2px 20px;
  padding-left: 36px !important;
  font-size: 13px;
}

/* 子菜单项左侧小圆点 */
:deep(.el-sub-menu .el-menu-item::before) {
  content: '';
  position: absolute;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 4px;
  background: var(--text-muted);
  border-radius: 50%;
  transition: background 0.25s;
}

/* 子菜单项 hover 时圆点变主题色 */
:deep(.el-sub-menu .el-menu-item:hover::before) {
  background: var(--accent-primary);
}

/* 子菜单激活项样式 */
:deep(.el-sub-menu .el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(0, 217, 192, 0.15) 0%, rgba(0, 217, 192, 0.05) 100%) !important;
  color: var(--accent-primary);
}

/* 子菜单激活项左侧圆点也变主题色 */
:deep(.el-sub-menu .el-menu-item.is-active::before) {
  background: var(--accent-primary);
  box-shadow: 0 0 6px var(--accent-primary);
}

/* 侧边栏滚动条 */
.sidebar-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-scroll::-webkit-scrollbar {
  width: 4px;
}

.sidebar-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
}

.sidebar-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.25);
}
</style>
