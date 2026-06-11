<template>
  <div class="data-table-container">
    <!-- 表格 -->
    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="displayData"
      :stripe="stripe"
      :border="border"
      :size="size"
      :height="height"
      :max-height="maxHeight"
      :fit="fit"
      :show-header="showHeader"
      :highlight-current-row="highlightCurrentRow"
      :row-class-name="rowClassName"
      :cell-class-name="cellClassName"
      :span-method="spanMethod"
      :default-sort="defaultSort"
      :tooltip-effect="tooltipEffect"
      @select="handleSelect"
      @select-all="handleSelectAll"
      @selection-change="handleSelectionChange"
      @cell-click="handleCellClick"
      @row-click="handleRowClick"
      @sort-change="handleSortChange"
    >
      <!-- 选择列 -->
      <el-table-column
        v-if="showSelection"
        type="selection"
        width="55"
        :selectable="selectable"
      />

      <!-- 索引列 -->
      <el-table-column
        v-if="showIndex"
        type="index"
        label="序号"
        width="60"
        :index="indexMethod"
        :align="indexAlign || 'center'"
      />

      <!-- 动态列 -->
      <el-table-column
        v-for="column in columns"
        :key="column.prop"
        :prop="column.prop"
        :label="column.label"
        :width="column.width"
        :min-width="column.minWidth"
        :fixed="column.fixed"
        :align="column.align || 'left'"
        :header-align="column.headerAlign"
        :sortable="column.sortable"
        :sort-by="column.sortBy"
        :sort-orders="column.sortOrders"
        :formatter="column.formatter"
        :show-overflow-tooltip="column.showOverflowTooltip !== false"
        :resizable="column.resizable !== false"
      >
        <!-- 自定义表头 -->
        <template v-if="column.slot" #header="scope">
          <slot :name="`header-${column.prop}`" v-bind="scope" />
        </template>

        <!-- 自定义单元格 -->
        <template v-if="column.slot" #default="scope">
          <slot :name="column.prop" v-bind="scope" />
        </template>
      </el-table-column>

      <!-- 操作列 -->
      <el-table-column
        v-if="$slots.action || showDefaultActions"
        :label="actionLabel || '操作'"
        :width="actionWidth"
        :fixed="actionFixed || 'right'"
        :align="actionAlign || 'center'"
      >
        <template #default="scope">
          <slot name="action" v-bind="scope" />
          <template v-if="showDefaultActions">
            <el-button
              v-if="showViewButton"
              type="primary"
              link
              size="small"
              @click="handleView(scope.row, scope.$index)"
            >
              查看
            </el-button>
            <el-button
              v-if="showEditButton"
              type="primary"
              link
              size="small"
              @click="handleEdit(scope.row, scope.$index)"
            >
              编辑
            </el-button>
            <el-button
              v-if="showDeleteButton"
              type="danger"
              link
              size="small"
              @click="handleDelete(scope.row, scope.$index)"
            >
              删除
            </el-button>
          </template>
        </template>
      </el-table-column>

      <!-- 空状态 -->
      <template #empty>
        <slot name="empty">
          <el-empty :description="emptyText || '暂无数据'" />
        </slot>
      </template>
    </el-table>

    <!-- 分页 -->
    <div v-if="showPagination" class="data-table-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="pageSizes"
        :total="effectiveTotal"
        :layout="paginationLayout"
        :background="paginationBackground"
        :small="paginationSmall"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- CSV 导出按钮 -->
    <div v-if="showExportButton" class="data-table-export">
      <el-button
        type="success"
        :icon="Download"
        :loading="exporting"
        @click="handleExport"
      >
        导出 CSV
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'

