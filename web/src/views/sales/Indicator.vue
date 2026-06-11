<template>
  <div class="indicator">
    <div class="section-header">
      <span class="section-title">指标达成情况</span>
      <div class="header-filters">
        <el-select
          v-model="filterStore.indicator.region"
          placeholder="大区"
          clearable
          filterable
          size="small"
          style="width: 140px; margin-right: 8px"
          @change="loadIndicatorData"
        >
          <el-option
            v-for="item in options.regions"
            :key="item.value || item"
            :label="item.label || item"
            :value="item.value || item"
          />
        </el-select>
        <el-date-picker
          v-model="indicatorMonth"
          type="month"
          placeholder="选择月份"
          value-format="YYYY-MM"
          format="YYYY-MM"
          size="small"
          @change="loadIndicatorData"
        />
      </div>
    </div>

    <el-table :data="indicatorData" size="small" stripe border>
      <el-table-column prop="regionName" label="区域" width="120" fixed />
      <el-table-column prop="managerName" label="客户经理" width="120" />
      <el-table-column prop="targetAmount" label="出货任务(万元)" width="120" align="right">
        <template #default="{ row }">
          {{ row.targetAmount?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="actualAmount" label="出货金额(万元)" width="120" align="right">
        <template #default="{ row }">
          {{ row.actualAmount?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="achievementRate" label="完成率" width="100" align="center">
        <template #default="{ row }">
          <el-progress
            :percentage="Math.min(row.achievementRate || 0, 100)"
            :color="getProgressColor(row.achievementRate)"
            :stroke-width="8"
          />
        </template>
      </el-table-column>
      <el-table-column prop="mom" label="环比" width="90" align="center">
        <template #default="{ row }">
          <span :style="{ color: row.mom >= 0 ? '#f56c6c' : '#67c23a' }">
            {{ row.mom > 0 ? '↑' : row.mom < 0 ? '↓' : '-' }}{{ Math.abs(row.mom || 0).toFixed(2) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="yoy" label="同比" width="90" align="center">
        <template #default="{ row }">
          <span :style="{ color: row.yoy >= 0 ? '#f56c6c' : '#67c23a' }">
            {{ row.yoy > 0 ? '↑' : row.yoy < 0 ? '↓' : '-' }}{{ Math.abs(row.yoy || 0).toFixed(2) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column label="W1任务" width="90" align="right">
        <template #default="{ row }">
          {{ row.w1Target?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="W1金额" width="90" align="right">
        <template #default="{ row }">
          {{ row.w1Amount?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="W1完成率" width="100" align="center">
        <template #default="{ row }">
          <el-progress
            :percentage="Math.min(row.w1Rate || 0, 100)"
            :color="getProgressColor(row.w1Rate)"
            :stroke-width="6"
          />
        </template>
      </el-table-column>
      <el-table-column label="W2任务" width="90" align="right">
        <template #default="{ row }">
          {{ row.w2Target?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="W2金额" width="90" align="right">
        <template #default="{ row }">
          {{ row.w2Amount?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="W2完成率" width="100" align="center">
        <template #default="{ row }">
          <el-progress
            :percentage="Math.min(row.w2Rate || 0, 100)"
            :color="getProgressColor(row.w2Rate)"
            :stroke-width="6"
          />
        </template>
      </el-table-column>
      <el-table-column label="W3任务" width="90" align="right">
        <template #default="{ row }">
          {{ row.w3Target?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="W3金额" width="90" align="right">
        <template #default="{ row }">
          {{ row.w3Amount?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="W3完成率" width="100" align="center">
        <template #default="{ row }">
          <el-progress
            :percentage="Math.min(row.w3Rate || 0, 100)"
            :color="getProgressColor(row.w3Rate)"
            :stroke-width="6"
          />
        </template>
      </el-table-column>
      <el-table-column label="W4任务" width="90" align="right">
        <template #default="{ row }">
          {{ row.w4Target?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="W4金额" width="90" align="right">
        <template #default="{ row }">
          {{ row.w4Amount?.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="W4完成率" width="100" align="center">
        <template #default="{ row }">
          <el-progress
            :percentage="Math.min(row.w4Rate || 0, 100)"
            :color="getProgressColor(row.w4Rate)"
            :stroke-width="6"
          />
        </template>
      </el-table-column>
    </el-table>

    <div v-if="indicatorSummary" class="indicator-summary">
      <span>汇总: 出货任务 {{ indicatorSummary.targetAmount?.toFixed(2) }} 万元 | 出货金额 {{ indicatorSummary.actualAmount?.toFixed(2) }} 万元 | 完成率 {{ indicatorSummary.achievementRate?.toFixed(2) }}%</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useFilterStore } from '@/stores/filter'
import { getSalesIndicator } from '@/api/sales'

const filterStore = useFilterStore()
const setLoading = inject('setLoading', () => {})

const options = computed(() => filterStore.options)

const loading = ref(false)
const indicatorMonth = ref(new Date().toISOString().slice(0, 7))
const indicatorData = ref([])
const indicatorSummary = ref(null)

function getProgressColor(rate) {
  if (rate >= 100) return '#67c23a'
  if (rate >= 80) return '#e6a23c'
  return '#f56c6c'
}

async function loadIndicatorData() {
  loading.value = true
  setLoading(true)
  try {
    const month = indicatorMonth.value?.replace('-', '/')
    const params = {
      region: filterStore.indicator.region,
      manager: filterStore.indicator.manager,
      month: month
    }
    const response = await getSalesIndicator(params)
    const data = response.data?.data || response.data || []

    indicatorData.value = data.map(row => ({
      regionName: row.region,
      managerName: row.manager,
      targetAmount: row.task,
      actualAmount: row.current_month,
      achievementRate: row.completion_rate,
      mom: row.mom,
      yoy: row.yoy,
      w1Target: row.week_task?.[0] || 0,
      w1Amount: row.w1,
      w1Rate: row.w1_rate,
      w2Target: row.week_task?.[1] || 0,
      w2Amount: row.w2,
      w2Rate: row.w2_rate,
      w3Target: row.week_task?.[2] || 0,
      w3Amount: row.w3,
      w3Rate: row.w3_rate,
      w4Target: row.week_task?.[3] || 0,
      w4Amount: row.w4,
      w4Rate: row.w4_rate,
    }))

    if (data.length > 0) {
      const totalTarget = data.reduce((sum, row) => sum + (row.task || 0), 0)
      const totalActual = data.reduce((sum, row) => sum + (row.current_month || 0), 0)
      indicatorSummary.value = {
        targetAmount: totalTarget,
        actualAmount: totalActual,
        achievementRate: totalTarget > 0 ? (totalActual / totalTarget) * 100 : 0
      }
    } else {
      indicatorSummary.value = null
    }
  } catch (error) {
    console.error('加载指标达成数据失败:', error)
    indicatorData.value = []
    indicatorSummary.value = null
  } finally {
    loading.value = false
    setLoading(false)
  }
}

onMounted(async () => {
  await filterStore.fetchRegions()
  loadIndicatorData()
})
</script>

<style scoped>
.indicator {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-filters {
  display: flex;
  align-items: center;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

:deep(.el-table__header th) {
  font-weight: bold !important;
  text-align: center !important;
}

.indicator-summary {
  margin-top: 16px;
  padding: 12px 16px;
  background-color: #e0f7e0;
  border-radius: 4px;
  font-weight: bold;
  color: #303133;
}

.el-progress {
  width: 100%;
}
</style>
