<template>
  <div class="sales-analysis">
    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="main-tabs">
      <!-- 销售宽表 -->
      <el-tab-pane label="销售宽表" name="table">
        <div class="tab-content">
          <!-- Tab0筛选器 - 对齐源程序 -->
          <div class="flow-filter">
            <el-form inline :model="filterStore.sales" class="filter-form-row">
              <!-- 默认显示的一行 -->
              <el-form-item label="单据日期">
                <el-date-picker v-model="filterStore.sales.docDateRange" type="daterange" range-separator="~" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 220px" />
              </el-form-item>
              <el-form-item label="审核日期">
                <el-date-picker v-model="filterStore.sales.auditDateRange" type="daterange" range-separator="~" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 220px" />
              </el-form-item>
              <el-form-item label="大区">
                <el-select v-model="filterStore.sales.region" placeholder="请选择大区" clearable filterable style="width: 120px" @change="handleSalesRegionChange">
                  <el-option v-for="item in options.regions" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="loadTableData">查询</el-button>
                <el-button @click="resetSalesFilters">重置</el-button>
                <el-button text @click="filterExpanded = !filterExpanded">
                  {{ filterExpanded ? '收起' : '更多' }}
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
              </el-form-item>
            </el-form>
            <!-- 折叠的其他筛选条件 -->
            <el-form v-show="filterExpanded" inline :model="filterStore.sales" class="more-filters">
              <el-form-item label="客户经理">
                <el-select v-model="filterStore.sales.manager" placeholder="请选择客户经理" clearable filterable style="width: 150px" @change="handleSalesManagerChange">
                  <el-option v-for="item in options.managers" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="客户">
                <el-select v-model="filterStore.sales.customer" placeholder="请选择客户" clearable filterable style="width: 180px">
                  <el-option v-for="item in options.customers" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="渠道">
                <el-select v-model="filterStore.sales.channel" placeholder="请选择渠道" clearable filterable style="width: 120px">
                  <el-option v-for="item in options.channels" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="商品品类">
                <el-select v-model="filterStore.sales.category" placeholder="请选择品类" clearable filterable style="width: 120px">
                  <el-option v-for="item in options.categories" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="ABC分类">
                <el-select v-model="filterStore.sales.abcClass" placeholder="请选择" clearable filterable style="width: 100px">
                  <el-option v-for="item in options.abcClasses" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="生命周期">
                <el-select v-model="filterStore.sales.lifecycleStatus" placeholder="请选择" clearable filterable style="width: 120px">
                  <el-option v-for="item in options.lifecycleStatuses" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="定制标记">
                <el-select v-model="filterStore.sales.customFlag" placeholder="请选择" clearable filterable style="width: 120px">
                  <el-option v-for="item in options.customFlags" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="主推标记">
                <el-select v-model="filterStore.sales.promotedFlag" placeholder="请选择" clearable filterable style="width: 120px">
                  <el-option v-for="item in options.promotedFlags" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="物料编码">
                <el-select v-model="filterStore.sales.materialCode" placeholder="请选择" clearable filterable style="width: 150px">
                  <el-option v-for="item in options.materialCodes" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="物料名称">
                <el-select
                  v-model="filterStore.sales.materialName"
                  placeholder="输入关键词搜索"
                  clearable
                  filterable
                  remote
                  :remote-method="searchMaterialNameRemote"
                  :loading="materialNameLoading"
                  style="width: 180px"
                >
                  <el-option v-for="item in options.materialNameOptions" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>

          <div class="section-header">
            <span class="section-title">销售数据明细</span>
            <el-button type="primary" size="small" :icon="Download" @click="handleExportTable">
              导出
            </el-button>
          </div>
          <!-- 汇总行 - 对齐源程序 -->
          <div class="summary-row" v-if="tableData.length > 0">
            <span class="summary-item"><strong>合计</strong></span>
            <span class="summary-item">金额：<strong>{{ formatNumber(summaryData.totalAmount) }}元</strong></span>
            <span class="summary-item">数量：<strong>{{ formatInteger(summaryData.totalQuantity) }}</strong></span>
            <span class="summary-item">进货金额：<strong>{{ formatNumber(summaryData.purchaseAmount) }}元</strong></span>
            <span class="summary-item">退货金额：<strong>{{ formatNumber(summaryData.returnAmount) }}元</strong></span>
            <span class="summary-item">进货客户数：<strong>{{ summaryData.purchaseCustomerCount }}</strong></span>
            <span class="summary-item">退货客户数：<strong>{{ summaryData.returnCustomerCount }}</strong></span>
            <span class="summary-item">进货SKU数：<strong>{{ summaryData.purchaseSkuCount }}</strong></span>
            <span class="summary-item">退货SKU数：<strong>{{ summaryData.returnSkuCount }}</strong></span>
          </div>
          <DataTable
            :data="tableData"
            :columns="tableColumns"
            :loading="loading"
            :show-pagination="true"
            :page-size="30"
            stripe
            :height="1500"
          />
        </div>
      </el-tab-pane>

      <!-- 出货仪表盘 - 对齐源程序 -->
      <el-tab-pane label="出货仪表盘" name="dashboard">
        <div class="tab-content">
          <!-- Tab1筛选器 - 简化版：只保留起始和结束时间 -->
          <div class="flow-filter">
            <el-form inline :model="filterStore.dashboard">
              <el-form-item label="起始期间">
                <el-select v-model="filterStore.dashboard.startMonth" placeholder="请选择起始期间" clearable filterable style="width: 150px">
                  <el-option v-for="item in options.startMonths" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="结束期间">
                <el-select v-model="filterStore.dashboard.endMonth" placeholder="请选择结束期间" clearable filterable style="width: 150px">
                  <el-option v-for="item in options.startMonths" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="loadDashboardCharts">查询</el-button>
                <el-button @click="resetDashboardFilters">重置</el-button>
              </el-form-item>
            </el-form>
          </div>

          <!-- 版块1: 出货情况 -->
          <h3 class="section-title-main">出货情况</h3>
          <div class="chart-section">
            <v-chart :option="salesOverviewOption" style="height: 350px" autoresize />
          </div>
          <!-- 出货情况数据表格 -->
          <div class="table-section">
            <el-table :data="salesOverviewTableData" size="small" stripe border>
              <el-table-column prop="指标" label="" width="120" fixed />
              <el-table-column v-for="month in overviewMonths" :key="month" :prop="month" :label="month" align="center" />
            </el-table>
          </div>

          <!-- 版块2: 分大区出货进度 -->
          <h3 class="section-title-main">分大区出货进度</h3>
          <div class="chart-section">
            <v-chart :option="regionProgressOption" style="height: 350px" autoresize />
          </div>
          <div class="table-section">
            <el-table :data="regionProgressTableData" size="small" stripe border>
              <el-table-column prop="系列" label="系列" width="150" fixed />
              <el-table-column v-for="month in overviewMonths" :key="month" :prop="month" :label="month" align="center" />
            </el-table>
          </div>

          <!-- 版块3: 客户分层-出货金额分布 -->
          <h3 class="section-title-main">客户分层-出货金额分布</h3>
          <div class="chart-section">
            <v-chart :option="customerAmountOption" style="height: 350px" autoresize />
          </div>
          <div class="table-section">
            <el-table :data="customerAmountTableData" size="small" stripe border>
              <el-table-column prop="等级" label="等级" width="100" fixed />
              <el-table-column v-for="month in overviewMonths" :key="month" :prop="month" :label="month" align="center" />
            </el-table>
          </div>

          <!-- 版块4: 客户分层-客户数量分布 -->
          <h3 class="section-title-main">客户分层-客户数量分布</h3>
          <div class="chart-section">
            <v-chart :option="customerCountOption" style="height: 350px" autoresize />
          </div>
          <div class="table-section">
            <el-table :data="customerCountTableData" size="small" stripe border>
              <el-table-column prop="等级" label="等级" width="100" fixed />
              <el-table-column v-for="month in overviewMonths" :key="month" :prop="month" :label="month" align="center" />
            </el-table>
          </div>

          <!-- 版块5: 主推品-出货金额分布 -->
          <h3 class="section-title-main">主推品-出货金额分布</h3>
          <div class="chart-section">
            <v-chart :option="promotedAmountOption" style="height: 350px" autoresize />
          </div>
          <div class="table-section">
            <el-table :data="promotedAmountTableData" size="small" stripe border>
              <el-table-column prop="主推标记" label="主推标记" width="120" fixed />
              <el-table-column v-for="month in overviewMonths" :key="month" :prop="month" :label="month" align="center" />
            </el-table>
          </div>

          <!-- 版块6: 主推品-渗透情况 -->
          <h3 class="section-title-main">主推品-渗透情况</h3>
          <div class="chart-section">
            <v-chart :option="promotedPenetrationOption" style="height: 350px" autoresize />
          </div>
          <div class="table-section">
            <el-table :data="promotedPenetrationTableData" size="small" stripe border>
              <el-table-column prop="分组" label="分组" width="100" fixed />
              <el-table-column v-for="month in overviewMonths" :key="month" :prop="month" :label="month" align="center" />
            </el-table>
          </div>

          <!-- 版块7: 品类-出货分布 -->
          <h3 class="section-title-main">品类-出货分布</h3>
          <div class="chart-section">
            <v-chart :option="categoryDistributionOption" style="height: 350px" autoresize />
          </div>
          <div class="table-section">
            <el-table :data="categoryDistributionTableData" size="small" stripe border>
              <el-table-column prop="品类" label="品类" width="120" fixed />
              <el-table-column v-for="month in overviewMonths" :key="month" :prop="month" :label="month" align="center" />
            </el-table>
          </div>
        </div>
      </el-tab-pane>

      <!-- 指标达成进度 - 对齐源程序 -->
      <el-tab-pane label="指标达成进度" name="indicator">
        <div class="tab-content">
          <div class="section-header">
            <span class="section-title">指标达成情况</span>
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
            <!-- 周任务列 - 对齐源程序 -->
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
          <!-- 汇总行 - 对齐源程序 -->
          <div v-if="indicatorSummary" class="indicator-summary">
            <span>汇总: 出货任务 {{ indicatorSummary.targetAmount?.toFixed(2) }} 万元 | 出货金额 {{ indicatorSummary.actualAmount?.toFixed(2) }} 万元 | 完成率 {{ indicatorSummary.achievementRate?.toFixed(2) }}%</span>
          </div>
        </div>
      </el-tab-pane>

      <!-- 销售出库明细 - 对齐源程序4个子Tab -->
      <el-tab-pane label="销售出库明细" name="detail">
        <div class="tab-content">
          <!-- Tab3筛选器 - 对齐源程序 -->
          <div class="flow-filter">
            <!-- 第一行 -->
            <el-form inline :model="filterStore.salesDetail">
              <el-form-item label="日期范围">
                <el-date-picker v-model="filterStore.salesDetail.dateRange" type="daterange" range-separator="~" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 220px" />
              </el-form-item>
              <el-form-item label="大区">
                <el-select v-model="filterStore.salesDetail.region" placeholder="请选择大区" clearable filterable style="width: 150px">
                  <el-option v-for="item in options.regions" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="客户">
                <el-select v-model="filterStore.salesDetail.customer" placeholder="请选择客户" clearable filterable style="width: 180px">
                  <el-option v-for="item in options.customers" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="loadDetailData">查询</el-button>
                <el-button @click="resetSalesDetailFilters">重置</el-button>
                <el-button text @click="detailExpanded = !detailExpanded">
                  {{ detailExpanded ? '收起' : '更多' }}
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
              </el-form-item>
            </el-form>
            <!-- 第二行（默认折叠） -->
            <el-form v-show="detailExpanded" inline :model="filterStore.salesDetail" class="more-filters">
              <el-form-item label="商品品类">
                <el-select v-model="filterStore.salesDetail.category" placeholder="请选择品类" clearable filterable style="width: 120px">
                  <el-option v-for="item in options.categories" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="ABC分类">
                <el-select v-model="filterStore.salesDetail.abcClass" placeholder="请选择" clearable filterable style="width: 100px">
                  <el-option v-for="item in options.abcClasses" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="物料编码">
                <el-select v-model="filterStore.salesDetail.materialCode" placeholder="请选择" clearable filterable style="width: 150px">
                  <el-option v-for="item in options.materialCodes" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="客户经理">
                <el-select v-model="filterStore.salesDetail.manager" placeholder="请选择客户经理" clearable filterable style="width: 150px">
                  <el-option v-for="item in options.managers" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>

          <el-tabs v-model="detailActiveTab" class="detail-tabs" :lazy="false">
            <!-- 子Tab1: 单品出货排名 -->
            <el-tab-pane label="单品出货排名" name="productRanking">
              <!-- 单品出货排名 Treemap 图 - 对齐源程序 -->
              <div class="chart-section">
                <v-chart ref="productRankingChartRef" :option="productRankingOption" style="height: 400px" autoresize />
              </div>
              <div class="section-header" style="justify-content: flex-end; margin-top: 16px;">
                <el-button type="primary" size="small" :icon="Download" @click="handleExportDetail">
                  导出
                </el-button>
              </div>
              <el-table :data="productRankingData" size="small" stripe border>
                <el-table-column type="index" label="排名" width="60" align="center" />
                <el-table-column prop="materialCode" label="物料编码" width="130" />
                <el-table-column prop="materialName" label="物料名称" min-width="180" show-overflow-tooltip />
                <el-table-column prop="salesAmount" label="含税金额合计（万元）" width="120" align="right">
                  <template #default="{ row }">
                    {{ row.salesAmount?.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="yoyAmountChange" label="YoY变动额（万元）" width="120" align="right">
                  <template #default="{ row }">
                    {{ row.yoyAmountChange?.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="momAmountChange" label="MoM变动额（万元）" width="120" align="right">
                  <template #default="{ row }">
                    {{ row.momAmountChange?.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="yoyAmountDiff" label="金额YoY（%）" width="90" align="center">
                  <template #default="{ row }">
                    <span :style="{ color: row.yoyAmountDiff >= 0 ? '#f56c6c' : '#67c23a' }">
                      {{ row.yoyAmountDiff > 0 ? '↑' : row.yoyAmountDiff < 0 ? '↓' : '-' }}{{ Math.abs(row.yoyAmountDiff || 0).toFixed(1) }}%
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="momAmountDiff" label="金额MoM（%）" width="90" align="center">
                  <template #default="{ row }">
                    <span :style="{ color: row.momAmountDiff >= 0 ? '#f56c6c' : '#67c23a' }">
                      {{ row.momAmountDiff > 0 ? '↑' : row.momAmountDiff < 0 ? '↓' : '-' }}{{ Math.abs(row.momAmountDiff || 0).toFixed(1) }}%
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="marketShare" label="金额占比（%）" width="90" align="center" />
                <el-table-column prop="salesQty" label="数量合计" width="80" align="right">
                  <template #default="{ row }">
                    {{ Number(row.salesQty).toLocaleString() }}
                  </template>
                </el-table-column>
                <el-table-column prop="yoyQtyDiff" label="YoY变动量" width="80" align="right">
                  <template #default="{ row }">
                    {{ Number(row.yoyQtyDiff).toLocaleString() }}
                  </template>
                </el-table-column>
                <el-table-column prop="momQtyDiff" label="MoM变动量" width="80" align="right">
                  <template #default="{ row }">
                    {{ Number(row.momQtyDiff).toLocaleString() }}
                  </template>
                </el-table-column>
                <el-table-column prop="qtyYoyPct" label="数量YoY（%）" width="90" align="center">
                  <template #default="{ row }">
                    <span :style="{ color: row.qtyYoyPct >= 0 ? '#f56c6c' : '#67c23a' }">
                      {{ row.qtyYoyPct > 0 ? '↑' : row.qtyYoyPct < 0 ? '↓' : '-' }}{{ Math.abs(row.qtyYoyPct || 0).toFixed(1) }}%
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="qtyMomPct" label="数量MoM（%）" width="90" align="center">
                  <template #default="{ row }">
                    <span :style="{ color: row.qtyMomPct >= 0 ? '#f56c6c' : '#67c23a' }">
                      {{ row.qtyMomPct > 0 ? '↑' : row.qtyMomPct < 0 ? '↓' : '-' }}{{ Math.abs(row.qtyMomPct || 0).toFixed(1) }}%
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="qtyShare" label="数量占比（%）" width="90" align="center" />
              </el-table>
            </el-tab-pane>

            <!-- 子Tab2: 区域×客户出货排名 -->
            <el-tab-pane label="区域×客户" name="regionCustomer">
              <div class="section-header">
                <span class="section-title">区域×客户出货排名</span>
              </div>
              <!-- 区域×客户 Waterfall 图 - 对齐源程序 -->
              <div class="chart-section">
                <v-chart ref="regionCustomerChartRef" :option="regionCustomerOption" style="height: 340px" autoresize />
              </div>
              <el-table :data="regionCustomerData" size="small" stripe border>
                <el-table-column type="index" label="排名" width="60" align="center" />
                <el-table-column prop="region" label="大区" width="100" />
                <el-table-column prop="customer" label="客户" min-width="180" show-overflow-tooltip />
                <el-table-column prop="salesAmount" label="含税金额(万元)" width="120" align="right">
                  <template #default="{ row }">
                    {{ row.salesAmount?.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="salesQty" label="数量" width="80" align="right" />
              </el-table>
            </el-tab-pane>

            <!-- 子Tab3: 区域×单品出货排名 -->
            <el-tab-pane label="区域×单品" name="regionProduct">
              <div class="section-header">
                <span class="section-title">区域×单品出货排名</span>
              </div>
              <el-table :data="regionProductData" size="small" stripe border>
                <el-table-column type="index" label="排名" width="60" align="center" />
                <el-table-column prop="region" label="大区" width="100" />
                <el-table-column prop="materialCode" label="物料编码" width="130" />
                <el-table-column prop="materialName" label="商品名称" min-width="180" show-overflow-tooltip />
                <el-table-column prop="salesAmount" label="含税金额(万元)" width="120" align="right">
                  <template #default="{ row }">
                    {{ row.salesAmount?.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="salesQty" label="数量" width="80" align="right" />
              </el-table>
            </el-tab-pane>

            <!-- 子Tab4: 客户×单品出货排名 -->
            <el-tab-pane label="客户×单品" name="customerProduct">
              <div class="section-header">
                <span class="section-title">客户×单品出货排名</span>
              </div>
              <el-table :data="customerProductData" size="small" stripe border>
                <el-table-column type="index" label="排名" width="60" align="center" />
                <el-table-column prop="customer" label="客户" min-width="150" show-overflow-tooltip />
                <el-table-column prop="materialCode" label="物料编码" width="130" />
                <el-table-column prop="materialName" label="商品名称" min-width="150" show-overflow-tooltip />
                <el-table-column prop="salesAmount" label="含税金额(万元)" width="120" align="right">
                  <template #default="{ row }">
                    {{ row.salesAmount?.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="salesQty" label="数量" width="80" align="right" />
              </el-table>
            </el-tab-pane>

            <!-- 子Tab5: TOP30商品 - 对齐源程序 -->
            <el-tab-pane label="TOP30" name="top30">
              <div class="section-header">
                <span class="section-title">TOP30商品</span>
              </div>
              <el-table :data="top30Data" size="small" stripe border class="top30-table">
                <el-table-column type="index" label="排名" width="60" align="center" fixed />
                <el-table-column prop="materialName" label="商品名称" min-width="200" fixed show-overflow-tooltip>
                  <template #default="{ row }">
                    <div class="mat-name">{{ row.materialName }}</div>
                    <div class="mat-code">{{ row.materialCode }}</div>
                  </template>
                </el-table-column>
                <el-table-column label="销售额" align="center" width="140">
                  <template #default="{ row }">
                    <div class="abs-val">{{ formatNumber(row.salesAmount) }}</div>
                    <div class="yoy-val" :style="{ color: row.yoyAmount >= 0 ? '#E02020' : '#00B578' }">
                      同比: {{ row.yoyAmount !== null ? (row.yoyAmount > 0 ? '▲' : '▼') : '--' }}{{ row.yoyAmount !== null ? Math.abs(row.yoyAmount).toFixed(2) + '%' : '' }}
                    </div>
                    <div class="yoy-val" :style="{ color: row.momAmount >= 0 ? '#E02020' : '#00B578' }">
                      环比: {{ row.momAmount !== null ? (row.momAmount > 0 ? '▲' : '▼') : '--' }}{{ row.momAmount !== null ? Math.abs(row.momAmount).toFixed(2) + '%' : '' }}
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="marketShare" label="出货金额占比(%)" width="120" align="center">
                  <template #default="{ row }">
                    {{ row.marketShare !== null ? row.marketShare.toFixed(2) + '%' : '--' }}
                  </template>
                </el-table-column>
                <el-table-column label="销量" align="center" width="120">
                  <template #default="{ row }">
                    <div class="abs-val">{{ formatInteger(row.salesQty) }}</div>
                    <div class="yoy-val" :style="{ color: row.yoyQty >= 0 ? '#E02020' : '#00B578' }">
                      同比: {{ row.yoyQty !== null ? (row.yoyQty > 0 ? '▲' : '▼') : '--' }}{{ row.yoyQty !== null ? Math.abs(row.yoyQty).toFixed(2) + '%' : '' }}
                    </div>
                    <div class="yoy-val" :style="{ color: row.momQty >= 0 ? '#E02020' : '#00B578' }">
                      环比: {{ row.momQty !== null ? (row.momQty > 0 ? '▲' : '▼') : '--' }}{{ row.momQty !== null ? Math.abs(row.momQty).toFixed(2) + '%' : '' }}
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="orderCount" label="订单数" width="80" align="right" />
                <el-table-column label="平均出货单价" width="100" align="right">
                  <template #default="{ row }">
                    {{ row.unitPrice !== null ? row.unitPrice.toFixed(2) : '--' }}
                  </template>
                </el-table-column>
                <el-table-column label="单均件数" width="80" align="right">
                  <template #default="{ row }">
                    {{ row.avgUnitsPerOrder !== null ? row.avgUnitsPerOrder.toFixed(2) : '--' }}
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-tab-pane>

      <!-- 货流分析 - 对齐源程序 -->
      <el-tab-pane label="货流分析" name="flow">
        <div class="tab-content">
          <div class="flow-filter">
            <el-form inline :model="flowFilter">
              <!-- 第一行：日期范围 -->
              <el-form-item label="日期范围">
                <el-date-picker
                  v-model="flowDateRange"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                  value-format="YYYY-MM-DD"
                  format="YYYY-MM-DD"
                  clearable
                  style="width: 220px"
                  @change="handleFlowDateRangeChange"
                />
              </el-form-item>
              <!-- 批次号 -->
              <el-form-item label="批次号">
                <el-input
                  v-model="flowFilter.batchNo"
                  placeholder="请输入批次号"
                  clearable
                  style="width: 120px"
                  @change="loadFlowData"
                />
              </el-form-item>
              <!-- 客户 -->
              <el-form-item label="客户">
                <el-select
                  v-model="flowFilter.customer"
                  placeholder="请选择客户"
                  clearable
                  filterable
                  style="width: 140px"
                  @change="loadFlowData"
                >
                  <el-option
                    v-for="item in options.customers"
                    :key="item.value || item.id"
                    :label="item.label || item.name"
                    :value="item.value || item.id"
                  />
                </el-select>
              </el-form-item>
              <!-- 物料编码 -->
              <el-form-item label="物料编码">
                <el-input
                  v-model="flowFilter.materialCode"
                  placeholder="请输入物料编码"
                  clearable
                  style="width: 120px"
                  @change="loadFlowData"
                />
              </el-form-item>
              <!-- 更多按钮 -->
              <el-form-item>
                <el-button text @click="flowExpanded = !flowExpanded">
                  {{ flowExpanded ? '收起' : '更多' }}
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
              </el-form-item>
            </el-form>
            <!-- 第二行：交易类型（默认折叠） -->
            <el-form v-show="flowExpanded" inline :model="flowFilter" class="more-filters">
              <!-- 交易类型 -->
              <el-form-item label="交易类型">
                <el-select v-model="flowFilter.txType" placeholder="请选择" clearable style="width: 120px" @change="loadFlowData">
                  <el-option label="全部" value="" />
                  <el-option label="销售出库" value="销售出库" />
                  <el-option label="退货入库" value="退货入库" />
                  <el-option label="销售退货" value="销售退货" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>
          <!-- 货流趋势图 -->
          <v-chart :option="flowTrendOption" style="height: 300px; margin-top: 16px" autoresize />
          <!-- 按单据聚合的表格 -->
          <DataTable
            :data="flowData"
            :columns="flowColumns"
            :loading="loading"
            :show-pagination="true"
            :page-size="20"
            :total="flowTotal"
            stripe
            :height="1200"
          />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, ArrowDown } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart, LineChart, TreemapChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import KpiCard from '@/components/common/KpiCard.vue'
import DataTable from '@/components/common/DataTable.vue'
import { useFilterStore } from '@/stores/filter'
import {
  getSalesDashboard,
  getSalesTable,
  getSalesIndicator,
  getSalesDetail,
  getProductFlow,
  getSalesRanking,
  getStarProducts,
  getChannelAnalysis,
  getCustomerTier,
  getPromotedPenetration,
  getCategoryDistribution
} from '@/api/sales'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  PieChart,
  BarChart,
  LineChart,
  TreemapChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

const filterStore = useFilterStore()

// 选项列表 - 用于货流分析的的客户下拉
const options = computed(() => filterStore.options)

// 物料名称远程搜索
const materialNameLoading = ref(false)
let materialNameTimer = null
function searchMaterialNameRemote(keyword) {
  if (materialNameTimer) clearTimeout(materialNameTimer)
  materialNameTimer = setTimeout(async () => {
    materialNameLoading.value = true
    try {
      await filterStore.searchMaterialName(keyword)
    } finally {
      materialNameLoading.value = false
    }
  }, 300)
}

// 状态
const activeTab = ref('table')
const detailActiveTab = ref('productRanking')  // 销售明细子Tab
const loading = ref(false)
const indicatorMonth = ref(new Date().toISOString().slice(0, 7))

// 货流筛选器 - 对齐源程序
const flowFilter = reactive({
  txType: '',           // 交易类型
  customer: null,       // 客户
  materialCode: '',     // 物料编码
  batchNo: ''           // 批次号
})

// 货流日期范围
const flowDateRange = ref([])

// 表格数据
const tableData = ref([])
const detailData = ref([])
const indicatorData = ref([])
const rankingData = ref([])
const flowData = ref([])
const flowTotal = ref(0)

// 销售明细4个子Tab数据 - 对齐源程序
const productRankingData = ref([])   // 单品出货排名
const regionCustomerData = ref([])    // 区域×客户
const regionProductData = ref([])     // 区域×单品
const customerProductData = ref([])   // 客户×单品
const top30Data = ref([])             // TOP30商品

// 汇总数据 - 对齐源程序
const summaryData = reactive({
  totalAmount: 0,
  totalQuantity: 0,
  purchaseAmount: 0,
  returnAmount: 0,
  purchaseCustomerCount: 0,
  returnCustomerCount: 0,
  purchaseSkuCount: 0,
  returnSkuCount: 0
})

// 指标达成汇总行 - 对齐源程序
const indicatorSummary = ref(null)

// 筛选器折叠状态
const filterExpanded = ref(false)
const flowExpanded = ref(false)
const detailExpanded = ref(false)

// ========== Tab2 出货仪表盘数据 - 对齐源程序 ==========
const overviewMonths = ref([])  // 月份列表

// 版块1: 出货情况图表配置
const salesOverviewOption = ref({})
const salesOverviewTableData = ref([])

// 版块2: 分大区出货进度
const regionProgressOption = ref({})
const regionProgressTableData = ref([])

// 版块3: 客户分层-出货金额分布
const customerAmountOption = ref({})
const customerAmountTableData = ref([])

// 版块4: 客户分层-客户数量分布
const customerCountOption = ref({})
const customerCountTableData = ref([])

// 版块5: 主推品-出货金额分布
const promotedAmountOption = ref({})
const promotedAmountTableData = ref([])

// 版块6: 主推品-渗透情况
const promotedPenetrationOption = ref({})
const promotedPenetrationTableData = ref([])

// 版块7: 品类-出货分布
const categoryDistributionOption = ref({})
const categoryDistributionTableData = ref([])

// 销售明细图表配置 - 对齐源程序
const productRankingOption = ref({})  // 单品出货排名 Treemap
const regionCustomerOption = ref({})  // 区域×客户 Waterfall
const productRankingChartRef = ref(null)  // 单品出货排名图表引用
const regionCustomerChartRef = ref(null)  // 区域×客户图表引用

// 计算汇总数据
function calculateSummary() {
  if (!tableData.value || tableData.value.length === 0) {
    Object.assign(summaryData, {
      totalAmount: 0,
      totalQuantity: 0,
      purchaseAmount: 0,
      returnAmount: 0,
      purchaseCustomerCount: 0,
      returnCustomerCount: 0,
      purchaseSkuCount: 0,
      returnSkuCount: 0
    })
    return
  }

  let totalAmount = 0
  let totalQuantity = 0
  let purchaseAmount = 0
  let returnAmount = 0
  const purchaseCustomers = new Set()
  const returnCustomers = new Set()
  const purchaseSkus = new Set()
  const returnSkus = new Set()

  tableData.value.forEach(row => {
    const amount = Number(row['含税金额']) || 0
    const quantity = Number(row['销售出库数量']) || 0
    const customer = row['客户'] || ''
    const sku = row['物料编码'] || ''

    totalAmount += amount
    totalQuantity += quantity

    if (amount > 0) {
      purchaseAmount += amount
      purchaseCustomers.add(customer)
      purchaseSkus.add(sku)
    } else if (amount < 0) {
      returnAmount += Math.abs(amount)
      returnCustomers.add(customer)
      returnSkus.add(sku)
    }
  })

  Object.assign(summaryData, {
    totalAmount,
    totalQuantity,
    purchaseAmount,
    returnAmount,
    purchaseCustomerCount: purchaseCustomers.size,
    returnCustomerCount: returnCustomers.size,
    purchaseSkuCount: purchaseSkus.size,
    returnSkuCount: returnSkus.size
  })
}

// 格式化数字
function formatNumber(num) {
  return Number(num || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 格式化整数
function formatInteger(num) {
  return Number(num || 0).toLocaleString('zh-CN')
}

// 图表配置 - 对齐源程序Tab2
const flowTrendOption = ref({})

// 表格列配置 - 对齐源程序 rpt_sales_out_wide 全部35个字段
const tableColumns = [
  // 销售原始字段
  { prop: '单据日期', label: '单据日期', width: 110 },
  { prop: '单据编号', label: '单据编号', width: 160 },
  { prop: '源头交易类型', label: '源头交易类型', width: 120 },
  { prop: '交易类型名称', label: '交易类型名称', width: 100 },
  { prop: '客户', label: '客户', minWidth: 180 },
  { prop: '客户分类', label: '客户分类', width: 100 },
  { prop: '大区经理', label: '大区经理', width: 100 },
  { prop: '仓库', label: '仓库', width: 120 },
  { prop: '物料编码', label: '物料编码', width: 130 },
  { prop: '物料名称', label: '物料名称', minWidth: 150 },
  { prop: '品牌', label: '品牌', width: 120 },
  { prop: '含税金额', label: '含税金额', width: 120, align: 'right' },
  { prop: '批次号', label: '批次号', width: 120 },
  { prop: '出货渠道', label: '出货渠道', width: 100 },
  { prop: '审核日期', label: '审核日期', width: 110 },
  { prop: '审核时间', label: '审核时间', width: 160 },
  { prop: '创建人', label: '创建人', width: 80 },
  { prop: '销售出库数量', label: '销售出库数量', width: 100, align: 'right' },
  { prop: '应发数量', label: '应发数量', width: 100, align: 'right' },
  { prop: '已开票数量', label: '已开票数量', width: 100, align: 'right' },
  { prop: '交易类型', label: '交易类型', width: 100 },
  { prop: '来源单据交易类型', label: '来源单据交易类型', width: 130 },
  { prop: '入账方式', label: '入账方式', width: 100 },
  { prop: '含税单价', label: '含税单价', width: 100, align: 'right' },
  { prop: '源头单据号', label: '源头单据号', width: 160 },
  { prop: '备注', label: '备注', minWidth: 150 },
  // 商品属性（来自 dim_product_attr）
  { prop: '商品品类', label: '商品品类', width: 100 },
  { prop: 'ABC分类', label: 'ABC分类', width: 80 },
  { prop: '生命周期状态', label: '生命周期状态', width: 100 },
  { prop: '定制标记', label: '定制标记', width: 80 },
  { prop: '主推标记', label: '主推标记', width: 80 },
  // 客户信息（来自 dim_customer）
  { prop: '大区', label: '大区', width: 100 },
  { prop: '客户经理', label: '客户经理', width: 100 },
  { prop: '渠道', label: '渠道', width: 100 },
  // 创建时间
  { prop: '创建时间', label: '创建时间', width: 160 }
]

const detailColumns = [
  { prop: '单据编号', label: '单据编号', width: 150 },
  { prop: '单据日期', label: '单据日期', width: 120 },
  { prop: '客户', label: '客户', minWidth: 150 },
  { prop: '物料编码', label: '物料编码', width: 120 },
  { prop: '物料名称', label: '物料名称', minWidth: 150 },
  { prop: '销售出库数量', label: '销售出库数量', width: 80, align: 'right' },
  { prop: '含税单价', label: '含税单价', width: 100, align: 'right' },
  { prop: '含税金额', label: '含税金额', width: 120, align: 'right' },
  { prop: '备注', label: '备注', minWidth: 150 }
]

const indicatorColumns = [
  { prop: 'regionName', label: '大区', width: 120 },
  { prop: 'managerName', label: '业务经理', width: 120 },
  { prop: 'targetAmount', label: '目标金额', width: 120, align: 'right' },
  { prop: 'actualAmount', label: '实际金额', width: 120, align: 'right' },
  { prop: 'gap', label: '差距', width: 100, align: 'right' },
  { prop: 'achievementRate', label: '达成率', width: 180, align: 'center' }
]

// 货流表格列 - 原始明细数据
const flowColumns = [
  { prop: '单据编号', label: '单据编号', width: 160 },
  { prop: '已开票数量', label: '已开票数量', width: 100 },
  { prop: '源头交易类型', label: '源头交易类型', width: 100 },
  { prop: '交易类型', label: '交易类型', width: 100 },
  { prop: '客户', label: '客户', minWidth: 180 },
  { prop: '客户分类', label: '客户分类', width: 100 },
  { prop: '仓库', label: '仓库', width: 100 },
  { prop: '审核日期', label: '审核日期', width: 110 },
  { prop: '物料编码', label: '物料编码', width: 130 },
  { prop: '物料名称', label: '物料名称', minWidth: 150, showOverflowTooltip: true },
  { prop: '批次号', label: '批次号', width: 120 },
  { prop: '含税金额', label: '含税金额', width: 120, align: 'right' },
  { prop: '销售出库数量', label: '销售出库数量', width: 120, align: 'right' }
]

// 进度条颜色
function getProgressColor(rate) {
  if (rate >= 100) return '#67c23a'
  if (rate >= 80) return '#e6a23c'
  return '#f56c6c'
}

// 加载仪表盘图表数据 - 对齐源程序7个版块
async function loadDashboardCharts() {
  loading.value = true
  try {
    const baseParams = {
      start_year_month: filterStore.dashboard.startMonth,
      end_year_month: filterStore.dashboard.endMonth
    }

    // ========== 版块1+2: 出货情况和分大区出货进度 - 调用 dashboard API ==========
    const dashboardRes = await getSalesDashboard(baseParams)
    const dashboardData = dashboardRes.data?.data || dashboardRes.data || {}
    overviewMonths.value = dashboardData.months || []

    if (dashboardData.table_data && dashboardData.table_data.length > 0) {
      const salesOverview = {
        targets: dashboardData.table_data.map(d => d.target),
        amounts: dashboardData.table_data.map(d => d.amount_wan),
        completionRates: dashboardData.table_data.map(d => d.completion_rate),
        yoy: dashboardData.table_data.map(d => d.yoy),
        mom: dashboardData.table_data.map(d => d.mom)
      }
      salesOverviewOption.value = buildSalesOverviewChart(salesOverview)
      salesOverviewTableData.value = buildSalesOverviewTable(salesOverview)
    }

    if (dashboardData.region_data && dashboardData.region_data.length > 0) {
      const regionProgress = buildRegionProgressFromRaw(dashboardData.region_data, dashboardData.months)
      regionProgressOption.value = buildRegionProgressChart(regionProgress)
      regionProgressTableData.value = buildRegionProgressTable(regionProgress)
    }

    // ========== 版块3+4: 客户分层 - 调用 customer-tier API ==========
    // 使用用户选择的起始月份和结束月份
    const customerTierRes = await getCustomerTier({
      start_year_month: filterStore.dashboard.startMonth,
      end_year_month: filterStore.dashboard.endMonth
    })
    const customerTierData = customerTierRes.data?.data || customerTierRes.data || {}

    if (customerTierData.tier_by_month && Object.keys(customerTierData.tier_by_month).length > 0) {
      const tierByMonth = customerTierData.tier_by_month
      const months = tierByMonth.months || []
      overviewMonths.value = months.length > 0 ? months : overviewMonths.value

      // 客户分层-出货金额分布
      const amountData = tierByMonth.amount_data || {}
      const customerAmount = {
        months: months,
        tiers: customerTierData.tier_order || ['<5万', '5-10万', '10-20万', '20-50万', '50-100万', '>=100万'],
        data: amountData
      }
      customerAmountOption.value = buildCustomerAmountChart(customerAmount)
      customerAmountTableData.value = buildCustomerAmountTable(customerAmount)

      // 客户分层-客户数量分布
      const countData = tierByMonth.customer_data || {}
      const customerCount = {
        months: months,
        tiers: customerTierData.tier_order || ['<5万', '5-10万', '10-20万', '20-50万', '50-100万', '>=100万'],
        data: countData
      }
      customerCountOption.value = buildCustomerCountChart(customerCount)
      customerCountTableData.value = buildCustomerCountTable(customerCount)
    }

    // ========== 版块5+6: 主推品 - 调用 promoted-penetration API ==========
    const promotedRes = await getPromotedPenetration({ start_month: filterStore.dashboard.startMonth, end_month: filterStore.dashboard.endMonth })
    const promotedData = promotedRes.data?.data || promotedRes.data || {}

    if (promotedData.months && promotedData.months.length > 0) {
      const months = promotedData.months
      const amounts = promotedData.amounts || {}
      const customers = promotedData.customers || {}
      const penetration = promotedData.penetration || {}

      // 主推品-出货金额分布 (堆叠面积图)
      promotedAmountOption.value = buildPromotedAmountChart({ months, amounts })
      promotedAmountTableData.value = Object.keys(amounts).map(flag => {
        const row = { '主推标记': flag }
        amounts[flag].forEach((v, i) => {
          row[months[i]] = (v / 10000).toFixed(2)
        })
        return row
      })

      // 主推品-渗透情况 (组合图)
      promotedPenetrationOption.value = buildPromotedPenetrationChart({ months, customers, penetration })
      promotedPenetrationTableData.value = Object.keys(customers).map(flag => {
        const row = { '分组': flag }
        customers[flag].forEach((v, i) => {
          row[months[i]] = v
        })
        return row
      })
    }

    // ========== 版块7: 品类-出货分布 - 调用 category-distribution API ==========
    const categoryRes = await getCategoryDistribution({ start_month: filterStore.dashboard.startMonth, end_month: filterStore.dashboard.endMonth })
    const categoryData = categoryRes.data?.data || categoryRes.data || {}

    if (categoryData.months && categoryData.months.length > 0) {
      const months = categoryData.months
      const categories = categoryData.categories || {}

      // 品类-出货分布 (堆叠柱状图)
      categoryDistributionOption.value = buildCategoryDistributionChart({ months, categories })
      categoryDistributionTableData.value = Object.keys(categories).map(cat => {
        const row = { '品类': cat }
        categories[cat].forEach((v, i) => {
          row[months[i]] = (v / 10000).toFixed(2)
        })
        return row
      })
    }

  } catch (error) {
    console.error('加载仪表盘数据失败:', error)
    initEmptyCharts()
  } finally {
    loading.value = false
  }
}

// 初始化空图表
function initEmptyCharts() {
  overviewMonths.value = []
  salesOverviewOption.value = {}
  salesOverviewTableData.value = []
  regionProgressOption.value = {}
  regionProgressTableData.value = []
  customerAmountOption.value = {}
  customerAmountTableData.value = []
  customerCountOption.value = {}
  customerCountTableData.value = []
  promotedAmountOption.value = {}
  promotedAmountTableData.value = []
  promotedPenetrationOption.value = {}
  promotedPenetrationTableData.value = []
  categoryDistributionOption.value = {}
  categoryDistributionTableData.value = []
  top30Data.value = []
}

// ========== 图表构建函数 - 对齐源程序 ==========

// 辅助函数：从后端 raw data 构建 regionProgress 格式
function buildRegionProgressFromRaw(rawData, months) {
  if (!rawData || !rawData.length) return { names: [], series: [] }

  // 获取所有大区名称
  const regionNames = [...new Set(rawData.map(d => d.region).filter(Boolean))].slice(0, 10)

  // 按月份×大区聚合
  const monthRegionMap = {}
  rawData.forEach(d => {
    if (!monthRegionMap[d.year_month]) {
      monthRegionMap[d.year_month] = {}
    }
    if (d.region && d.amount) {
      monthRegionMap[d.year_month][d.region] = (monthRegionMap[d.year_month][d.region] || 0) + d.amount
    }
  })

  // 构建 series
  const series = regionNames.map(name => ({
    name: name,
    data: months.map(m => monthRegionMap[m]?.[name] || 0)
  }))

  return { names: regionNames, series }
}

// 版块1: 出货情况 - 柱状图+双Y轴折线
function buildSalesOverviewChart(data) {
  const months = overviewMonths.value
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['完成额', '指标完成率', '同比', '环比'], bottom: 0 },
    grid: { left: '3%', right: '8%', bottom: '12%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: [
      { type: 'value', name: '完成额(万元)', splitLine: { show: false } },
      { type: 'value', name: '完成率/同比/环比(%)', splitLine: { show: false } }
    ],
    series: [
      { name: '完成额', type: 'bar', data: data.amounts || [], itemStyle: { color: '#595959' } },
      { name: '指标完成率', type: 'line', yAxisIndex: 1, data: data.completionRates || [], itemStyle: { color: '#e74c3c' } },
      { name: '同比', type: 'line', yAxisIndex: 1, data: data.yoy || [], itemStyle: { color: '#0077cc' }, symbol: 'diamond' },
      { name: '环比', type: 'line', yAxisIndex: 1, data: data.mom || [], itemStyle: { color: '#27ae60' }, symbol: 'triangle' }
    ]
  }
}

function buildSalesOverviewTable(data) {
  const months = overviewMonths.value
  return [{
    '指标': '指标(万元)',
    ...Object.fromEntries(months.map((m, i) => [m, data.targets?.[i]?.toFixed(2) || '-']))
  }, {
    '指标': '完成额(万元)',
    ...Object.fromEntries(months.map((m, i) => [m, data.amounts?.[i]?.toFixed(2) || '-']))
  }, {
    '指标': '完成率(%)',
    ...Object.fromEntries(months.map((m, i) => [m, data.completionRates?.[i] || '-']))
  }, {
    '指标': '同比(%)',
    ...Object.fromEntries(months.map((m, i) => [m, data.yoy?.[i] || '-']))
  }, {
    '指标': '环比(%)',
    ...Object.fromEntries(months.map((m, i) => [m, data.mom?.[i] || '-']))
  }]
}

// 版块2: 分大区出货进度 - 堆叠面积图
function buildRegionProgressChart(data) {
  const months = overviewMonths.value
  const series = data.series || []
  const colors = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f', '#e5c494', '#b3b3b3']
  return {
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        let total = 0
        let result = params[0].name + '<br/>'
        params.forEach(p => {
          total += (p.value || 0)
          result += p.marker + ' ' + p.seriesName + ': ' + (p.value || 0).toFixed(2) + ' 万元<br/>'
        })
        result += '<strong>合计: ' + total.toFixed(2) + ' 万元</strong><br/>'
        return result
      }
    },
    legend: { data: data.names || [], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '出货额(万元)', splitLine: { show: false } },
    series: series.map((s, i) => ({
      name: s.name,
      type: 'line',
      stack: '总量',
      areaStyle: {},
      data: s.data.map(v => v / 10000),
      lineStyle: { color: colors[i % colors.length] },
      itemStyle: { color: colors[i % colors.length] }
    }))
  }
}

function buildRegionProgressTable(data) {
  const months = overviewMonths.value
  return (data.series || []).map(s => ({
    '系列': s.name,
    ...Object.fromEntries(months.map((m, i) => [m, ((s.data?.[i] || 0) / 10000).toFixed(2)]))
  }))
}

// 版块3: 客户分层-出货金额分布 - 堆叠面积图
// data 格式: { months: [], tiers: [], data: { '<5万': [], '5-10万': [], ... } }
function buildCustomerAmountChart(data) {
  const months = data.months || overviewMonths.value
  const tiers = data.tiers || ['<5万', '5-10万', '10-20万', '20-50万', '50-100万', '>=100万']
  const dataMap = data.data || {}
  const colors = ['#d1c6c6', '#c4a0a0', '#bd7474', '#bd4141', '#a52626', '#851313']
  return {
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        let total = 0
        let result = params[0].name + '<br/>'
        params.forEach(p => {
          total += (p.value || 0)
          result += p.marker + ' ' + p.seriesName + ': ' + (p.value || 0).toFixed(2) + ' 万元<br/>'
        })
        result += '<strong>合计: ' + total.toFixed(2) + ' 万元</strong><br/>'
        return result
      }
    },
    legend: { data: tiers, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '出货额(万元)', splitLine: { show: false } },
    series: tiers.map((tier, i) => ({
      name: tier,
      type: 'line',
      stack: '总量',
      areaStyle: {},
      data: (dataMap[tier] || []),
      itemStyle: { color: colors[i] }
    }))
  }
}

function buildCustomerAmountTable(data) {
  const months = data.months || overviewMonths.value
  const tiers = data.tiers || ['<5万', '5-10万', '10-20万', '20-50万', '50-100万', '>=100万']
  const dataMap = data.data || {}
  return tiers.map(tier => ({
    '等级': tier,
    ...Object.fromEntries(months.map((m, i) => [m, ((dataMap[tier]?.[i] || 0)).toFixed(2)]))
  }))
}

// 版块4: 客户分层-客户数量分布 - 堆叠柱状图
function buildCustomerCountChart(data) {
  const months = data.months || overviewMonths.value
  const tiers = data.tiers || ['<5万', '5-10万', '10-20万', '20-50万', '50-100万', '>=100万']
  const dataMap = data.data || {}
  const colors = ['#d1c6c6', '#c4a0a0', '#bd7474', '#bd4141', '#a52626', '#851313']
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: tiers, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '客户数', splitLine: { show: false } },
    series: tiers.map((tier, i) => ({
      name: tier,
      type: 'bar',
      stack: '总量',
      data: dataMap[tier] || [],
      itemStyle: { color: colors[i] }
    }))
  }
}

function buildCustomerCountTable(data) {
  const months = data.months || overviewMonths.value
  const tiers = data.tiers || ['<5万', '5-10万', '10-20万', '20-50万', '50-100万', '>=100万']
  const dataMap = data.data || {}
  return tiers.map(tier => ({
    '等级': tier,
    ...Object.fromEntries(months.map((m, i) => [m, dataMap[tier]?.[i] || 0]))
  }))
}

// 版块5: 主推品-出货金额分布 (堆叠面积图)
function buildPromotedAmountChart(data) {
  const months = data.months || []
  const amounts = data.amounts || {}
  const flags = Object.keys(amounts)

  // 配色：下午茶→红色系，小狗→灰色系，其它→黑色
  const 红色系 = ['#722626', '#983e3e', '#b16161', '#be9191']
  const 灰色系 = ['#554343', '#856f6f', '#ada3a3']
  let redIdx = 0, grayIdx = 0

  function getColor(flag) {
    if (flag.includes('下午茶')) {
      return 红色系[redIdx++ % 红色系.length]
    } else if (flag.includes('小狗')) {
      return 灰色系[grayIdx++ % 灰色系.length]
    }
    return '#333333'
  }

  return {
    tooltip: { trigger: 'axis', formatter: function(params) {
      let result = params[0].name + '<br/>'
      let total = 0
      params.forEach(p => {
        total += p.value
        result += p.marker + ' ' + p.seriesName + ': ' + (p.value || 0).toFixed(2) + ' 万元<br/>'
      })
      result += '<strong>合计: ' + total.toFixed(2) + ' 万元</strong>'
      return result
    }},
    legend: { data: flags, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '出货额(万元)', splitLine: { show: false } },
    series: flags.map(flag => ({
      name: flag,
      type: 'line',
      stack: '总量',
      areaStyle: {},
      data: amounts[flag].map(v => v / 10000),
      lineStyle: { width: 0.5, color: getColor(flag) },
      itemStyle: { color: getColor(flag) },
      emphasis: { focus: 'series' }
    }))
  }
}

// 版块6: 主推品-渗透情况 (组合图)
function buildPromotedPenetrationChart(data) {
  const months = data.months || []
  const customers = data.customers || {}
  const penetration = data.penetration || {}
  const flags = Object.keys(customers)

  function getColor(flag) {
    if (flag.includes('下午茶')) return '#983e3e'
    if (flag.includes('小狗')) return '#856f6f'
    return '#333333'
  }

  // 柱状图系列（客户数）
  const barSeries = flags.map(flag => ({
    name: flag,
    type: 'bar',
    data: customers[flag],
    itemStyle: { color: getColor(flag) }
  }))

  // 折线图系列（渗透率）
  const lineFlags = flags.filter(f => f.includes('下午茶') || f.includes('小狗'))
  const lineSeries = lineFlags.map(flag => ({
    name: flag + '渗透率',
    type: 'line',
    yAxisIndex: 1,
    data: penetration[flag] || [],
    lineStyle: { color: getColor(flag), width: 2 },
    symbol: 'circle',
    symbolSize: 6
  }))

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: [...flags, ...lineFlags.map(f => f + '渗透率')], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: [
      { type: 'value', name: '客户数', splitLine: { show: false } },
      { type: 'value', name: '渗透率(%)', splitLine: { show: false }, max: 105 }
    ],
    series: [...barSeries, ...lineSeries]
  }
}

// 版块7: 品类-出货分布 (堆叠柱状图)
function buildCategoryDistributionChart(data) {
  const months = data.months || []
  const categories = data.categories || {}
  const catNames = Object.keys(categories)
  const colors = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f', '#e5c494', '#b3b3b3']

  return {
    tooltip: { trigger: 'axis', formatter: function(params) {
      let result = params[0].name + '<br/>'
      let total = 0
      params.forEach(p => {
        total += p.value
        result += p.marker + ' ' + p.seriesName + ': ' + (p.value || 0).toFixed(2) + ' 万元<br/>'
      })
      result += '<strong>合计: ' + total.toFixed(2) + ' 万元</strong>'
      return result
    }},
    legend: { data: catNames, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '出货额(万元)', splitLine: { show: false } },
    series: catNames.map((cat, i) => ({
      name: cat,
      type: 'bar',
      stack: '总量',
      data: categories[cat].map(v => v / 10000),
      itemStyle: { color: colors[i % colors.length] }
    }))
  }
}

// 加载销售宽表 - 对齐源程序筛选器
async function loadTableData() {
  loading.value = true
  try {
    const params = {
      // 基础筛选（对齐后端 API 参数名）
      region: filterStore.sales.region,
      manager: filterStore.sales.manager,
      customer: filterStore.sales.customer,
      channel: filterStore.sales.channel,
      // 单据日期筛选
      doc_date_from: filterStore.sales.docDateRange?.[0] || null,
      doc_date_to: filterStore.sales.docDateRange?.[1] || null,
      // 审核日期筛选（后端用 date_from/date_to）
      date_from: filterStore.sales.auditDateRange?.[0] || null,
      date_to: filterStore.sales.auditDateRange?.[1] || null,
      // 商品属性筛选（对齐源程序）
      category: filterStore.sales.category,
      abc_class: filterStore.sales.abcClass,
      lifecycle_status: filterStore.sales.lifecycleStatus,
      custom_flag: filterStore.sales.customFlag,
      promoted_flag: filterStore.sales.promotedFlag,
      material_code: filterStore.sales.materialCode,
      material_name: filterStore.sales.materialName,
      page: 1,
      page_size: 1000
    }

    // 循环获取所有分页数据
    let allData = []
    let totalRecords = 0
    let backendSummary = {}

    while (true) {
      const response = await getSalesTable(params)
      const pageData = response.data?.data || response.data || []

      // 首次请求获取总记录数和汇总数据
      if (params.page === 1) {
        totalRecords = response.data?.total || pageData.length || 0
        backendSummary = response.data?.summary || {}
      }

      allData = allData.concat(pageData)

      // 检查是否已获取所有数据
      if (allData.length >= totalRecords || pageData.length === 0) {
        break
      }

      // 下一页
      params.page++
    }

    tableData.value = allData
    // 使用后端返回的汇总数据（不受分页限制）
    Object.assign(summaryData, {
      totalAmount: backendSummary.total_amount || 0,
      totalQuantity: backendSummary.total_quantity || 0,
      purchaseAmount: backendSummary.inbound_amount || 0,
      returnAmount: backendSummary.outbound_amount || 0,
      purchaseCustomerCount: backendSummary.inbound_customer_count || 0,
      returnCustomerCount: backendSummary.outbound_customer_count || 0,
      purchaseSkuCount: backendSummary.inbound_sku_count || 0,
      returnSkuCount: backendSummary.outbound_sku_count || 0
    })
  } catch (error) {
    console.error('加载销售宽表失败:', error)
    tableData.value = []
    // 失败时使用后端返回的 summary 或置零
    const backendSummary = error.response?.data?.summary || {}
    Object.assign(summaryData, {
      totalAmount: backendSummary.total_amount || 0,
      totalQuantity: backendSummary.total_quantity || 0,
      purchaseAmount: backendSummary.inbound_amount || 0,
      returnAmount: backendSummary.outbound_amount || 0,
      purchaseCustomerCount: backendSummary.inbound_customer_count || 0,
      returnCustomerCount: backendSummary.outbound_customer_count || 0,
      purchaseSkuCount: backendSummary.inbound_sku_count || 0,
      returnSkuCount: backendSummary.outbound_sku_count || 0
    })
  } finally {
    loading.value = false
  }
}

// 加载指标达成数据 - 对齐源程序
async function loadIndicatorData() {
  loading.value = true
  try {
    // 转换月份格式 YYYY-MM -> YYYY/MM，使用 indicatorMonth.value 与日期选择器同步
    const month = indicatorMonth.value?.replace('-', '/')
    const params = {
      region: filterStore.indicator.region,
      manager: filterStore.indicator.manager,
      month: month
    }
    const response = await getSalesIndicator(params)
    const data = response.data?.data || response.data || []

    // 转换后端字段名为前端期望的格式
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

    // 计算汇总行 - 对齐源程序
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
  }
}

// 加载销售明细 - 对齐源程序4个子Tab
async function loadDetailData() {
  loading.value = true
  try {
    // 根据激活的Tab确定group_by参数
    const groupByMap = {
      'productRanking': 'material',
      'regionCustomer': 'region_customer',
      'regionProduct': 'region_material',
      'customerProduct': 'customer_material'
    }

    const params = {
      region: filterStore.salesDetail.region,
      manager: filterStore.salesDetail.manager,
      customer: filterStore.salesDetail.customer,
      date_from: filterStore.salesDetail.dateRange?.[0] || null,
      date_to: filterStore.salesDetail.dateRange?.[1] || null,
      group_by: groupByMap[detailActiveTab.value] || 'material'
    }
    const response = await getSalesDetail(params)
    const resData = response.data || {}

    // 后端返回结构: { data: [...items], total, page, page_size } 或直接返回数组
    const listData = Array.isArray(resData) ? resData : (resData.data || [])
    if (detailActiveTab.value === 'productRanking') {
      productRankingData.value = listData.map(row => ({
        materialCode: row.material_code,
        materialName: row.material_name,
        salesAmount: row.tax_included_amount_sum,
        yoyAmountChange: row.yoy_amount_diff,
        momAmountChange: row.mom_amount_diff,
        yoyAmountDiff: row.amount_yoy_pct,
        momAmountDiff: row.amount_mom_pct,
        marketShare: row.amount_share_pct,
        salesQty: row.quantity_sum,
        yoyQtyDiff: row.yoy_qty_diff,
        momQtyDiff: row.mom_qty_diff,
        qtyYoyPct: row.qty_yoy_pct,
        qtyMomPct: row.qty_mom_pct,
        qtyShare: row.qty_share_pct
      }))
    } else if (detailActiveTab.value === 'regionCustomer') {
      regionCustomerData.value = listData.map(row => ({
        region: row.region,
        customer: row.customer,
        salesAmount: row.tax_included_amount_sum,
        salesQty: row.quantity_sum
      }))
    } else if (detailActiveTab.value === 'regionProduct') {
      regionProductData.value = listData.map(row => ({
        region: row.region,
        materialCode: row.material_code,
        materialName: row.material_name,
        salesAmount: row.tax_included_amount_sum,
        salesQty: row.quantity_sum
      }))
    } else if (detailActiveTab.value === 'customerProduct') {
      // group_by=customer_material 时，后端只返回 customer, material_code, material_name
      customerProductData.value = listData.map(row => ({
        customer: row.customer,
        materialCode: row.material_code,
        materialName: row.material_name,
        salesAmount: row.tax_included_amount_sum,
        salesQty: row.quantity_sum
      }))
    } else if (detailActiveTab.value === 'top30') {
      // TOP30 使用独立的 star_products API
      const starResponse = await getStarProducts({
        region: filterStore.salesDetail.region,
        manager: filterStore.salesDetail.manager,
        date_from: filterStore.salesDetail.dateRange?.[0] || null,
        date_to: filterStore.salesDetail.dateRange?.[1] || null,
        top_n: 30
      })
      const starData = starResponse.data?.data || starResponse.data || {}
      const products = starData.products || []
      top30Data.value = products.map(row => ({
        materialCode: row.material_code,
        materialName: row.material_name,
        brand: row.brand,
        salesAmount: row.sales_amount_wan,
        salesQty: row.sales_qty,
        orderCount: row.order_count,
        marketShare: row.market_share,
        unitPrice: row.unit_price,
        avgUnitsPerOrder: row.avg_units_per_order,
        yoyAmount: row.yoy_amount,
        yoyQty: row.yoy_qty,
        momAmount: row.mom_amount,
        momQty: row.mom_qty
      }))
      return  // TOP30 单独处理，不需要下面的逻辑
    }
    detailData.value = listData

    // 构建图表 - 对齐源程序
    // 延迟一下让 DOM 完成渲染（tab 可能刚切换）
    setTimeout(() => {
      buildDetailCharts()
    }, 100)
  } catch (error) {
    console.error('加载销售明细失败:', error)
    detailData.value = []
    productRankingData.value = []
    regionCustomerData.value = []
    regionProductData.value = []
    customerProductData.value = []
    top30Data.value = []
    productRankingOption.value = {}
    regionCustomerOption.value = {}
  } finally {
    loading.value = false
  }
}

// 构建销售明细图表 - 对齐源程序
function buildDetailCharts() {
  // 单品出货排名 Treemap - 对齐源程序 Plotly treemap
  if (productRankingData.value.length > 0) {
    const treemapData = productRankingData.value.map(row => ({
      name: row.materialName || row.materialCode,
      value: row.salesAmount || 0,
      itemStyle: {
        color: getTreemapColor(row.salesAmount, productRankingData.value)
      }
    }))

    productRankingOption.value = {
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          const d = productRankingData.value.find(x => (x.materialName || x.materialCode) === params.name)
          if (d) {
            return `<b>${params.name}</b><br/>含税金额：${d.salesAmount?.toFixed(2)} 万元<br/>数量：${d.salesQty || 0}<br/>金额占比：${d.marketShare || 0}%`
          }
          return params.name
        }
      },
      series: [{
        type: 'treemap',
        data: treemapData,
        label: {
          show: true,
          formatter: '{b}',
          fontSize: 11,
          color: '#333'
        },
        breadcrumb: { show: false },
        levels: [
          {
            itemStyle: {
              borderColor: '#fff',
              borderWidth: 2,
              gapWidth: 2
            }
          }
        ]
      }]
    }
  } else {
    productRankingOption.value = {}
  }

  // 区域×客户 Waterfall - 对齐源程序 Plotly waterfall
  // 由于后端未返回 lifecycle_status/abc_class 分类数据，暂时显示柱状图
  if (regionCustomerData.value.length > 0) {
    const sortedData = [...regionCustomerData.value].sort((a, b) => b.salesAmount - a.salesAmount)
    const top10 = sortedData.slice(0, 10)

    regionCustomerOption.value = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: top10.map(d => d.customer?.substring(0, 8) || ''),
        axisLabel: { fontSize: 11, rotate: 30 }
      },
      yAxis: {
        type: 'value',
        name: '金额(万元)',
        splitLine: { show: false }
      },
      series: [{
        type: 'bar',
        data: top10.map(d => ({
          value: d.salesAmount,
          itemStyle: { color: '#8faeae' }
        })),
        barWidth: '60%',
        label: {
          show: true,
          position: 'top',
          formatter: (params) => params.value.toFixed(1),
          fontSize: 10
        }
      }]
    }
    // 区域×客户图表 resize
    setTimeout(() => {
      regionCustomerChartRef.value?.resize()
    }, 50)
  } else {
    regionCustomerOption.value = {}
  }

  // 单品出货排名图表 resize
  setTimeout(() => {
    productRankingChartRef.value?.resize()
  }, 50)
}

