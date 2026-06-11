<template>
  <div class="repurchase-page">
    <!-- 子菜单 Tab 切换 -->
    <div class="sub-menu-tabs">
      <!-- 客户留存 Tab 组 -->
      <div v-if="currentSection === 'customer'" class="tab-group">
        <span class="tab-group-label">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
          </svg>
          客户返单
        </span>
        <div class="tab-items">
          <div
            v-for="item in customerTabs"
            :key="item.path"
            class="tab-item"
            :class="{ active: currentPath === item.path }"
            @click="navigateTo(item.path)"
          >
            {{ item.label }}
          </div>
        </div>
      </div>

      <!-- 商品返单 Tab 组 -->
      <div v-if="currentSection === 'product'" class="tab-group">
        <span class="tab-group-label">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
            <line x1="7" y1="7" x2="7.01" y2="7"/>
          </svg>
          商品返单
        </span>
        <div class="tab-items">
          <div
            v-for="item in productTabs"
            :key="item.path"
            class="tab-item"
            :class="{ active: currentPath === item.path }"
            @click="navigateTo(item.path)"
          >
            {{ item.label }}
          </div>
        </div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-area">
      <router-view :key="$route.fullPath" />
    </div>

    <!-- Loading Overlay -->
    <LoadingOverlay :show="loading" />
  </div>
</template>

<script setup>
import { ref, computed, watch, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LoadingOverlay } from '@/components/common'

const route = useRoute()
const router = useRouter()
const loading = ref(false)

// Provide loading state to child components
provide('setLoading', (val) => {
  loading.value = val
})

const customerTabs = [
  { label: '客户留存', path: '/repurchase/customer/overview' },
  { label: '客户返单', path: '/repurchase/customer/detail' },
  { label: '流失预警', path: '/repurchase/customer/churn' },
  { label: '新客追踪', path: '/repurchase/customer/new-customer' },
  { label: '客户价值', path: '/repurchase/customer/value' }
]

const productTabs = [
  { label: '单品返单', path: '/repurchase/product/retention' },
  { label: '销量追踪', path: '/repurchase/product/sales' },
  { label: '新品预警', path: '/repurchase/product/new-product' }
]

const currentPath = computed(() => route.path)

const currentSection = computed(() => {
  const path = route.path
  if (path.startsWith('/repurchase/customer')) return 'customer'
  if (path.startsWith('/repurchase/product')) return 'product'
  return 'customer'
})

function navigateTo(path) {
  router.push(path)
}

// 监听路由变化，更新 Tab 状态
watch(() => route.path, (newPath) => {
  currentPath.value = newPath
}, { immediate: true })
</script>

<style scoped>
.repurchase-page {
  padding: 20px;
  position: relative;
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

.sub-menu-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 12px;
  margin-bottom: 20px;
  border: 1px solid #e8edf2;
}

.tab-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tab-group-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.tab-group-label svg {
  width: 14px;
  height: 14px;
}

.tab-items {
  display: flex;
  gap: 4px;
}

.tab-item {
  padding: 8px 16px;
  font-size: 13px;
  color: #64748b;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.tab-item:hover {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.08);
}

.tab-item.active {
  color: #3b82f6;
  background: #fff;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06);
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 2px;
  background: #3b82f6;
  border-radius: 2px 2px 0 0;
}

.content-area {
  min-height: 400px;
  position: relative;
}
</style>
