<template>
  <div class="permissions-page">
    <div class="page-header">
      <h2>权限配置</h2>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs">
      <!-- Tab 1: 角色权限配置 -->
      <el-tab-pane label="角色权限配置" name="role-permissions">
        <div class="tab-content">
          <div class="role-selector">
            <span class="selector-label">选择角色：</span>
            <el-select
              v-model="selectedRole"
              placeholder="请选择角色"
              style="width: 240px"
              @change="handleRoleChange"
            >
              <el-option
                v-for="role in roleList"
                :key="role.role"
                :label="role.role"
                :value="role.role"
              />
            </el-select>
            <el-button
              type="primary"
              :icon="Check"
              :loading="saving"
              :disabled="!selectedRole"
              style="margin-left: 16px"
              @click="handleSavePermissions"
            >
              保存权限
            </el-button>
          </div>

          <div v-if="selectedRole" class="permission-panels">
            <!-- 导航模块权限 -->
            <div class="permission-panel">
              <div class="panel-header">
                <span class="panel-title">导航模块权限</span>
                <el-checkbox
                  v-model="modulesUnlimited"
                  @change="handleModulesUnlimitedChange"
                >
                  不限制
                </el-checkbox>
              </div>
              <div class="panel-body">
                <el-checkbox-group v-model="permissions.modules" :disabled="modulesUnlimited">
                  <el-checkbox
                    v-for="item in moduleOptions"
                    :key="item.value"
                    :value="item.value"
                  >
                    {{ item.label }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>

            <!-- 销售分析 Tab 权限 -->
            <div class="permission-panel">
              <div class="panel-header">
                <span class="panel-title">销售分析 Tab 权限</span>
                <el-checkbox
                  v-model="salesTabsUnlimited"
                  @change="handleSalesTabsUnlimitedChange"
                >
                  不限制
                </el-checkbox>
              </div>
              <div class="panel-body">
                <el-checkbox-group v-model="permissions.sales_tabs" :disabled="salesTabsUnlimited">
                  <el-checkbox
                    v-for="item in salesTabOptions"
                    :key="item.value"
                    :value="item.value"
                  >
                    {{ item.label }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>

            <!-- 区域查看权限 -->
            <div class="permission-panel">
              <div class="panel-header">
                <span class="panel-title">区域查看权限</span>
                <el-checkbox
                  v-model="regionsUnlimited"
                  @change="handleRegionsUnlimitedChange"
                >
                  不限制
                </el-checkbox>
              </div>
              <div class="panel-body">
                <el-checkbox-group v-model="permissions.regions" :disabled="regionsUnlimited">
                  <el-checkbox
                    v-for="region in regionOptions"
                    :key="region"
                    :value="region"
                  >
                    {{ region }}
                  </el-checkbox>
                </el-checkbox-group>
                <el-empty v-if="regionOptions.length === 0" description="暂无区域数据" :image-size="60" />
              </div>
            </div>
          </div>

          <el-empty v-else description="请先选择一个角色进行权限配置" />
        </div>
      </el-tab-pane>

      <!-- Tab 2: 账号编辑 -->
      <el-tab-pane label="账号编辑" name="users">
        <div class="tab-content">
          <div class="action-bar">
            <el-button type="primary" :icon="Plus" @click="handleAddUser">新增用户</el-button>
            <el-button :icon="Refresh" @click="loadUsers">刷新</el-button>
          </div>
          <DataTable
            :data="userList"
            :columns="userColumns"
            :loading="loading"
            :show-pagination="true"
            :page-size="15"
            stripe
          >
            <template #is_active="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
            <template #role="{ row }">
              <el-tag size="small" type="primary">{{ row.role }}</el-tag>
            </template>
            <template #action="{ row }">
              <el-button type="primary" link size="small" @click="handleEditUser(row)">
                编辑
              </el-button>
              <el-button type="danger" link size="small" @click="handleDeleteUser(row)">
                删除
              </el-button>
            </template>
          </DataTable>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 角色编辑 -->
      <el-tab-pane label="角色编辑" name="roles">
        <div class="tab-content">
          <div class="action-bar">
            <el-button type="primary" :icon="Plus" @click="handleAddRole">新增角色</el-button>
            <el-button :icon="Refresh" @click="loadRoleList">刷新</el-button>
          </div>
          <DataTable
            :data="roleEditList"
            :columns="roleColumns"
            :loading="loading"
            :show-pagination="false"
            stripe
          >
            <template #action="{ row }">
              <el-button
                v-if="row.role !== 'admin'"
                type="primary"
                link
                size="small"
                @click="handleRenameRole(row)"
              >
                重命名
              </el-button>
              <el-button
                v-if="row.role !== 'admin'"
                type="danger"
                link
                size="small"
                @click="handleDeleteRole(row)"
              >
                删除
              </el-button>
            </template>
          </DataTable>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增/编辑用户对话框 -->
    <el-dialog
      v-model="userDialogVisible"
      :title="isEditUser ? '编辑用户' : '新增用户'"
      width="500px"
      destroy-on-close
    >
      <el-form ref="userFormRef" :model="userForm" :rules="userFormRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" placeholder="请输入用户名" :disabled="isEditUser" />
        </el-form-item>
        <el-form-item v-if="!isEditUser" label="密码" prop="password">
          <el-input v-model="userForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="显示名" prop="display_name">
          <el-input v-model="userForm.display_name" placeholder="请输入显示名" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" placeholder="请选择角色" style="width: 100%">
            <el-option
              v-for="r in availableRoleNames"
              :key="r"
              :label="r"
              :value="r"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isEditUser" label="状态" prop="is_active">
          <el-radio-group v-model="userForm.is_active">
            <el-radio :value="true">启用</el-radio>
            <el-radio :value="false">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增角色对话框 -->
    <el-dialog v-model="roleDialogVisible" title="新增角色" width="400px" destroy-on-close>
      <el-form ref="roleFormRef" :model="roleForm" :rules="roleFormRules" label-width="80px">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="roleForm.name" placeholder="请输入角色名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveRole">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重命名角色对话框 -->
    <el-dialog v-model="renameDialogVisible" title="重命名角色" width="400px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="原名称">
          <el-input :model-value="renameOldName" disabled />
        </el-form-item>
        <el-form-item label="新名称">
          <el-input v-model="renameNewName" placeholder="请输入新角色名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleConfirmRename">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Check } from '@element-plus/icons-vue'
import DataTable from '@/components/common/DataTable.vue'
import {
  getRoles,
  getRolePermissions,
  saveRolePermissions,
  createRole,
  deleteRole,
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  getRegions
} from '@/api/permissions'

// ========== 常量选项 ==========
const moduleOptions = [
  { label: '待办事项', value: '待办事项' },
  { label: '数据导入', value: '数据导入' },
  { label: 'ETL执行', value: 'ETL执行' },
  { label: '基础分析', value: '基础分析' },
  { label: '库存分析', value: '库存分析' },
  { label: '销售分析', value: '销售分析' },
  { label: '返单分析', value: '返单分析' },
  { label: '高级分析', value: '高级分析' },
  { label: '预警通知', value: '预警通知' },
  { label: '自定义报表', value: '自定义报表' },
  { label: '信息维护', value: '信息维护' },
  { label: '权限配置', value: '权限配置' },
  { label: '系统日志', value: '系统日志' },
  { label: '修改密码', value: '修改密码' }
]

const salesTabOptions = [
  { label: '销售出库宽表', value: '销售出库宽表' },
  { label: '出货仪表盘', value: '出货仪表盘' },
  { label: '指标达成进度', value: '指标达成进度' },
  { label: '销售出库明细', value: '销售出库明细' },
  { label: '单品货流明细', value: '单品货流明细' }
]

// ========== 状态 ==========
const activeTab = ref('role-permissions')
const loading = ref(false)
const saving = ref(false)

// 角色权限配置
const roleList = ref([])
const selectedRole = ref('')
const regionOptions = ref([])
const modulesUnlimited = ref(false)
const salesTabsUnlimited = ref(false)
const regionsUnlimited = ref(false)
const permissions = reactive({
  modules: [],
  sales_tabs: [],
  regions: []
})

// 用户管理
const userList = ref([])
const userDialogVisible = ref(false)
const isEditUser = ref(false)
const userFormRef = ref(null)
const userForm = reactive({
  id: null,
  username: '',
  password: '',
  display_name: '',
  role: '',
  is_active: true
})
const userFormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

// 角色编辑
const roleEditList = ref([])
const roleDialogVisible = ref(false)
const roleFormRef = ref(null)
const roleForm = reactive({ name: '' })
const roleFormRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }]
}
const renameDialogVisible = ref(false)
const renameOldName = ref('')
const renameNewName = ref('')

