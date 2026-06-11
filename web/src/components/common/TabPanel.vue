<template>
  <div class="tab-panel">
    <el-tabs
      v-model="activeTab"
      :type="type"
      :tab-position="tabPosition"
      :stretch="stretch"
      :before-leave="handleBeforeLeave"
      @tab-change="handleTabChange"
      @tab-click="handleTabClick"
    >
      <el-tab-pane
        v-for="tab in tabs"
        :key="tab.name"
        :label="tab.label"
        :name="tab.name"
        :closable="tab.closable"
        :disabled="tab.disabled"
        :lazy="tab.lazy"
      >
        <template v-if="tab.slot" #label>
          <slot :name="`tab-label-${tab.name}`" :tab="tab">
            <span>{{ tab.label }}</span>
            <el-badge
              v-if="tab.badge"
              :value="tab.badge"
              :type="tab.badgeType"
              :max="tab.badgeMax"
              class="tab-badge"
            />
          </slot>
        </template>

        <slot :name="tab.name" :tab="tab">
          <component
            :is="tab.component"
            v-if="tab.component && (activeTab === tab.name || !tab.lazy)"
            v-bind="tab.props"
            v-on="tab.listeners || {}"
          />
          <div v-else-if="tab.content" class="tab-content">
            {{ tab.content }}
          </div>
        </slot>
      </el-tab-pane>

      <!-- 额外插槽 -->
      <template v-if="$slots.right" #right>
        <slot name="right" />
      </template>
    </el-tabs>

    <!-- 额外底部插槽 -->
    <slot name="footer" />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  // Tab 配置数组
  tabs: {
    type: Array,
    default: () => []
  },
  // 当前激活的 Tab
  modelValue: {
    type: [String, Number],
    default: null
  },
  // Tab 类型：'card' | 'border-card' | '' | 'border-card'
  type: {
    type: String,
    default: ''
  },
  // Tab 位置：'top' | 'right' | 'bottom' | 'left'
  tabPosition: {
    type: String,
    default: 'top'
  },
  // Tab 宽度是否自适用
  stretch: {
    type: Boolean,
    default: false
  },
  // 切换前回调，返回 false 或 Promise 可阻止切换
  beforeLeave: {
    type: Function,
    default: null
  },
  // 是否显示额外操作区域
  showExtra: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'update:modelValue',
  'tab-change',
  'tab-click',
  'change'
])

const activeTab = ref(props.modelValue || (props.tabs[0]?.name))

// 监听外部 modelValue 变化
watch(
  () => props.modelValue,
  (val) => {
    if (val !== activeTab.value) {
      activeTab.value = val
    }
  }
)

// 监听 tabs 变化
watch(
  () => props.tabs,
  (newTabs) => {
    // 如果当前激活的 tab 不存在，切换到第一个
    if (newTabs.length > 0 && !newTabs.find(t => t.name === activeTab.value)) {
      activeTab.value = newTabs[0].name
    }
  },
  { immediate: true }
)

// Tab 切换前回调
async function handleBeforeLeave(newTab, oldTab) {
  if (props.beforeLeave) {
    try {
      const result = await Promise.resolve(props.beforeLeave(newTab, oldTab))
      return result !== false
    } catch {
      return false
    }
  }
  return true
}

// Tab 切换回调
function handleTabChange(tabName) {
  emit('update:modelValue', tabName)
  emit('tab-change', tabName)
  emit('change', tabName)
}

// Tab 点击回调
function handleTabClick(tab) {
  emit('tab-click', tab)
}

// 获取当前激活的 Tab
function getActiveTab() {
  return props.tabs.find(t => t.name === activeTab.value)
}

// 设置激活的 Tab
function setActiveTab(tabName) {
  activeTab.value = tabName
}

// 禁用某个 Tab
function disableTab(tabName, disabled = true) {
  const tab = props.tabs.find(t => t.name === tabName)
  if (tab) {
    tab.disabled = disabled
  }
}

// 显示/隐藏某个 Tab
function showTab(tabName, visible = true) {
  const tab = props.tabs.find(t => t.name === tabName)
  if (tab) {
    tab.hidden = !visible
  }
}

// 暴露方法
defineExpose({
  activeTab,
  getActiveTab,
  setActiveTab,
  disableTab,
  showTab
})
</script>

<style scoped>
.tab-panel {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
}

.tab-badge {
  margin-left: 4px;
}

.tab-content {
  padding: 20px;
  color: #606266;
}
</style>
