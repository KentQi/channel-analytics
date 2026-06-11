<template>
  <div class="data-management">
    <div class="page-header">
      <h2>信息维护</h2>
      <p class="page-desc">管理商品属性、客户信息、业务指标、自营品牌、渠道客户设定等主数据</p>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs" @tab-change="onTabChange">

      <!-- ==================== Tab 1: 商品属性 ==================== -->
      <el-tab-pane label="商品属性" name="productAttrs">
        <div class="tab-content">
          <div class="action-bar">
            <el-input
              v-model="productAttrs.search"
              placeholder="搜索物料编码/名称"
              clearable
              style="width: 260px"
              @keyup.enter="loadProductAttrs"
              @clear="loadProductAttrs"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-button type="primary" :icon="Plus" @click="openProductAttrDialog(null)">新增</el-button>
            <el-upload
              ref="productAttrUploadRef"
              :auto-upload="false"
              :show-file-list="false"
              accept=".xlsx,.xls"
              :on-change="onProductAttrImport"
            >
              <el-button :icon="Upload">导入 Excel</el-button>
            </el-upload>
            <el-button :icon="Download" @click="handleDownloadTemplate('productAttr')">下载模板</el-button>
            <el-button :icon="Refresh" @click="loadProductAttrs">刷新</el-button>
            <el-button type="warning" :loading="batchLoading.firstStock" @click="handleUpdateFirstStockDate">
              批量更新首批入库时间
            </el-button>
            <el-button type="warning" :loading="batchLoading.lifecycle" @click="handleUpdateLifecycleStatus">
              批量更新商品状态
            </el-button>
          </div>

          <el-table :data="productAttrs.list" v-loading="loading.productAttrs" stripe border>
            <el-table-column prop="material_code" label="物料编码" width="130" />
            <el-table-column prop="material_name" label="商品名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="category" label="品类" width="100" />
            <el-table-column prop="first_stock_in_date" label="首批入库时间" width="130" />
            <el-table-column prop="abc_class" label="ABC分类" width="100" />
            <el-table-column prop="lifecycle_status" label="生命周期状态" width="120" />
            <el-table-column prop="custom_flag" label="定制标志" width="90" align="center">
              <template #default="{ row }">{{ row.custom_flag ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column prop="promoted_flag" label="推广标志" width="90" align="center">
              <template #default="{ row }">{{ row.promoted_flag ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openProductAttrDialog(row)">编辑</el-button>
                <el-button type="danger" link size="small" @click="handleDeleteProductAttr(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="productAttrs.total > PAGE_SIZE"
            class="pagination"
            :current-page="productAttrs.page"
            :page-size="PAGE_SIZE"
            :total="productAttrs.total"
            layout="total, prev, pager, next, jumper"
            @current-change="onProductAttrsPageChange"
          />
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 2: 客户信息 ==================== -->
      <el-tab-pane label="客户信息" name="customerInfo">
        <div class="tab-content">
          <div class="action-bar">
            <el-input
              v-model="customerInfo.search"
              placeholder="搜索客户名称"
              clearable
              style="width: 260px"
              @keyup.enter="loadCustomerInfo"
              @clear="loadCustomerInfo"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-button type="primary" :icon="Plus" @click="openCustomerDialog(null)">新增</el-button>
            <el-upload
              ref="customerUploadRef"
              :auto-upload="false"
              :show-file-list="false"
              accept=".xlsx,.xls"
              :on-change="onCustomerImport"
            >
              <el-button :icon="Upload">导入 Excel</el-button>
            </el-upload>
            <el-button :icon="Download" @click="handleDownloadTemplate('customer')">下载模板</el-button>
            <el-button :icon="Refresh" @click="loadCustomerInfo">刷新</el-button>
          </div>

          <el-table :data="customerInfo.list" v-loading="loading.customerInfo" stripe border>
            <el-table-column prop="customer_name" label="客户名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="region" label="大区" width="90" />
            <el-table-column prop="province" label="省份" width="90" />
            <el-table-column prop="sales_area" label="销售区域" width="100" />
            <el-table-column prop="channel" label="渠道" width="80" />
            <el-table-column prop="cooperation_status" label="合作状态" width="100" />
            <el-table-column prop="account_manager" label="客户经理" width="100" />
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openCustomerDialog(row)">编辑</el-button>
                <el-button type="danger" link size="small" @click="handleDeleteCustomer(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="customerInfo.total > PAGE_SIZE"
            class="pagination"
            :current-page="customerInfo.page"
            :page-size="PAGE_SIZE"
            :total="customerInfo.total"
            layout="total, prev, pager, next, jumper"
            @current-change="onCustomerInfoPageChange"
          />
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 3: 业务指标-省区 ==================== -->
      <el-tab-pane label="业务指标-省区" name="regionIndicators">
        <div class="tab-content">
          <div class="action-bar">
            <el-input
              v-model="regionIndicators.search"
              placeholder="搜索大区/省份/销售区域"
              clearable
              style="width: 260px"
              @keyup.enter="loadRegionIndicators"
              @clear="loadRegionIndicators"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-upload
              ref="regionUploadRef"
              :auto-upload="false"
              :show-file-list="false"
              accept=".xlsx,.xls"
              :on-change="onRegionIndicatorImport"
            >
              <el-button :icon="Upload">导入 Excel</el-button>
            </el-upload>
            <el-button :icon="Download" @click="handleDownloadTemplate('region_indicator')">下载模板</el-button>
            <el-button :icon="Refresh" @click="loadRegionIndicators">刷新</el-button>
          </div>

          <el-table :data="regionIndicators.list" v-loading="loading.regionIndicators" stripe border>
            <el-table-column prop="period" label="期间" width="100" />
            <el-table-column prop="region" label="大区" width="90" />
            <el-table-column prop="province" label="省份" width="90" />
            <el-table-column prop="sales_area" label="销售区域" width="110" />
            <el-table-column prop="manager" label="负责人" width="100" />
            <el-table-column prop="monthly_target" label="月度目标" width="120" align="right">
              <template #default="{ row }">{{ formatNumber(row.monthly_target) }}</template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="regionIndicators.total > PAGE_SIZE"
            class="pagination"
            :current-page="regionIndicators.page"
            :page-size="PAGE_SIZE"
            :total="regionIndicators.total"
            layout="total, prev, pager, next, jumper"
            @current-change="onRegionIndicatorsPageChange"
          />
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 4: 业务指标-客户 ==================== -->
      <el-tab-pane label="业务指标-客户" name="customerIndicators">
        <div class="tab-content">
          <div class="action-bar">
            <el-input
              v-model="customerIndicators.search"
              placeholder="搜索客户名称/大区/省份"
              clearable
              style="width: 260px"
              @keyup.enter="loadCustomerIndicators"
              @clear="loadCustomerIndicators"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-upload
              ref="customerIndUploadRef"
              :auto-upload="false"
              :show-file-list="false"
              accept=".xlsx,.xls"
              :on-change="onCustomerIndicatorImport"
            >
              <el-button :icon="Upload">导入 Excel</el-button>
            </el-upload>
            <el-button :icon="Download" @click="handleDownloadTemplate('customer_indicator')">下载模板</el-button>
            <el-button :icon="Refresh" @click="loadCustomerIndicators">刷新</el-button>
          </div>

          <el-table :data="customerIndicators.list" v-loading="loading.customerIndicators" stripe border>
            <el-table-column prop="period" label="期间" width="100" />
            <el-table-column prop="region" label="大区" width="90" />
            <el-table-column prop="province" label="省份" width="90" />
            <el-table-column prop="sales_area" label="销售区域" width="110" />
            <el-table-column prop="manager" label="负责人" width="100" />
            <el-table-column prop="customer_name" label="客户名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="monthly_target" label="月度目标" width="120" align="right">
              <template #default="{ row }">{{ formatNumber(row.monthly_target) }}</template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="customerIndicators.total > PAGE_SIZE"
            class="pagination"
            :current-page="customerIndicators.page"
            :page-size="PAGE_SIZE"
            :total="customerIndicators.total"
            layout="total, prev, pager, next, jumper"
            @current-change="onCustomerIndicatorsPageChange"
          />
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 5: 自营品牌资料 ==================== -->
      <el-tab-pane label="自营品牌资料" name="selfBrands">
        <div class="tab-content">
          <div class="action-bar">
            <el-button type="primary" :icon="Plus" @click="openBrandDialog(null)">新增</el-button>
            <el-upload
              ref="brandUploadRef"
              :auto-upload="false"
              :show-file-list="false"
              accept=".xlsx,.xls"
              :on-change="onBrandImport"
            >
              <el-button :icon="Upload">导入 Excel</el-button>
            </el-upload>
            <el-button :icon="Download" @click="handleDownloadTemplate('self_operated_brand')">下载模板</el-button>
            <el-button :icon="Refresh" @click="loadSelfBrands">刷新</el-button>
          </div>

          <el-table :data="selfBrands.list" v-loading="loading.selfBrands" stripe border>
            <el-table-column prop="brand_name" label="品牌名称" min-width="200" />
            <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openBrandDialog(row)">编辑</el-button>
                <el-button type="danger" link size="small" @click="handleDeleteBrand(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 6: 渠道客户设定 ==================== -->
      <el-tab-pane label="渠道客户设定" name="channelCustomer">
        <div class="tab-content">
          <div class="action-bar">
            <el-button :icon="Refresh" @click="loadChannelCustomerConfig">刷新</el-button>
          </div>

          <el-form label-width="140px" class="channel-customer-form">
            <el-form-item label="客户分类">
              <el-select
                v-model="channelConfig.selectedClasses"
                multiple
                collapse-tags
                collapse-tags-tooltip
                placeholder="请选择客户分类"
                style="width: 100%"
                :loading="loading.customerClasses"
                @change="onClassChange"
              >
                <el-option v-for="cls in channelConfig.classes" :key="cls" :label="cls" :value="cls" />
              </el-select>
            </el-form-item>

            <el-form-item label="客户">
              <el-select
                v-model="channelConfig.selectedCustomers"
                multiple
                collapse-tags
                collapse-tags-tooltip
                placeholder="请先选择客户分类"
                style="width: 100%"
                :loading="loading.customersByClass"
                :disabled="!channelConfig.selectedClasses.length"
              >
                <el-option
                  v-for="c in channelConfig.filteredCustomers"
                  :key="c"
                  :label="c"
                  :value="c"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="新客户定义">
              <div class="new-customer-row">
                <span>最近</span>
                <el-input-number
                  v-model="channelConfig.newCustomerDays"
                  :min="1"
                  :max="365"
                  controls-position="right"
                  style="width: 140px"
                />
                <span>天内首次进货的客户</span>
                <el-button
                  type="primary"
                  size="small"
                  style="margin-left: 12px"
                  :loading="saving.newCustomerDays"
                  @click="saveNewCustomerDays"
                >
                  保存
                </el-button>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="saving.channelCustomer" @click="saveChannelCustomer">
                保存渠道客户设定
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ========== 商品属性 编辑对话框 ========== -->
    <el-dialog
      v-model="dialogs.productAttr.visible"
      :title="dialogs.productAttr.isEdit ? '编辑商品属性' : '新增商品属性'"
      width="600px"
      destroy-on-close
    >
      <el-form
        ref="productAttrFormRef"
        :model="dialogs.productAttr.form"
        :rules="productAttrRules"
        label-width="120px"
      >
        <el-form-item label="物料编码" prop="material_code">
          <el-input
            v-model="dialogs.productAttr.form.material_code"
            :disabled="dialogs.productAttr.isEdit"
            placeholder="请输入物料编码"
          />
        </el-form-item>
        <el-form-item label="商品名称" prop="material_name">
          <el-input v-model="dialogs.productAttr.form.material_name" placeholder="由 ETL 自动同步" disabled />
        </el-form-item>
        <el-form-item label="品类">
          <el-input v-model="dialogs.productAttr.form.category" placeholder="由 ETL 自动同步" disabled />
        </el-form-item>
        <el-form-item label="首批入库时间">
          <el-date-picker
            v-model="dialogs.productAttr.form.first_stock_in_date"
            type="date"
            value-format="YYYY/MM/DD"
            placeholder="由 ETL 自动同步"
            style="width: 100%"
            disabled
          />
        </el-form-item>
        <el-form-item label="ABC分类">
          <el-select v-model="dialogs.productAttr.form.abc_class" placeholder="请选择" style="width: 100%">
            <el-option label="引流品" value="引流品" />
            <el-option label="主推品" value="主推品" />
            <el-option label="利润品" value="利润品" />
          </el-select>
        </el-form-item>
        <el-form-item label="生命周期状态">
          <el-select v-model="dialogs.productAttr.form.lifecycle_status" placeholder="请选择" style="width: 100%">
            <el-option label="新品" value="新品" />
            <el-option label="持续销售" value="持续销售" />
            <el-option label="售完即止" value="售完即止" />
            <el-option label="重新上架" value="重新上架" />
            <el-option label="淘汰" value="淘汰" />
          </el-select>
        </el-form-item>
        <el-form-item label="定制标志">
          <el-switch v-model="dialogs.productAttr.form.custom_flag" />
        </el-form-item>
        <el-form-item label="推广标志">
          <el-switch v-model="dialogs.productAttr.form.promoted_flag" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogs.productAttr.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving.productAttr" @click="saveProductAttr">保存</el-button>
      </template>
    </el-dialog>

    <!-- ========== 客户信息 编辑对话框 ========== -->
    <el-dialog
      v-model="dialogs.customer.visible"
      :title="dialogs.customer.isEdit ? '编辑客户' : '新增客户'"
      width="600px"
      destroy-on-close
    >
      <el-form
        ref="customerFormRef"
        :model="dialogs.customer.form"
        :rules="customerRules"
        label-width="100px"
      >
        <el-form-item label="客户名称" prop="customer_name">
          <el-input
            v-model="dialogs.customer.form.customer_name"
            :disabled="dialogs.customer.isEdit"
            placeholder="请输入客户名称"
          />
        </el-form-item>
        <el-form-item label="大区">
          <el-input v-model="dialogs.customer.form.region" placeholder="请输入大区" />
        </el-form-item>
        <el-form-item label="省份">
          <el-input v-model="dialogs.customer.form.province" placeholder="请输入省份" />
        </el-form-item>
        <el-form-item label="销售区域">
          <el-input v-model="dialogs.customer.form.sales_area" placeholder="请输入销售区域" />
        </el-form-item>
        <el-form-item label="渠道">
          <el-select v-model="dialogs.customer.form.channel" placeholder="请选择渠道" style="width: 100%">
            <el-option label="批发" value="批发" />
            <el-option label="零售" value="零售" />
            <el-option label="电商" value="电商" />
            <el-option label="直营" value="直营" />
          </el-select>
        </el-form-item>
        <el-form-item label="合作状态">
          <el-select v-model="dialogs.customer.form.cooperation_status" placeholder="请选择合作状态" style="width: 100%">
            <el-option label="合作中" value="合作中" />
            <el-option label="已暂停" value="已暂停" />
            <el-option label="已终止" value="已终止" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户经理">
          <el-input v-model="dialogs.customer.form.account_manager" placeholder="请输入客户经理" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogs.customer.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving.customer" @click="saveCustomer">保存</el-button>
      </template>
    </el-dialog>

    <!-- ========== 自营品牌 编辑对话框 ========== -->
    <el-dialog
      v-model="dialogs.brand.visible"
      :title="dialogs.brand.form.id ? '编辑品牌' : '新增品牌'"
      width="500px"
      destroy-on-close
    >
      <el-form
        ref="brandFormRef"
        :model="dialogs.brand.form"
        :rules="brandRules"
        label-width="100px"
      >
        <el-form-item label="品牌名称" prop="brand_name">
          <el-input v-model="dialogs.brand.form.brand_name" placeholder="请输入品牌名称" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="dialogs.brand.form.remark" type="textarea" :rows="3" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogs.brand.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving.brand" @click="saveBrand">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Download, Refresh, Search } from '@element-plus/icons-vue'