// ========== 计算属性 ==========
const availableRoleNames = computed(() => roleList.value.map(r => r.role))

// ========== 表格列定义 ==========
const userColumns = [
  { prop: 'username', label: '用户名', width: 140 },
  { prop: 'display_name', label: '显示名', width: 140 },
  { prop: 'role', label: '角色', width: 120, slot: true },
  { prop: 'is_active', label: '状态', width: 80, slot: true },
  { prop: 'created_at', label: '创建时间', width: 180 }
]

const roleColumns = [
  { prop: 'role', label: '角色名称', minWidth: 200 }
]

// ========== 角色权限配置 ==========
async function loadRoleList() {
  loading.value = true
  try {
    const res = await getRoles()
    roleList.value = res.data || []
    // 同步角色编辑列表
    roleEditList.value = roleList.value.map(r => ({ role: r.role }))
  } catch (e) {
    console.error('加载角色列表失败:', e)
    roleList.value = []
    roleEditList.value = []
  } finally {
    loading.value = false
  }
}

async function loadRegions() {
  try {
    const res = await getRegions()
    regionOptions.value = res.data?.regions || []
  } catch (e) {
    console.error('加载区域列表失败:', e)
    regionOptions.value = []
  }
}

async function handleRoleChange(role) {
  // 重置"不限制"
  modulesUnlimited.value = false
  salesTabsUnlimited.value = false
  regionsUnlimited.value = false

  try {
    const res = await getRolePermissions(role)
    const perms = res.data?.permissions || {}

    if (perms.modules && perms.modules.length === 0 && !perms.sales_tabs && !perms.regions) {
      // 空权限 = 不限制所有
      modulesUnlimited.value = true
      salesTabsUnlimited.value = true
      regionsUnlimited.value = true
      permissions.modules = moduleOptions.map(m => m.value)
      permissions.sales_tabs = salesTabOptions.map(t => t.value)
      permissions.regions = [...regionOptions.value]
    } else {
      // 后端用 null 表示"不限制"该维度（销售 tabs / 区域）
      permissions.modules = perms.modules || []
      permissions.sales_tabs = perms.sales_tabs || []
      permissions.regions = perms.regions || []

      // null = 不限制
      if (perms.sales_tabs === null) {
        salesTabsUnlimited.value = true
        permissions.sales_tabs = salesTabOptions.map(t => t.value)
      } else if (perms.sales_tabs.length === salesTabOptions.length) {
        salesTabsUnlimited.value = true
      }
      if (perms.regions === null) {
        regionsUnlimited.value = true
        permissions.regions = [...regionOptions.value]
      } else if (perms.regions.length === regionOptions.value.length) {
        regionsUnlimited.value = true
      }
      // modules 走 [] 表示不限制，保持原逻辑
      if (perms.modules && perms.modules.length === moduleOptions.length) {
        modulesUnlimited.value = true
      }
    }
  } catch (e) {
    console.error('加载角色权限失败:', e)
    permissions.modules = []
    permissions.sales_tabs = []
    permissions.regions = []
  }
}

