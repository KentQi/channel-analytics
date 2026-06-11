<template>
  <div class="filter-bar">
    <el-form
      :model="localFilter"
      :inline="true"
      :size="size"
      class="filter-form"
    >
      <!-- 大区选择 -->
      <el-form-item v-if="showFields.region" label="大区">
        <el-select
          v-model="localFilter.region"
          placeholder="请选择大区"
          clearable
          filterable
          :loading="loading.regions"
          @change="handleRegionChange"
        >
          <el-option
            v-for="item in options.regions"
            :key="item.value || item.id"
            :label="item.label || item.name"
            :value="item.value || item.id"
          />
        </el-select>
      </el-form-item>

      <!-- 业务经理选择 -->
      <el-form-item v-if="showFields.manager" label="业务经理">
        <el-select
          v-model="localFilter.manager"
          placeholder="请选择业务经理"
          clearable
          filterable
          :loading="loading.managers"
          @change="handleManagerChange"
        >
          <el-option
            v-for="item in options.managers"
            :key="item.value || item.id"
            :label="item.label || item.name"
            :value="item.value || item.id"
          />
        </el-select>
      </el-form-item>

      <!-- 客户选择 -->
      <el-form-item v-if="showFields.customer" label="客户">
        <el-select
          v-model="localFilter.customer"
          placeholder="请选择客户"
          clearable
          filterable
          :loading="loading.customers"
          @change="handleFieldChange('customer')"
        >
          <el-option
            v-for="item in options.customers"
            :key="item.value || item.id"
            :label="item.label || item.name"
            :value="item.value || item.id"
          />
        </el-select>
      </el-form-item>

      <!-- 渠道选择 -->
      <el-form-item v-if="showFields.channel" label="渠道">
        <el-select
          v-model="localFilter.channel"
          placeholder="请选择渠道"
          clearable
          filterable
          :loading="loading.channels"
          @change="handleFieldChange('channel')"
        >
          <el-option
            v-for="item in options.channels"
            :key="item.value || item.id"
            :label="item.label || item.name"
            :value="item.value || item.id"
          />
        </el-select>
      </el-form-item>

      <!-- 月份选择 -->
      <el-form-item v-if="showFields.month" label="月份">
        <el-date-picker
          v-model="localFilter.month"
          type="month"
          placeholder="请选择月份"
          value-format="YYYY-MM"
          format="YYYY-MM"
          clearable
          @change="handleFieldChange('month')"
        />
      </el-form-item>

      <!-- 日期范围选择 -->
      <el-form-item v-if="showFields.dateRange" label="日期范围">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          format="YYYY-MM-DD"
          clearable
          :disabled="loading.dateRange"
          @change="handleDateRangeChange"
        />
      </el-form-item>

      <!-- 物料编码 -->
      <el-form-item v-if="showFields.materialCode" label="物料编码">
        <el-input
          v-model="localFilter.materialCode"
          placeholder="请输入物料编码"
          clearable
          @change="handleFieldChange('materialCode')"
        />
      </el-form-item>

      <!-- 批次号 -->
      <el-form-item v-if="showFields.batchNo" label="批次号">
        <el-input
          v-model="localFilter.batchNo"
          placeholder="请输入批次号"
          clearable
          @change="handleFieldChange('batchNo')"
        />
      </el-form-item>

      <!-- 单据日期范围 - 对齐源程序 -->
      <el-form-item v-if="showFields.docDateRange" label="单据日期">
        <el-date-picker
          v-model="docDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          format="YYYY-MM-DD"
          clearable
          @change="handleDocDateRangeChange"
        />
      </el-form-item>

      <!-- 审核日期范围 - 对齐源程序 -->
      <el-form-item v-if="showFields.auditDateRange" label="审核日期">
        <el-date-picker
          v-model="auditDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          format="YYYY-MM-DD"
          clearable
          @change="handleAuditDateRangeChange"
        />
      </el-form-item>

      <!-- 商品品类 - 对齐源程序 -->
      <el-form-item v-if="showFields.category" label="商品品类">
        <el-select
          v-model="localFilter.category"
          placeholder="请选择商品品类"
          clearable
          filterable
          @change="handleFieldChange('category')"
        >
          <el-option
            v-for="item in options.categories"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>

      <!-- ABC分类 - 对齐源程序 -->
      <el-form-item v-if="showFields.abcClass" label="ABC分类">
        <el-select
          v-model="localFilter.abcClass"
          placeholder="请选择ABC分类"
          clearable
          filterable
          @change="handleFieldChange('abcClass')"
        >
          <el-option
            v-for="item in options.abcClasses"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>

      <!-- 生命周期 - 对齐源程序 -->
      <el-form-item v-if="showFields.lifecycleStatus" label="生命周期">
        <el-select
          v-model="localFilter.lifecycleStatus"
          placeholder="请选择生命周期"
          clearable
          filterable
          @change="handleFieldChange('lifecycleStatus')"
        >
          <el-option
            v-for="item in options.lifecycleStatuses"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>

      <!-- 定制标记 - 对齐源程序 -->
      <el-form-item v-if="showFields.customFlag" label="定制标记">
        <el-select
          v-model="localFilter.customFlag"
          placeholder="请选择定制标记"
          clearable
          filterable
          @change="handleFieldChange('customFlag')"
        >
          <el-option
            v-for="item in options.customFlags"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>

      <!-- 主推标记 - 对齐源程序 -->
      <el-form-item v-if="showFields.promotedFlag" label="主推标记">
        <el-select
          v-model="localFilter.promotedFlag"
          placeholder="请选择主推标记"
          clearable
          filterable
          @change="handleFieldChange('promotedFlag')"
        >
          <el-option
            v-for="item in options.promotedFlags"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>

      <!-- 物料编码(下拉) - 对齐源程序 -->
      <el-form-item v-if="showFields.materialCodeSelect" label="物料编码">
        <el-select
          v-model="localFilter.materialCode"
          placeholder="请选择物料编码"
          clearable
          filterable
          @change="handleFieldChange('materialCode')"
        >
          <el-option
            v-for="item in options.materialCodes"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>

      <!-- 起始期间 - 对齐源程序Tab1 -->
      <el-form-item v-if="showFields.startMonth" label="起始期间">
        <el-select
          v-model="localFilter.startMonth"
          placeholder="请选择起始期间"
          clearable
          filterable
          @change="handleFieldChange('startMonth')"
        >
          <el-option
            v-for="item in options.startMonths"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>

      <!-- 交易类型 - 对齐源程序货流分析 -->
      <el-form-item v-if="showFields.txType" label="交易类型">
        <el-select
          v-model="localFilter.txType"
          placeholder="请选择交易类型"
          clearable
          filterable
          @change="handleFieldChange('txType')"
        >
          <el-option
            v-for="item in options.txTypes"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>

      <!-- 搜索按钮 -->
      <el-form-item v-if="showSearchButton">
        <el-button type="primary" :icon="Search" @click="handleSearch">
          查询
        </el-button>
      </el-form-item>

      <!-- 重置按钮 -->
      <el-form-item v-if="showResetButton">
        <el-button :icon="Refresh" @click="handleReset">
          重置
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { useFilterStore } from '@/stores/filter'