// 获取 Treemap 颜色 - 更平滑的渐变
function getTreemapColor(value, dataArray) {
  const values = dataArray.map(d => d.salesAmount || 0).filter(v => v > 0)
  if (values.length === 0) return '#f5f5f5'
  const max = Math.max(...values)
  const min = Math.min(...values)
  const range = max - min
  if (range === 0) return 'rgb(217,217,217)'
  const ratio = (value - min) / range
  // 平滑渐变：白->浅灰->浅红->红->深红
  const colors = [
    { pos: 0.0, r: 255, g: 255, b: 255 },
    { pos: 0.2, r: 240, g: 240, b: 240 },
    { pos: 0.4, r: 255, g: 200, b: 200 },
    { pos: 0.6, r: 255, g: 150, b: 150 },
    { pos: 0.8, r: 255, g: 100, b: 100 },
    { pos: 1.0, r: 255, g: 50, b: 50 }
  ]
  for (let i = 0; i < colors.length - 1; i++) {
    if (ratio >= colors[i].pos && ratio <= colors[i + 1].pos) {
      const t = (ratio - colors[i].pos) / (colors[i + 1].pos - colors[i].pos)
      const r = Math.round(colors[i].r + (colors[i + 1].r - colors[i].r) * t)
      const g = Math.round(colors[i].g + (colors[i + 1].g - colors[i].g) * t)
      const b = Math.round(colors[i].b + (colors[i + 1].b - colors[i].b) * t)
      return `rgb(${r},${g},${b})`
    }
  }
  return 'rgb(255,50,50)'
}

