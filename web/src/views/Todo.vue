<template>
  <div class="todo-page">
    <h2 class="page-title">待办事项</h2>

    <div v-loading="loading">
      <!-- 板块1: 商品属性待维护列表 -->
      <el-card class="section-card" shadow="hover">
        <template #header>
          <span class="section-title">商品属性待维护列表</span>
        </template>

        <el-alert
          v-if="items.missing_products.length === 0"
          title="所有商品属性均已维护"
          type="success"
          show-icon
          :closable="false"
        />

        <el-table
          v-else
          :data="items.missing_products"
          stripe
          border
          style="width: 100%"
        >
          <el-table-column prop="material_code" label="物料编码" width="180" />
          <el-table-column prop="material_name" label="物料名称" />
        </el-table>
      </el-card>

      <!-- 板块2: 客户信息待维护列表 -->
      <el-card class="section-card" shadow="hover">
        <template #header>
          <span class="section-title">客户信息待维护列表</span>
        </template>

        <!-- 警示一：客户档案不存在 -->
        <div class="sub-section">
          <h4 class="sub-title">警示一：客户档案不存在</h4>

          <el-alert
            v-if="items.missing_customers.length === 0"
            title="所有客户档案均已维护"
            type="success"
            show-icon
            :closable="false"
          />

          <el-table
            v-else
            :data="items.missing_customers"
            stripe
            border
            style="width: 100%"
          >
            <el-table-column prop="customer" label="客户名称" />
            <el-table-column prop="region" label="区域" width="160" />
          </el-table>
        </div>

        <!-- 警示二：客户经理为空 -->
        <div class="sub-section">
          <h4 class="sub-title">警示二：客户已建档但客户经理为空</h4>

          <el-alert
            v-if="items.no_manager_customers.length === 0"
            title="所有已建档客户均已有客户经理"
            type="success"
            show-icon
            :closable="false"
          />

          <el-table
            v-else
            :data="items.no_manager_customers"
            stripe
            border
            style="width: 100%"
          >
            <el-table-column prop="customer" label="客户名称" />
            <el-table-column prop="region" label="区域" width="120" />
            <el-table-column prop="annual_sales" label="年销售额" width="150">
              <template #default="{ row }">
                {{ (row.annual_sales || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
              </template>
            </el-table-column>
            <el-table-column prop="cooperation_status" label="合作状态" width="120" />
          </el-table>
        </div>
      </el-card>

      <!-- 板块3: 数据对齐提醒 -->
      <el-card class="section-card" shadow="hover">
        <template #header>
          <span class="section-title">数据对齐提醒</span>
        </template>

        <el-alert
          v-if="items.data_alignment.diff === 0"
          title="销售出库暂存表与销售出库宽表数据行数一致"
          type="success"
          show-icon
          :closable="false"
        />

        <el-alert
          v-else
          :title="`数据行数不一致，差异 ${items.data_alignment.diff} 行（暂存表: ${items.data_alignment.stg_count}，宽表: ${items.data_alignment.wide_count}）`"
          type="warning"
          show-icon
          :closable="false"
        />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getTodoItems } from '@/api/todo'

const loading = ref(false)

const items = reactive({
  missing_products: [],
  missing_customers: [],
  no_manager_customers: [],
  data_alignment: { stg_count: 0, wide_count: 0, diff: 0 }
})

async function loadTodoItems() {
  loading.value = true
  try {
    const response = await getTodoItems()
    const data = response.data?.data || response.data || {}
    items.missing_products = data.missing_products || []
    items.missing_customers = data.missing_customers || []
    items.no_manager_customers = data.no_manager_customers || []
    items.data_alignment = data.data_alignment || { stg_count: 0, wide_count: 0, diff: 0 }
  } catch (error) {
    console.error('加载待办数据失败:', error)
    ElMessage.error('加载待办数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadTodoItems()
})
</script>

<style scoped>
.todo-page {
  padding: 0;
  max-width: 1400px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  margin: 0 0 24px 0;
  letter-spacing: -0.5px;
}

.section-card {
  margin-bottom: 20px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: all 0.25s ease;
}

.section-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

:deep(.el-card__header) {
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
  padding: 16px 20px;
}

:deep(.el-card__body) {
  padding: 20px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.sub-section {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #ebeef5;
}

.sub-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.sub-title {
  font-size: 13px;
  font-weight: 600;
  color: #00d9c0;
  margin: 0 0 16px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
</style>