const props = defineProps({
  // 筛选器类型: sales, dashboard, indicator, salesDetail, productFlow
  filterType: {
    type: String,
    default: 'sales'
  },
  // 是否显示各字段 - 对齐源程序
  showFields: {
    type: Object,
    default: () => ({
      region: true,
      manager: true,
      customer: true,
      channel: true,
      dateRange: true,
      month: false,
      materialCode: false,
      batchNo: false,
      // 源程序对齐的字段
      docDateRange: false,      // 单据日期范围
      auditDateRange: false,     // 审核日期范围
      category: false,           // 商品品类
      abcClass: false,           // ABC分类
      lifecycleStatus: false,    // 生命周期
      customFlag: false,          // 定制标记
      promotedFlag: false,       // 主推标记
      materialCodeSelect: false,  // 物料编码(下拉选择)
      startMonth: false,         // 起始期间
      txType: false             // 交易类型
    })
  },
  // 组件大小
  size: {
    type: String,
    default: 'default'
  },
  // 是否显示搜索按钮
  showSearchButton: {
    type: Boolean,
    default: true
  },
  // 是否显示重置按钮
  showResetButton: {
    type: Boolean,
    default: true
  },
  // 外部传入的筛选器状态（可选）
  modelValue: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'search', 'reset', 'change'])

// 获取 filter store
const filterStore = useFilterStore()