import {
  getProductAttrs, updateProductAttr, importProductAttrs,
  downloadProductAttrsTemplate, updateFirstStockDate, updateLifecycleStatus,
  getCustomers, updateCustomer, importCustomers, downloadCustomersTemplate,
  getRegionIndicators, importRegionIndicators, downloadRegionIndicatorsTemplate,
  getCustomerIndicators, importCustomerIndicators, downloadCustomerIndicatorsTemplate,
  getFilterConfig, saveFilterConfig,
  getSelfOperatedBrands, updateSelfOperatedBrand, importSelfOperatedBrands,
  downloadSelfOperatedBrandsTemplate,
  getCustomerClasses, getCustomersByClass,
} from '@/api/data'

// ==================== 常量 ====================
const PAGE_SIZE = 15

// ==================== 响应式状态 ====================
const activeTab = ref('productAttrs')

// 分 tab 的 loading 状态
const loading = reactive({
  productAttrs: false,
  customerInfo: false,
  regionIndicators: false,
  customerIndicators: false,
  selfBrands: false,
  customerClasses: false,
  customersByClass: false,
})

// 分操作的 saving 状态
const saving = reactive({
  productAttr: false,
  customer: false,
  brand: false,
  channelCustomer: false,
  newCustomerDays: false,
})

