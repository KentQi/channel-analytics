<template>
  <div class="app-header">
    <div class="header-left">
      <!-- Mobile hamburger menu button -->
      <el-button
        v-if="isMobile"
        :icon="Menu"
        text
        class="menu-btn"
        @click="emit('toggleSidebar')"
      />
      <span class="page-title">{{ pageTitle }}</span>
    </div>
    <div class="header-right">
      <!-- Notification bell -->
      <NotificationBell class="hide-mobile" />

      <el-dropdown @command="handleCommand">
        <span class="user-info">
          <el-icon><User /></el-icon>
          <span class="username">{{ authStore.displayName || authStore.username }}</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="changePassword">
              <el-icon><Key /></el-icon>
              修改密码
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="400px"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="100px"
      >
        <el-form-item label="旧密码" prop="oldPassword">
          <el-input
            v-model="passwordForm.oldPassword"
            type="password"
            placeholder="请输入旧密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api/auth'
import { useResponsive } from '@/composables/useResponsive'
import NotificationBell from './NotificationBell.vue'
import { Menu, Bell, User, ArrowDown, Key, SwitchButton } from '@element-plus/icons-vue'

const emit = defineEmits(['toggleSidebar'])

const { isMobile } = useResponsive()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const pageTitleMap = {
  'Todo': '待办事项',
  'DataImport': '数据导入',
  'ETL': 'ETL执行',
  'StockAnalysis': '库存分析',
  'SalesAnalysis': '销售分析',
  'RepurchaseAnalysis': '返单分析',
  'DataManagement': '信息维护',
  'Permissions': '权限配置',
  'Alerts': '预警通知',
  'Reports': '自定义报表'
}

const pageTitle = computed(() => {
  return pageTitleMap[route.name] || ''
})

const passwordDialogVisible = ref(false)
const passwordLoading = ref(false)
const passwordFormRef = ref(null)

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  oldPassword: [
    { required: true, message: '请输入旧密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleCommand = async (command) => {
  if (command === 'changePassword') {
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    passwordDialogVisible.value = true
  } else if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      authStore.logout()
      router.push({ name: 'Login' })
      ElMessage.success('已退出登录')
    } catch {
      // 用户取消
    }
  }
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return

  try {
    await passwordFormRef.value.validate()
    passwordLoading.value = true

    await changePassword(passwordForm.oldPassword, passwordForm.newPassword)

    ElMessage.success('密码修改成功')
    passwordDialogVisible.value = false
  } catch (error) {
    if (error !== false) {
      console.error('修改密码失败:', error)
    }
  } finally {
    passwordLoading.value = false
  }
}
</script>

<style scoped>
.app-header {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: linear-gradient(180deg, rgba(26, 31, 46, 0.95) 0%, rgba(26, 31, 46, 0.88) 100%);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-btn {
  color: #e2e8f0;
  font-size: 20px;
}

.menu-btn:hover {
  color: #00d9c0;
}

.notification-badge {
  margin-right: 8px;
}

.notification-btn {
  color: #e2e8f0;
}

.notification-btn:hover {
  color: #00d9c0;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  letter-spacing: 0.3px;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  transition: all 0.25s ease;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.user-info:hover {
  background: rgba(0, 217, 192, 0.1);
  border-color: rgba(0, 217, 192, 0.2);
}

.username {
  color: #e2e8f0;
  font-size: 14px;
  font-weight: 500;
}

:deep(.el-dropdown-menu) {
  background: #1a1f2e;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

:deep(.el-dropdown-menu__item) {
  color: #e2e8f0;
}

:deep(.el-dropdown-menu__item:hover) {
  background: rgba(0, 217, 192, 0.1);
  color: #00d9c0;
}

:deep(.el-dialog) {
  background: #1a1f2e;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

:deep(.el-dialog__title) {
  color: #e2e8f0;
}

:deep(.el-form-item__label) {
  color: #94a3b8;
}

:deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: none;
}

:deep(.el-input__wrapper:hover) {
  border-color: rgba(0, 217, 192, 0.3);
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #00d9c0;
  box-shadow: 0 0 0 2px rgba(0, 217, 192, 0.15);
}
</style>
