<template>
  <div class="sales-detail">
    <!-- 子 Tab 切换 -->
    <div class="sub-tabs">
      <div
        v-for="item in subTabs"
        :key="item.name"
        class="sub-tab-item"
        :class="{ active: activeSubTab === item.name }"
        @click="activeSubTab = item.name"
      >
        {{ item.label }}
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-area">
      <component :is="currentComponent" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import ProductRanking from './detail/ProductRanking.vue'
import RegionCustomer from './detail/RegionCustomer.vue'
import RegionProduct from './detail/RegionProduct.vue'
import CustomerProduct from './detail/CustomerProduct.vue'
import Top30 from './detail/Top30.vue'

const activeSubTab = ref('product-ranking')

const subTabs = [
  { label: '单品出货排名', name: 'product-ranking' },
  { label: '区域×客户', name: 'region-customer' },
  { label: '区域×单品', name: 'region-product' },
  { label: '客户×单品', name: 'customer-product' },
  { label: 'TOP30', name: 'top30' }
]

const componentMap = {
  'product-ranking': ProductRanking,
  'region-customer': RegionCustomer,
  'region-product': RegionProduct,
  'customer-product': CustomerProduct,
  'top30': Top30
}

const currentComponent = computed(() => componentMap[activeSubTab.value] || ProductRanking)
</script>

<style scoped>
.sales-detail {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
}

.sub-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  padding: 8px;
  background-color: #f5f7fa;
  border-radius: 6px;
}

.sub-tab-item {
  padding: 8px 16px;
  font-size: 13px;
  color: #64748b;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sub-tab-item:hover {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.08);
}

.sub-tab-item.active {
  color: #fff;
  background: #3b82f6;
  font-weight: 600;
}

.content-area {
  min-height: 400px;
}
</style>
