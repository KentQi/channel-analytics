<template>
  <div class="advanced-page">
    <router-view />
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
.advanced-page {
  padding: 20px;
}
</style>
