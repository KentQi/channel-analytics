<template>
  <div class="new-product-warning">
    <!-- 筛选器 -->
    <div class="filter-bar">
      <div class="filter-item">
        <span class="filter-label">首批入库</span>
        <el-select v-model="days" style="width: 120px" @change="loadData">
          <el-option :value="60" label="60 天内" />
          <el-option :value="90" label="90 天内" />
          <el-option :value="180" label="180 天内" />
        </el-select>
      </div>
    </div>

    <!-- 新品预警表 -->
    <div class="section-card">
      <div class="section-title">新品预警表</div>
      <el-table :data="newProductWarning" stripe border size="small" max-height="450">
        <el-table-column prop="lifecycle_status" label="生命周期" width="80" align="center" />
        <el-table-column prop="abc_class" label="ABC" width="60" align="center" />
        <el-table-column prop="material_code" label="物料编码" width="110" show-overflow-tooltip />
        <el-table-column prop="material_name" label="物料名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="first_stock_in_date" label="首批入库" width="110" align="center" />
        <el-table-column prop="first_sale_date" label="首销" width="110" align="center" />
        <el-table-column prop="current_stock" label="在库量" width="80" align="right" />
        <el-table-column prop="0-7" label="0-7天销量" width="90" align="center" />
        <el-table-column prop="7-15" label="7-15天销量" width="95" align="center" />
        <el-table-column prop="15-30" label="15-30天销量" width="100" align="center" />
        <el-table-column prop="30-45" label="30-45天销量" width="100" align="center" />
        <el-table-column prop="45-60" label="45-60天销量" width="100" align="center" />
        <el-table-column prop="60-90" label="60-90天销量" width="100" align="center" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import { getNewProductWarning } from '@/api/repurchase'

const setLoading = inject('setLoading', () => {})

const days = ref(90)

const newProductWarning = ref([])

async function loadData() {
  try {
    setLoading(true)
    const res = await getNewProductWarning({ days: days.value })
    const data = res.data?.data || res.data || {}
    newProductWarning.value = data.new_products || []
  } catch (e) {
    console.error('加载新品预警表失败:', e)
    newProductWarning.value = []
  } finally {
    setLoading(false)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.new-product-warning {
  padding: 0;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background-color: #f5f7fa;
  border-radius: 6px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.section-card {
  background-color: #fff;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

:deep(.el-table__header th) {
  font-weight: bold;
  text-align: center;
}
</style>
