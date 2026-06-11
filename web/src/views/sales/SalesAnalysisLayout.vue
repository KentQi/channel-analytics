<template>
  <div class="sales-analysis-layout">
    <router-view :key="$route.fullPath" />
    <LoadingOverlay :show="loading" />
  </div>
</template>

<script setup>
import { ref, provide } from 'vue'
import { LoadingOverlay } from '@/components/common'

const loading = ref(false)
provide('setLoading', (val) => {
  loading.value = val
})
</script>

<style scoped>
.sales-analysis-layout {
  padding: 20px;
}
</style>
