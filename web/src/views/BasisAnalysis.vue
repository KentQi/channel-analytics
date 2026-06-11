<template>
  <div class="basis-analysis">
    <h2>基础分析</h2>
    <el-tabs v-model="activeTab" type="border-card" @tab-change="handleTabChange">
      <el-tab-pane
        v-for="tab in tabList"
        :key="tab.name"
        :label="tab.label"
        :name="tab.name"
      >
        <div class="report-header">
          <span class="report-stats">
            共 <strong>{{ reportData[tab.name]?.total || 0 }}</strong> 行，
            <strong>{{ reportData[tab.name]?.columns?.length || 0 }}</strong> 列
          </span>
          <el-button
            type="primary"
            size="small"
            :icon="Refresh"
            :loading="loading[tab.name]"
            @click="loadReport(tab.name)"
          >
            刷新
          </el-button>
        </div>

        <el-table
          v-loading="loading[tab.name]"
          :data="reportData[tab.name]?.rows || []"
          border
          stripe
          max-height="600"
          size="small"
          style="width: 100%"
        >
          <el-table-column
            type="index"
            label="序号"
            width="60"
            align="center"
          />
          <el-table-column
            v-for="col in reportData[tab.name]?.columns || []"
            :key="col"
            :prop="col"
            :label="col"
            :min-width="120"
            show-overflow-tooltip
          />
          <template #empty>
            <el-empty description="暂无数据" />
          </template>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getReportTable } from '@/api/stock'

const tabList = [
  { name: 'rpt_expiry_warning', label: '效期预警聚合表' },
  { name: 'rpt_expiry_turnover', label: '效期-周转表' },
  { name: 'rpt_self_operated_concentration', label: '自营品库存集中度' },
  { name: 'rpt_turnover_warning', label: '周转预警聚合表' },
  { name: 'rpt_trend_warning', label: '趋势预警聚合表' },
  { name: 'rpt_warehouse_risk', label: '物料-仓库综合风险表' },
  { name: 'rpt_procurement_linked', label: '请购-采购-入库关联' },
]

const activeTab = ref(tabList[0].name)
const loading = reactive({})
const reportData = reactive({})

async function loadReport(tableName) {
  loading[tableName] = true
  try {
    const res = await getReportTable(tableName)
    const body = res.data
    if (body.success) {
      reportData[tableName] = body.data
    } else {
      ElMessage.error(`加载 ${tableName} 失败: ${body.error || '未知错误'}`)
      reportData[tableName] = { columns: [], rows: [], total: 0 }
    }
  } catch (e) {
    ElMessage.error(`请求 ${tableName} 异常: ${e.message}`)
    reportData[tableName] = { columns: [], rows: [], total: 0 }
  } finally {
    loading[tableName] = false
  }
}

function handleTabChange(name) {
  // 首次切换到某个 Tab 时自动加载数据
  if (!reportData[name]) {
    loadReport(name)
  }
}

onMounted(() => {
  // 默认加载第一个 Tab
  loadReport(activeTab.value)
})
</script>

<style scoped>
.basis-analysis {
  padding: 20px;
}

.basis-analysis h2 {
  margin-bottom: 16px;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.report-stats {
  font-size: 14px;
  color: #606266;
}
</style>