function handleModulesUnlimitedChange(val) {
  if (val) {
    permissions.modules = moduleOptions.map(m => m.value)
  } else {
    permissions.modules = []
  }
}

function handleSalesTabsUnlimitedChange(val) {
  if (val) {
    permissions.sales_tabs = salesTabOptions.map(t => t.value)
  } else {
    permissions.sales_tabs = []
  }
}

function handleRegionsUnlimitedChange(val) {
  if (val) {
    permissions.regions = [...regionOptions.value]
  } else {
    permissions.regions = []
  }
}

async function handleSavePermissions() {
  if (!selectedRole.value) return

  saving.value = true
  try {
    const payload = {
      modules: modulesUnlimited.value ? [] : permissions.modules,
      sales_tabs: salesTabsUnlimited.value ? null : permissions.sales_tabs,
      regions: regionsUnlimited.value ? null : permissions.regions
    }
    await saveRolePermissions(selectedRole.value, payload)
    ElMessage.success('权限保存成功')
  } catch (e) {
    console.error('保存权限失败:', e)
  } finally {
    saving.value = false
  }
}

// ========== 用户管理 ==========
async function loadUsers() {
  loading.value = true
  try {
    const res = await getUsers()
    userList.value = res.data?.items || []
  } catch (e) {
    console.error('加载用户列表失败:', e)
    userList.value = []
  } finally {
    loading.value = false
  }
}