// 本地筛选器状态
const localFilter = reactive({})

// 日期范围（特殊处理）
const dateRange = ref([])
const docDateRange = ref([])   // 单据日期范围
const auditDateRange = ref([]) // 审核日期范围

// 计算属性：选项列表
const options = computed(() => filterStore.options)

// 计算属性：加载状态
const loading = computed(() => filterStore.loadingOptions)

// 初始化本地筛选器状态
function initLocalFilter() {
  // 如果有外部传入的 modelValue，使用它
  if (props.modelValue) {
    Object.assign(localFilter, props.modelValue)
    // 处理日期范围
    if (localFilter.dateFrom && localFilter.dateTo) {
      dateRange.value = [localFilter.dateFrom, localFilter.dateTo]
    }
  } else {
    // 使用 store 中的筛选器状态
    const storeFilter = filterStore[props.filterType]
    if (storeFilter) {
      Object.assign(localFilter, storeFilter)
      // 处理日期范围
      if (localFilter.dateFrom && localFilter.dateTo) {
        dateRange.value = [localFilter.dateFrom, localFilter.dateTo]
      }
    }
  }
}

// 加载选项数据
async function loadOptions() {
  const tasks = []

  if (props.showFields.region) {
    tasks.push(filterStore.fetchRegions())
  }
  if (props.showFields.manager) {
    tasks.push(filterStore.fetchManagers())
  }
  if (props.showFields.customer) {
    tasks.push(filterStore.fetchCustomers())
  }
  if (props.showFields.channel) {
    tasks.push(filterStore.fetchChannels())
  }
  if (props.showFields.month) {
    tasks.push(filterStore.fetchMonths())
  }
  // 商品属性选项（对齐源程序）
  if (props.showFields.category) {
    tasks.push(filterStore.fetchCategories())
  }
  if (props.showFields.abcClass) {
    tasks.push(filterStore.fetchAbcClasses())
  }
  if (props.showFields.lifecycleStatus) {
    tasks.push(filterStore.fetchLifecycleStatuses())
  }
  if (props.showFields.customFlag) {
    tasks.push(filterStore.fetchCustomFlags())
  }
  if (props.showFields.promotedFlag) {
    tasks.push(filterStore.fetchPromotedFlags())
  }
  if (props.showFields.materialCodeSelect) {
    tasks.push(filterStore.fetchMaterialCodes())
  }

  await Promise.all(tasks)
}

// 大区变更处理
async function handleRegionChange(value) {
  // 重置下游字段
  filterStore.resetDownstream('region', value)
  // 如果有经理筛选，重新加载经理列表
  if (props.showFields.manager) {
    await filterStore.fetchManagers(value)
  }
  // 如果有客户筛选，重新加载客户列表
  if (props.showFields.customer) {
    await filterStore.fetchCustomers(null)
  }
  handleFieldChange('region')
}

// 经理变更处理
async function handleManagerChange(value) {
  // 重置下游字段
  filterStore.resetDownstream('manager', value)
  // 如果有客户筛选，重新加载客户列表
  if (props.showFields.customer) {
    await filterStore.fetchCustomers(value)
  }
  handleFieldChange('manager')
}

// 日期范围变更处理
function handleDateRangeChange(value) {
  if (value && value.length === 2) {
    localFilter.dateFrom = value[0]
    localFilter.dateTo = value[1]
  } else {
    localFilter.dateFrom = null
    localFilter.dateTo = null
  }
  filterStore.resetDownstream('dateFrom', localFilter.dateFrom)
  filterStore.resetDownstream('dateTo', localFilter.dateTo)
  handleFieldChange('dateFrom')
  emit('change', localFilter)
}

// 单据日期范围变更处理 - 对齐源程序
function handleDocDateRangeChange(value) {
  if (value && value.length === 2) {
    localFilter.docDateFrom = value[0]
    localFilter.docDateTo = value[1]
  } else {
    localFilter.docDateFrom = null
    localFilter.docDateTo = null
  }
  handleFieldChange('docDateFrom')
  emit('change', localFilter)
}

// 审核日期范围变更处理 - 对齐源程序
function handleAuditDateRangeChange(value) {
  if (value && value.length === 2) {
    localFilter.auditDateFrom = value[0]
    localFilter.auditDateTo = value[1]
  } else {
    localFilter.auditDateFrom = null
    localFilter.auditDateTo = null
  }
  handleFieldChange('auditDateFrom')
  emit('change', localFilter)
}