// 批量操作 loading
const batchLoading = reactive({ firstStock: false, lifecycle: false })

// ==================== Tab 1: 商品属性 ====================
const productAttrs = reactive({ list: [], page: 1, total: 0, search: '' })

const dialogs = reactive({
  productAttr: {
    visible: false,
    isEdit: false,
    form: {
      material_code: '', material_name: '', category: '',
      first_stock_in_date: '', abc_class: '', lifecycle_status: '',
      custom_flag: false, promoted_flag: false,
    },
  },
  customer: {
    visible: false,
    isEdit: false,
    form: {
      customer_name: '', region: '', province: '', sales_area: '',
      channel: '', cooperation_status: '', account_manager: '',
    },
  },
  brand: {
    visible: false,
    form: { id: null, brand_name: '', remark: '' },
  },
})

const productAttrFormRef = ref(null)
const productAttrRules = {
  material_code: [{ required: true, message: '请输入物料编码', trigger: 'blur' }],
  material_name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
}

async function loadProductAttrs() {
  loading.productAttrs = true
  try {
    const res = await getProductAttrs({
      page: productAttrs.page,
      page_size: PAGE_SIZE,
      search: productAttrs.search || undefined,
    })
    const data = res.data || {}
    productAttrs.list = data.items || []
    productAttrs.total = data.total || 0
  } catch (e) {
    console.error('加载商品属性失败:', e)
  } finally {
    loading.productAttrs = false
  }
}