const props = defineProps({
  // 表格数据
  data: {
    type: Array,
    default: () => []
  },
  // 列配置
  columns: {
    type: Array,
    default: () => []
  },
  // 加载状态
  loading: {
    type: Boolean,
    default: false
  },
  // 斑马纹
  stripe: {
    type: Boolean,
    default: false
  },
  // 边框
  border: {
    type: Boolean,
    default: true
  },
  // 表格尺寸
  size: {
    type: String,
    default: 'default'
  },
  // 固定高度
  height: {
    type: [String, Number],
    default: null
  },
  // 最大高度
  maxHeight: {
    type: [String, Number],
    default: null
  },
  // 自动适应宽度
  fit: {
    type: Boolean,
    default: true
  },
  // 显示表头
  showHeader: {
    type: Boolean,
    default: true
  },
  // 高亮当前行
  highlightCurrentRow: {
    type: Boolean,
    default: false
  },
  // 行类名
  rowClassName: {
    type: [Function, String],
    default: null
  },
  // 单元格类名
  cellClassName: {
    type: [Function, String],
    default: null
  },
  // 合并行或列
  spanMethod: {
    type: Function,
    default: null
  },
  // 默认排序
  defaultSort: {
    type: Object,
    default: null
  },
  // 提示效果
  tooltipEffect: {
    type: String,
    default: 'light'
  },
  // 显示选择列
  showSelection: {
    type: Boolean,
    default: false
  },
  // 选择列行选择器
  selectable: {
    type: Function,
    default: () => true
  },
  // 显示索引列
  showIndex: {
    type: Boolean,
    default: false
  },
  // 索引列对齐方式
  indexAlign: {
    type: String,
    default: 'center'
  },
  // 索引格式化方法
  indexMethod: {
    type: Function,
    default: (index) => index + 1
  },
  // 显示分页
  showPagination: {
    type: Boolean,
    default: true
  },
  // 当前页码
  modelValue: {
    type: Number,
    default: 1
  },
  // 每页条数
  pageSize: {
    type: Number,
    default: 20
  },
  // 每页条数选项
  pageSizes: {
    type: Array,
    default: () => [10, 20, 50, 100]
  },
  // 总数据条数
  total: {
    type: Number,
    default: 0
  },
  // 分页布局
  paginationLayout: {
    type: String,
    default: 'total, sizes, prev, pager, next, jumper'
  },
  // 分页按钮背景色
  paginationBackground: {
    type: Boolean,
    default: true
  },
  // 分页组件使用 small 样式
  paginationSmall: {
    type: Boolean,
    default: false
  },
  // 空状态文本
  emptyText: {
    type: String,
    default: '暂无数据'
  },
  // 显示导出按钮
  showExportButton: {
    type: Boolean,
    default: false
  },
  // 导出文件名
  exportFileName: {
    type: String,
    default: 'export'
  },
  // 显示默认操作按钮
  showDefaultActions: {
    type: Boolean,
    default: false
  },
  // 操作列标签
  actionLabel: {
    type: String,
    default: '操作'
  },
  // 操作列宽度
  actionWidth: {
    type: [String, Number],
    default: 150
  },
  // 操作列固定位置
  actionFixed: {
    type: String,
    default: 'right'
  },
  // 操作列对齐方式
  actionAlign: {
    type: String,
    default: 'center'
  },
  // 显示查看按钮
  showViewButton: {
    type: Boolean,
    default: true
  },
  // 显示编辑按钮
  showEditButton: {
    type: Boolean,
    default: true
  },
  // 显示删除按钮
  showDeleteButton: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'update:modelValue',
  'update:pageSize',
  'select',
  'select-all',
  'selection-change',
  'cell-click',
  'row-click',
  'sort-change',
  'view',
  'edit',
  'delete',
  'export'
])

const tableRef = ref(null)
const currentPage = ref(props.modelValue)
const pageSize = ref(props.pageSize)
const exporting = ref(false)

// 显示的数据（客户端分页）
const displayData = computed(() => {
  if (!props.showPagination) {
    return props.data
  }
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return props.data.slice(start, end)
})

// 实际 total：优先用 prop，否则用 data.length
const effectiveTotal = computed(() => {
  return props.total > 0 ? props.total : props.data.length
})

// 监听外部 modelValue 变化
watch(
  () => props.modelValue,
  (val) => {
    currentPage.value = val
  }
)