// 货流日期范围变更处理
function handleFlowDateRangeChange(value) {
  if (value && value.length === 2) {
    flowFilter.dateFrom = value[0]
    flowFilter.dateTo = value[1]
  } else {
    flowFilter.dateFrom = null
    flowFilter.dateTo = null
  }
  loadFlowData()
}

// 加载货流数据 - 对齐源程序
async function loadFlowData() {
  loading.value = true
  try {
    let allData = []
    let totalRecords = 0
    let page = 1
    const pageSize = 500

    console.log('[Flow] Starting loadFlowData, pageSize:', pageSize)
    console.log('[Flow] flowFilter:', JSON.stringify(flowFilter))

    // 循环获取所有数据
    while (true) {
      const params = {
        tx_type: flowFilter.txType,
        customer_id: flowFilter.customer,
        material_code: flowFilter.materialCode,
        batch_no: flowFilter.batchNo,
        date_from: flowFilter.dateFrom,
        date_to: flowFilter.dateTo,
        page: page,
        page_size: pageSize
      }
      console.log('[Flow] Request params:', JSON.stringify(params))

      const response = await getProductFlow(params)
      const data = response.data?.data || response.data || {}
      console.log('[Flow] Response data:', { total: data.total, itemsCount: (data.items || []).length, pageSize: data.page_size })

      const pageData = data.items || data.list || []

      if (page === 1) {
        totalRecords = data.total || pageData.length || 0
        flowTotal.value = totalRecords
        console.log('[Flow] Set totalRecords:', totalRecords)
      }

      allData = allData.concat(pageData)
      console.log('[Flow] after page', page, 'allData.length:', allData.length, 'totalRecords:', totalRecords)

      if (allData.length >= totalRecords || pageData.length === 0) {
        console.log('[Flow] Breaking loop')
        break
      }
      page++
    }

    flowData.value = allData
    console.log('[Flow] Final flowData.value.length:', flowData.value.length, 'flowTotal.value:', flowTotal.value)

    // 货流趋势图（从第一页数据获取）
    const firstPageParams = {
      tx_type: flowFilter.txType,
      customer_id: flowFilter.customer,
      material_code: flowFilter.materialCode,
      batch_no: flowFilter.batchNo,
      date_from: flowFilter.dateFrom,
      date_to: flowFilter.dateTo,
      page: 1,
      page_size: pageSize
    }
    const response = await getProductFlow(firstPageParams)
    const trendData = response.data?.data || response.data || {}

    flowTrendOption.value = {
      tooltip: { trigger: 'axis' },
      legend: { data: ['入库', '出库'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true, splitLine: { show: false } },
      xAxis: {
        type: 'category',
        data: trendData.dates || []
      },
      yAxis: { type: 'value', splitLine: { show: false } },
      series: [
        {
          name: '入库',
          type: 'bar',
          data: trendData.inbounds || [],
          itemStyle: { color: '#67c23a' }
        },
        {
          name: '出库',
          type: 'bar',
          data: trendData.outbounds || [],
          itemStyle: { color: '#f56c6c' }
        }
      ]
    }
  } catch (error) {
    console.error('加载货流数据失败:', error)
    flowData.value = []
  } finally {
    loading.value = false
  }
}

// 导出全部数据到 CSV
async function handleExportTable() {
  loading.value = true
  ElMessage.info('正在导出全部数据，请稍候...')

  try {
    // 构建查询参数（与 loadTableData 相同）
    const params = {
      // 基础筛选（对齐后端 API 参数名）
      region: filterStore.sales.region,
      manager: filterStore.sales.manager,
      customer: filterStore.sales.customer,
      channel: filterStore.sales.channel,
      // 单据日期筛选
      doc_date_from: filterStore.sales.docDateRange?.[0] || null,
      doc_date_to: filterStore.sales.docDateRange?.[1] || null,
      // 审核日期筛选（后端用 date_from/date_to）
      date_from: filterStore.sales.auditDateRange?.[0] || null,
      date_to: filterStore.sales.auditDateRange?.[1] || null,
      // 商品属性筛选（对齐源程序）
      category: filterStore.sales.category,
      abc_class: filterStore.sales.abcClass,
      lifecycle_status: filterStore.sales.lifecycleStatus,
      custom_flag: filterStore.sales.customFlag,
      promoted_flag: filterStore.sales.promotedFlag,
      material_code: filterStore.sales.materialCode,
      material_name: filterStore.sales.materialName,
      page: 1,
      page_size: 1000
    }

    // 获取所有分页数据
    let allData = []
    let totalRecords = 0

    while (true) {
      const response = await getSalesTable(params)
      const pageData = response.data?.data || response.data || []

      if (params.page === 1) {
        totalRecords = response.data?.total || pageData.length || 0
      }

      allData = allData.concat(pageData)

      if (allData.length >= totalRecords || pageData.length === 0) {
        break
      }

      params.page++
    }

    // 生成 CSV
    const headers = tableColumns.map(col => escapeCSV(col.label || col.prop))
    const headerRow = headers.join(',')

    const rows = allData.map(row => {
      return tableColumns.map(col => {
        let value = row[col.prop]
        if (col.formatter && typeof col.formatter === 'function') {
          value = col.formatter(row, col, value, row[col.prop])
        }
        if (value === null || value === undefined) {
          value = ''
        } else {
          value = String(value)
        }
        return escapeCSV(value)
      }).join(',')
    })

    const BOM = '﻿'
    const csvContent = BOM + headerRow + '\n' + rows.join('\n')

    // 下载文件
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `销售宽表_${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(link.href)

    ElMessage.success(`导出成功，共 ${allData.length} 条数据`)
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  } finally {
    loading.value = false
  }
}

// CSV 转义
function escapeCSV(value) {
  const str = String(value)
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    return '"' + str.replace(/"/g, '""') + '"'
  }
  return str
}

// 重置销售宽表筛选器
function resetSalesFilters() {
  filterStore.resetSales()
  loadTableData()
}

// 销售宽表-大区变更
function handleSalesRegionChange() {
  filterStore.sales.manager = null
  filterStore.sales.customer = null
}

// 销售宽表-客户经理变更
function handleSalesManagerChange() {
  filterStore.sales.customer = null
}

// 重置仪表盘筛选器
function resetDashboardFilters() {
  filterStore.resetDashboard()
  loadDashboardCharts()
}

// 重置销售明细筛选器
function resetSalesDetailFilters() {
  filterStore.resetSalesDetail()
  loadDetailData()
}

function handleExportDetail() {
  ElMessage.info('导出销售明细')
}

// 监听 Tab 切换
watch(activeTab, (newTab) => {
  if (newTab === 'table') {
    loadTableData()
  } else if (newTab === 'dashboard') {
    loadDashboardCharts()
  } else if (newTab === 'indicator') {
    loadIndicatorData()
  } else if (newTab === 'detail') {
    loadDetailData()
  } else if (newTab === 'flow') {
    // 加载货流分析所需的客户选项
    filterStore.fetchCustomers()
    loadFlowData()
  }
})

// 监听销售明细子Tab切换，重新加载数据
watch(detailActiveTab, () => {
  if (activeTab.value === 'detail') {
    loadDetailData()
    // 触发 ECharts resize（tab 切换后 DOM 可能需要时间渲染）
    setTimeout(() => {
      if (detailActiveTab.value === 'productRanking' && productRankingChartRef.value) {
        productRankingChartRef.value.resize()
      } else if (detailActiveTab.value === 'regionCustomer' && regionCustomerChartRef.value) {
        regionCustomerChartRef.value.resize()
      }
    }, 300)
  }
})

// 初始加载
onMounted(async () => {
  // 加载筛选器选项
  await filterStore.fetchAllOptions()
  loadTableData()
})
</script>

<style scoped>
.sales-analysis {
  padding: 20px;
}

.main-tabs {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
}

.tab-content {
  padding: 16px 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.dashboard-card {
  background-color: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
}

.chart-card {
  min-height: 350px;
}

.chart-card h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

/* 表格表头加粗居中 */
:deep(.el-table__header th) {
  font-weight: bold !important;
  text-align: center !important;
}

.span-2 {
  grid-column: span 2;
}

.flow-filter {
  margin-bottom: 16px;
  padding: 12px 16px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.filter-form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-form-actions {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.more-filters {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #dcdfe6;
}

/* 汇总行样式 - 对齐源程序 */
.summary-row {
  display: flex;
  flex-wrap: nowrap;
  gap: 12px;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 12px;
  white-space: nowrap;
  overflow-x: auto;
}

.summary-item {
  color: #606266;
}

.summary-item strong {
  color: #303133;
}

/* 对齐源程序的图表和表格样式 */
.section-title-main {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 24px 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.chart-section {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 16px;
  min-height: 350px;
  width: 100%;
  box-sizing: border-box;
}

.table-section {
  margin-bottom: 24px;
}

.table-section :deep(.el-table) {
  font-size: 12px;
}

.table-section :deep(.el-table__header) {
  font-weight: 600;
}

/* 进度条样式 */
.el-progress {
  width: 100%;
}

/* 指标达成汇总行 - 对齐源程序 */
.indicator-summary {
  margin-top: 16px;
  padding: 12px 16px;
  background-color: #e0f7e0;
  border-radius: 4px;
  font-weight: bold;
  color: #303133;
}

/* TOP30表格子文本样式 - 对齐源程序 */
.top30-table .mat-name {
  font-weight: 600;
  font-size: 13px;
  color: #333;
  margin-bottom: 2px;
}
.top30-table .mat-code {
  font-size: 11px;
  color: #999;
}
.top30-table .abs-val {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}
.top30-table .yoy-val {
  font-size: 11px;
  margin-top: 2px;
}
.sub-text {
  font-size: 11px;
  margin-top: 2px;
}
</style>