function onProductAttrsPageChange(page) {
  productAttrs.page = page
  loadProductAttrs()
}

function openProductAttrDialog(row) {
  if (row) {
    dialogs.productAttr.isEdit = true
    Object.assign(dialogs.productAttr.form, {
      material_code: row.material_code,
      material_name: row.material_name || '',
      category: row.category || '',
      first_stock_in_date: row.first_stock_in_date || '',
      abc_class: row.abc_class || '',
      lifecycle_status: row.lifecycle_status || '',
      custom_flag: !!row.custom_flag,
      promoted_flag: !!row.promoted_flag,
    })
  } else {
    dialogs.productAttr.isEdit = false
    Object.assign(dialogs.productAttr.form, {
      material_code: '', material_name: '', category: '',
      first_stock_in_date: '', abc_class: '', lifecycle_status: '',
      custom_flag: false, promoted_flag: false,
    })
  }
  dialogs.productAttr.visible = true
}

async function saveProductAttr() {
  const valid = await productAttrFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.productAttr = true
  try {
    const f = dialogs.productAttr.form
    await updateProductAttr(f.material_code, {
      material_name: f.material_name,
      category: f.category,
      first_stock_in_date: f.first_stock_in_date,
      abc_class: f.abc_class,
      lifecycle_status: f.lifecycle_status,
      custom_flag: f.custom_flag,
      promoted_flag: f.promoted_flag,
    })
    ElMessage.success('保存成功')
    dialogs.productAttr.visible = false
    loadProductAttrs()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.productAttr = false
  }
}