// 监听外部 pageSize 变化
watch(
  () => props.pageSize,
  (val) => {
    pageSize.value = val
  }
)

// 每页条数变化
function handleSizeChange(val) {
  pageSize.value = val
  emit('update:pageSize', val)
  // 切换每页条数时回到第一页
  currentPage.value = 1
  emit('update:modelValue', 1)
}

// 当前页变化
function handleCurrentChange(val) {
  currentPage.value = val
  emit('update:modelValue', val)
}

// 选择变化
function handleSelect(selection, row) {
  emit('select', selection, row)
}

// 全选变化
function handleSelectAll(selection) {
  emit('select-all', selection)
}

// 多选变化
function handleSelectionChange(selection) {
  emit('selection-change', selection)
}

// 单元格点击
function handleCellClick(row, column, cell, event) {
  emit('cell-click', row, column, cell, event)
}

// 行点击
function handleRowClick(row, column, event) {
  emit('row-click', row, column, event)
}

// 排序变化
function handleSortChange({ column, prop, order }) {
  emit('sort-change', { column, prop, order })
}

// 查看
function handleView(row, index) {
  emit('view', row, index)
}

// 编辑
function handleEdit(row, index) {
  emit('edit', row, index)
}

// 删除
function handleDelete(row, index) {
  emit('delete', row, index)
}

// 导出 CSV
async function handleExport() {
  exporting.value = true

  try {
    const exportData = props.data
    if (!exportData || exportData.length === 0) {
      ElMessage.warning('没有可导出的数据')
      return
    }

    // 生成 CSV 内容
    const csvContent = generateCSV(exportData, props.columns)

    // 下载文件
    downloadCSV(csvContent, props.exportFileName)

    ElMessage.success('导出成功')
    emit('export', exportData)
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// 生成 CSV 内容
function generateCSV(data, columns) {
  // 表头
  const headers = columns.map(col => escapeCSV(col.label || col.prop))
  const headerRow = headers.join(',')

  // 数据行
  const rows = data.map(row => {
    return columns.map(col => {
      let value = row[col.prop]

      // 使用格式化函数
      if (col.formatter && typeof col.formatter === 'function') {
        value = col.formatter(row, col, value, row[col.prop])
      }

      // 转字符串
      if (value === null || value === undefined) {
        value = ''
      } else {
        value = String(value)
      }

      return escapeCSV(value)
    }).join(',')
  })

  // 添加 BOM 以支持 Excel 打开 UTF-8 编码的 CSV
  const BOM = '﻿'

  return BOM + headerRow + '\n' + rows.join('\n')
}

// 转义 CSV 特殊字符
function escapeCSV(value) {
  const str = String(value)
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    return '"' + str.replace(/"/g, '""') + '"'
  }
  return str
}

// 下载 CSV 文件
function downloadCSV(content, fileName) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)

  link.setAttribute('href', url)
  link.setAttribute('download', `${fileName}_${formatDate(new Date())}.csv`)
  link.style.visibility = 'hidden'

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  URL.revokeObjectURL(url)
}

// 格式化日期
function formatDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')

  return `${year}${month}${day}${hours}${minutes}${seconds}`
}

// 暴露方法
defineExpose({
  table: tableRef,
  getTable: () => tableRef.value,
  clearSelection: () => tableRef.value?.clearSelection(),
  toggleRowSelection: (row, selected) => tableRef.value?.toggleRowSelection(row, selected),
  toggleAllSelection: () => tableRef.value?.toggleAllSelection(),
  toggleRowExpansion: (row, expanded) => tableRef.value?.toggleRowExpansion(row, expanded),
  setCurrentRow: (row) => tableRef.value?.setCurrentRow(row),
  clearSort: () => tableRef.value?.clearSort(),
  doLayout: () => tableRef.value?.doLayout()
})
</script>

<style scoped>
.data-table-container {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.data-table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.data-table-export {
  display: flex;
  justify-content: flex-start;
  margin-top: 12px;
}
</style>
