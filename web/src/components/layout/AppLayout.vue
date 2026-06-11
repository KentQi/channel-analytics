<template>
  <div class="app-layout">
    <!-- Mobile sidebar (drawer) -->
    <mobile-sidebar
      :visible="showMobileSidebar"
      @close="showMobileSidebar = false"
    />

    <!-- Desktop sidebar -->
    <app-sidebar
      v-if="!isMobile"
      class="app-sidebar"
      :class="{ 'is-collapse': isTablet && sidebarCollapsed }"
    />

    <div class="app-main">
      <app-header
        class="app-header"
        @toggle-sidebar="handleToggleSidebar"
      />
      <div class="app-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import MobileSidebar from './MobileSidebar.vue'
import { useResponsive } from '@/composables/useResponsive'

const route = useRoute()
const { isMobile, isTablet } = useResponsive()

const showMobileSidebar = ref(false)
const sidebarCollapsed = ref(false)

function handleToggleSidebar() {
  if (isMobile.value) {
    showMobileSidebar.value = true
  } else if (isTablet.value) {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
}

// Close mobile sidebar on route change
watch(() => route.path, () => {
  if (isMobile.value) {
    showMobileSidebar.value = false
  }
})
</script>

<style scoped>
.app-layout {
  display: flex;
  width: 100%;
  height: 100%;
}

.app-sidebar {
  width: 200px;
  flex-shrink: 0;
  height: 100%;
  transition: width 0.3s ease;
}

.app-sidebar.is-collapse {
  width: 64px;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0; /* Prevent flex overflow */
}

.app-header {
  height: 56px;
  flex-shrink: 0;
}

.app-content {
  flex: 1;
  overflow: auto;
  padding: 20px;
  background-color: #f5f7fa;
}

/* Mobile responsive */
@media (max-width: 767px) {
  .app-sidebar {
    display: none;
  }

  .app-content {
    padding: 12px;
  }
}

/* Tablet responsive */
@media (min-width: 768px) and (max-width: 1023px) {
  .app-sidebar.is-collapse {
    width: 64px;
  }
}
</style>