function handleAddUser() {
  isEditUser.value = false
  Object.assign(userForm, {
    id: null,
    username: '',
    password: '',
    display_name: '',
    role: '',
    is_active: true
  })
  userDialogVisible.value = true
}

function handleEditUser(row) {
  isEditUser.value = true
  Object.assign(userForm, {
    id: row.id,
    username: row.username,
    password: '',
    display_name: row.display_name,
    role: row.role,
    is_active: row.is_active
  })
  userDialogVisible.value = true
}

async function handleSaveUser() {
  try {
    await userFormRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    if (isEditUser.value) {
      await updateUser(userForm.id, {
        display_name: userForm.display_name,
        role: userForm.role,
        is_active: userForm.is_active
      })
      ElMessage.success('用户更新成功')
    } else {
      await createUser({
        username: userForm.username,
        display_name: userForm.display_name,
        password: userForm.password,
        role: userForm.role
      })
      ElMessage.success('用户创建成功')
    }
    userDialogVisible.value = false
    loadUsers()
  } catch (e) {
    console.error('保存用户失败:', e)
  } finally {
    saving.value = false
  }
}

async function handleDeleteUser(row) {
  try {
    await ElMessageBox.confirm(`确定要删除用户 "${row.username}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') {
      console.error('删除用户失败:', e)
    }
  }
}

// ========== 角色编辑 ==========
function handleAddRole() {
  roleForm.name = ''
  roleDialogVisible.value = true
}

async function handleSaveRole() {
  try {
    await roleFormRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    await createRole(roleForm.name)
    ElMessage.success('角色创建成功')
    roleDialogVisible.value = false
    loadRoleList()
  } catch (e) {
    console.error('创建角色失败:', e)
  } finally {
    saving.value = false
  }
}

function handleRenameRole(row) {
  renameOldName.value = row.role
  renameNewName.value = ''
  renameDialogVisible.value = true
}

async function handleConfirmRename() {
  if (!renameNewName.value || renameNewName.value === renameOldName.value) {
    ElMessage.warning('请输入不同的角色名称')
    return
  }

  saving.value = true
  try {
    // 获取旧角色权限，然后使用原子重命名API
    const res = await getRolePermissions(renameOldName.value)
    const perms = res.data?.permissions || {}

    // 原子重命名：更新角色名称并保留权限
    await saveRolePermissions(renameOldName.value, {
      modules: perms.modules || [],
      sales_tabs: perms.sales_tabs,
      regions: perms.regions
    }, renameNewName.value)

    ElMessage.success('角色重命名成功')
    renameDialogVisible.value = false

    // 如果当前选中的是被重命名的角色，更新选择
    if (selectedRole.value === renameOldName.value) {
      selectedRole.value = renameNewName.value
    }

    loadRoleList()
  } catch (e) {
    console.error('重命名角色失败:', e)
  } finally {
    saving.value = false
  }
}

async function handleDeleteRole(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除角色 "${row.role}" 吗？删除后使用该角色的用户将无法登录。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await deleteRole(row.role)
    ElMessage.success('角色删除成功')

    if (selectedRole.value === row.role) {
      selectedRole.value = ''
    }

    loadRoleList()
  } catch (e) {
    if (e !== 'cancel') {
      console.error('删除角色失败:', e)
    }
  }
}

// ========== 初始化 ==========
onMounted(async () => {
  await loadRoleList()
  loadUsers()
  loadRegions()
  // 自动选中第一个角色，触发 handleRoleChange 回填权限
  if (roleList.value.length > 0 && !selectedRole.value) {
    selectedRole.value = roleList.value[0].role
    await handleRoleChange(selectedRole.value)
  }
})
</script>

<style scoped>
.permissions-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
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
  gap: 12px;
  margin-bottom: 16px;
}

.role-selector {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.selector-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-right: 8px;
}

.permission-panels {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.permission-panel {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.panel-body {
  padding: 16px;
}

.panel-body .el-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
}

.panel-body .el-checkbox {
  margin-right: 0;
}
</style>