// 字段变更处理
function handleFieldChange(field) {
  // 同步到 store
  if (filterStore[props.filterType]) {
    Object.assign(filterStore[props.filterType], localFilter)
  }
  filterStore.resetDownstream(field, localFilter[field])
  emit('change', localFilter)
}

// 搜索处理
function handleSearch() {
  // 同步到 store
  if (filterStore[props.filterType]) {
    Object.assign(filterStore[props.filterType], localFilter)
  }
  emit('search', localFilter)
}

// 重置处理
function handleReset() {
  // 重置 store 中的筛选器
  const resetMethod = `reset${props.filterType.charAt(0).toUpperCase() + props.filterType.slice(1)}`
  if (filterStore[resetMethod]) {
    filterStore[resetMethod]()
  }

  // 重置本地状态
  Object.keys(localFilter).forEach(key => {
    if (key === 'dateFrom' || key === 'dateTo') {
      localFilter[key] = filterStore[props.filterType]?.[key] || null
    } else if (key === 'docDateFrom' || key === 'docDateTo') {
      localFilter[key] = filterStore[props.filterType]?.[key] || null
    } else if (key === 'auditDateFrom' || key === 'auditDateTo') {
      localFilter[key] = filterStore[props.filterType]?.[key] || null
    } else {
      localFilter[key] = filterStore[props.filterType]?.[key] || null
    }
  })

  // 重置日期范围
  dateRange.value = []
  docDateRange.value = []
  auditDateRange.value = []

  // 如果有 dateFrom/dateTo
  if (filterStore[props.filterType]?.dateFrom && filterStore[props.filterType]?.dateTo) {
    dateRange.value = [filterStore[props.filterType].dateFrom, filterStore[props.filterType].dateTo]
  }
  // 如果有 docDateFrom/docDateTo
  if (filterStore[props.filterType]?.docDateFrom && filterStore[props.filterType]?.docDateTo) {
    docDateRange.value = [filterStore[props.filterType].docDateFrom, filterStore[props.filterType].docDateTo]
  }
  // 如果有 auditDateFrom/auditDateTo
  if (filterStore[props.filterType]?.auditDateFrom && filterStore[props.filterType]?.auditDateTo) {
    auditDateRange.value = [filterStore[props.filterType].auditDateFrom, filterStore[props.filterType].auditDateTo]
  }

  emit('reset', localFilter)
  emit('change', localFilter)
}

// 监听外部 modelValue 变化
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      Object.assign(localFilter, newVal)
    }
  },
  { deep: true }
)

// 监听 store 中筛选器变化
watch(
  () => filterStore[props.filterType],
  (newVal) => {
    if (newVal && props.modelValue) {
      // 如果没有外部传入的 modelValue，同步 store 变化
      Object.assign(localFilter, newVal)
      if (newVal.dateFrom && newVal.dateTo) {
        dateRange.value = [newVal.dateFrom, newVal.dateTo]
      }
    }
  },
  { deep: true }
)

// 初始化
onMounted(async () => {
  initLocalFilter()
  await loadOptions()
})

// 暴露方法
defineExpose({
  getFilter: () => ({ ...localFilter }),
  setFilter: (filter) => Object.assign(localFilter, filter),
  reset: handleReset,
  search: handleSearch
})
</script>

<style scoped>
.filter-bar {
  background: #fff;
  padding: 16px 20px;
  border-radius: 10px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.filter-form :deep(.el-form-item__label) {
  color: #606266;
  font-weight: 500;
}

.filter-form :deep(.el-select),
.filter-form :deep(.el-date-editor) {
  width: 180px;
}

.filter-form :deep(.el-input) {
  width: 180px;
}

.filter-form :deep(.el-button--primary) {
  background: linear-gradient(135deg, #00d9c0 0%, #06b6d4 100%);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0, 217, 192, 0.3);
}

.filter-form :deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #00f5db 0%, #0891b2 100%);
  box-shadow: 0 6px 16px rgba(0, 217, 192, 0.4);
  transform: translateY(-1px);
}

.filter-form :deep(.el-button) {
  border-radius: 8px;
  font-weight: 500;
}
</style>