async function handleDeleteProductAttr(row) {
  await ElMessageBox.confirm(
    `确定要删除商品 "${row.material_name || row.material_code}" 吗？`,
    '提示',
    { type: 'warning' }
  )
  try {
    await updateProductAttr(row.material_code, { lifecycle_status: '淘汰' })
    ElMessage.success('删除成功')
    loadProductAttrs()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function handleUpdateFirstStockDate() {
  batchLoading.firstStock = true
  try {
    const res = await updateFirstStockDate()
    ElMessage.success(`已更新 ${res.data?.updated || 0} 条记录`)
    loadProductAttrs()
  } catch (e) {
    ElMessage.error('更新失败')
  } finally {
    batchLoading.firstStock = false
  }
}

async function handleUpdateLifecycleStatus() {
  batchLoading.lifecycle = true
  try {
    const res = await updateLifecycleStatus()
    ElMessage.success(`已更新 ${res.data?.updated || 0} 条记录`)
    loadProductAttrs()
  } catch (e) {
    ElMessage.error('更新失败')
  } finally {
    batchLoading.lifecycle = false
  }
}

async function onProductAttrImport(file) {
  await doImport(importProductAttrs, file, loadProductAttrs)
}

// ==================== Tab 2: 客户信息 ====================
const customerInfo = reactive({ list: [], page: 1, total: 0, search: '' })
const customerFormRef = ref(null)
const customerRules = {
  customer_name: [{ required: true, message: '请输入客户名称', trigger: 'blur' }],
}

async function loadCustomerInfo() {
  loading.customerInfo = true
  try {
    const res = await getCustomers({
      page: customerInfo.page,
      page_size: PAGE_SIZE,
      search: customerInfo.search || undefined,
    })
    const data = res.data || {}
    customerInfo.list = data.items || []
    customerInfo.total = data.total || 0
  } catch (e) {
    console.error('加载客户信息失败:', e)
  } finally {
    loading.customerInfo = false
  }
}

function onCustomerInfoPageChange(page) {
  customerInfo.page = page
  loadCustomerInfo()
}

function openCustomerDialog(row) {
  if (row) {
    dialogs.customer.isEdit = true
    Object.assign(dialogs.customer.form, {
      customer_name: row.customer_name,
      region: row.region || '',
      province: row.province || '',
      sales_area: row.sales_area || '',
      channel: row.channel || '',
      cooperation_status: row.cooperation_status || '',
      account_manager: row.account_manager || '',
    })
  } else {
    dialogs.customer.isEdit = false
    Object.assign(dialogs.customer.form, {
      customer_name: '', region: '', province: '', sales_area: '',
      channel: '', cooperation_status: '', account_manager: '',
    })
  }
  dialogs.customer.visible = true
}

async function saveCustomer() {
  const valid = await customerFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.customer = true
  try {
    const f = dialogs.customer.form
    const { customer_name, ...data } = f
    await updateCustomer(customer_name, data)
    ElMessage.success('保存成功')
    dialogs.customer.visible = false
    loadCustomerInfo()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.customer = false
  }
}

async function handleDeleteCustomer(row) {
  await ElMessageBox.confirm(
    `确定要删除客户 "${row.customer_name}" 吗？`,
    '提示',
    { type: 'warning' }
  )
  try {
    await updateCustomer(row.customer_name, { cooperation_status: '已终止' })
    ElMessage.success('删除成功')
    loadCustomerInfo()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function onCustomerImport(file) {
  await doImport(importCustomers, file, loadCustomerInfo)
}

// ==================== Tab 3: 业务指标-省区 ====================
const regionIndicators = reactive({ list: [], page: 1, total: 0, search: '' })

async function loadRegionIndicators() {
  loading.regionIndicators = true
  try {
    const res = await getRegionIndicators({
      page: regionIndicators.page,
      page_size: PAGE_SIZE,
      search: regionIndicators.search || undefined,
    })
    const data = res.data || {}
    regionIndicators.list = data.items || []
    regionIndicators.total = data.total || 0
  } catch (e) {
    console.error('加载省区指标失败:', e)
  } finally {
    loading.regionIndicators = false
  }
}

function onRegionIndicatorsPageChange(page) {
  regionIndicators.page = page
  loadRegionIndicators()
}

async function onRegionIndicatorImport(file) {
  await doImport(importRegionIndicators, file, loadRegionIndicators)
}

// ==================== Tab 4: 业务指标-客户 ====================
const customerIndicators = reactive({ list: [], page: 1, total: 0, search: '' })

async function loadCustomerIndicators() {
  loading.customerIndicators = true
  try {
    const res = await getCustomerIndicators({
      page: customerIndicators.page,
      page_size: PAGE_SIZE,
      search: customerIndicators.search || undefined,
    })
    const data = res.data || {}
    customerIndicators.list = data.items || []
    customerIndicators.total = data.total || 0
  } catch (e) {
    console.error('加载客户指标失败:', e)
  } finally {
    loading.customerIndicators = false
  }
}

function onCustomerIndicatorsPageChange(page) {
  customerIndicators.page = page
  loadCustomerIndicators()
}

async function onCustomerIndicatorImport(file) {
  await doImport(importCustomerIndicators, file, loadCustomerIndicators)
}

// ==================== Tab 5: 自营品牌资料 ====================
const selfBrands = reactive({ list: [] })
const brandFormRef = ref(null)
const brandRules = {
  brand_name: [{ required: true, message: '请输入品牌名称', trigger: 'blur' }],
}

async function loadSelfBrands() {
  loading.selfBrands = true
  try {
    const res = await getSelfOperatedBrands({ page_size: 1000 })
    const data = res.data || {}
    selfBrands.list = data.items || []
  } catch (e) {
    console.error('加载自营品牌失败:', e)
  } finally {
    loading.selfBrands = false
  }
}

function openBrandDialog(row) {
  if (row) {
    Object.assign(dialogs.brand.form, {
      id: row.id,
      brand_name: row.brand_name,
      remark: row.remark || '',
    })
  } else {
    Object.assign(dialogs.brand.form, { id: null, brand_name: '', remark: '' })
  }
  dialogs.brand.visible = true
}

async function saveBrand() {
  const valid = await brandFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.brand = true
  try {
    const f = dialogs.brand.form
    await updateSelfOperatedBrand(f.id, { brand_name: f.brand_name, remark: f.remark })
    ElMessage.success('保存成功')
    dialogs.brand.visible = false
    loadSelfBrands()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.brand = false
  }
}

async function handleDeleteBrand(row) {
  await ElMessageBox.confirm(
    `确定要删除品牌 "${row.brand_name}" 吗？`,
    '提示',
    { type: 'warning' }
  )
  try {
    await updateSelfOperatedBrand(row.id, { brand_name: row.brand_name, remark: '[已删除]' })
    ElMessage.success('删除成功')
    loadSelfBrands()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function onBrandImport(file) {
  await doImport(importSelfOperatedBrands, file, loadSelfBrands)
}

// ==================== Tab 6: 渠道客户设定 ====================
const channelConfig = reactive({
  classes: [],
  selectedClasses: [],
  filteredCustomers: [],
  selectedCustomers: [],
  newCustomerDays: 90,
})

async function loadChannelCustomerConfig() {
  loading.customerClasses = true
  try {
    const clsRes = await getCustomerClasses()
    channelConfig.classes = clsRes.data?.items || clsRes.data || []

    const classConfig = await getFilterConfig('customer_class')
    channelConfig.selectedClasses = classConfig.data?.values || []

    if (channelConfig.selectedClasses.length) {
      await onClassChange(channelConfig.selectedClasses)
    }

    const customerConfig = await getFilterConfig('customer')
    channelConfig.selectedCustomers = customerConfig.data?.values || []

    const daysConfig = await getFilterConfig('new_customer_days')
    const daysArr = daysConfig.data?.values || []
    if (daysArr.length) {
      const d = parseInt(daysArr[0])
      if (!isNaN(d)) channelConfig.newCustomerDays = d
    }
  } catch (e) {
    console.error('加载渠道客户设定失败:', e)
  } finally {
    loading.customerClasses = false
  }
}

async function onClassChange(classes) {
  if (!classes?.length) {
    channelConfig.filteredCustomers = []
    return
  }
  loading.customersByClass = true
  try {
    const res = await getCustomersByClass(classes)
    const items = res.data?.items || []
    channelConfig.filteredCustomers = items.map(i => i.customer || i)
    // 过滤掉已不在可选项中的已选客户
    channelConfig.selectedCustomers = channelConfig.selectedCustomers.filter(
      c => channelConfig.filteredCustomers.includes(c)
    )
  } catch (e) {
    console.error('获取客户列表失败:', e)
  } finally {
    loading.customersByClass = false
  }
}

async function saveChannelCustomer() {
  saving.channelCustomer = true
  try {
    await saveFilterConfig('customer_class', channelConfig.selectedClasses)
    await saveFilterConfig('customer', channelConfig.selectedCustomers)
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.channelCustomer = false
  }
}

async function saveNewCustomerDays() {
  saving.newCustomerDays = true
  try {
    await saveFilterConfig('new_customer_days', [String(channelConfig.newCustomerDays)])
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.newCustomerDays = false
  }
}

// ==================== 通用方法 ====================

/** 通用导入处理（el-upload on-change 回调） */
async function doImport(importFn, file, reloadFn) {
  const rawFile = file.raw || file
  if (!rawFile.name.match(/\.(xlsx|xls)$/)) {
    ElMessage.error('仅支持 Excel 文件 (.xlsx/.xls)')
    return
  }
  const tabKey = getTabKeyForReload(reloadFn)
  if (tabKey) loading[tabKey] = true
  try {
    const res = await importFn(rawFile)
    const data = res.data || {}
    ElMessage.success(`导入完成: 成功 ${data.success || 0}, 失败 ${data.error || 0}`)
    reloadFn()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    if (tabKey) loading[tabKey] = false
  }
}

function getTabKeyForReload(fn) {
  if (fn === loadProductAttrs) return 'productAttrs'
  if (fn === loadCustomerInfo) return 'customerInfo'
  if (fn === loadRegionIndicators) return 'regionIndicators'
  if (fn === loadCustomerIndicators) return 'customerIndicators'
  if (fn === loadSelfBrands) return 'selfBrands'
  return null
}

/** 下载模板 */
const TEMPLATE_MAP = {
  productAttr: downloadProductAttrsTemplate,
  customer: downloadCustomersTemplate,
  region_indicator: downloadRegionIndicatorsTemplate,
  customer_indicator: downloadCustomerIndicatorsTemplate,
  self_operated_brand: downloadSelfOperatedBrandsTemplate,
}

async function handleDownloadTemplate(key) {
  const fn = TEMPLATE_MAP[key]
  if (!fn) return
  try {
    const res = await fn()
    const columns = res.data?.columns || []
    if (columns.length) {
      ElMessage.info(`模板列: ${columns.join(', ')}`)
    }
  } catch (e) {
    ElMessage.error('下载模板失败')
  }
}

/** 格式化数字 */
function formatNumber(val) {
  if (val == null) return '0'
  return Number(val).toLocaleString('zh-CN')
}

/** Tab 切换时加载对应数据 */
function onTabChange(tab) {
  const loaderMap = {
    productAttrs: loadProductAttrs,
    customerInfo: loadCustomerInfo,
    regionIndicators: loadRegionIndicators,
    customerIndicators: loadCustomerIndicators,
    selfBrands: loadSelfBrands,
    channelCustomer: loadChannelCustomerConfig,
  }
  loaderMap[tab]?.()
}

onMounted(() => {
  loadProductAttrs()
})
</script>

<style scoped>
.data-management {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

.page-desc {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.main-tabs {
  background-color: #fff;
  border-radius: 4px;
  padding: 16px;
}

.tab-content {
  padding: 16px 0;
}

.action-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.action-bar :deep(.el-upload) {
  display: inline-flex;
}

.channel-customer-form {
  max-width: 700px;
}

.new-customer-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
