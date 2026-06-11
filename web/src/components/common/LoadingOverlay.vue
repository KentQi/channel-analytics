<template>
  <Transition name="fade">
    <div v-if="show" class="loading-overlay">
      <div class="loading-spinner">
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
      </div>
      <p class="loading-text">{{ text }}</p>
    </div>
  </Transition>
</template>

<script setup>
defineProps({
  show: { type: Boolean, default: false },
  text: { type: String, default: '加载中...' }
})
</script>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 56px;
  left: 200px;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.loading-spinner {
  width: 60px;
  height: 60px;
  position: relative;
}

.spinner-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 3px solid transparent;
  border-top-color: #409EFF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-ring:nth-child(1) { animation-delay: 0s; }
.spinner-ring:nth-child(2) {
  animation-delay: 0.1s;
  border-top-color: #67C23A;
}
.spinner-ring:nth-child(3) {
  animation-delay: 0.2s;
  border-top-color: #E6A23C;
}
.spinner-ring:nth-child(4) {
  animation-delay: 0.3s;
  border-top-color: #F56C6C;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 20px;
  font-size: 14px;
  color: #606266;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
