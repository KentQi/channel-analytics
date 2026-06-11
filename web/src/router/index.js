import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    redirect: '/todo',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'todo',
        name: 'Todo',
        component: () => import('@/views/Todo.vue'),
        meta: { module: '待办事项' }
      },
      {
        path: 'data-import',
        name: 'DataImport',
        component: () => import('@/views/DataImport.vue'),
        meta: { module: '数据导入' }
      },
      {
        path: 'etl',
        name: 'ETL',
        component: () => import('@/views/ETL.vue'),
        meta: { module: 'ETL执行' }
      },
      {
        path: 'rpa',
        name: 'RpaManagement',
        component: () => import('@/views/RpaManagement.vue'),
        meta: { module: 'RPA采集' }
      },
      {
        path: 'basis-analysis',
        name: 'BasisAnalysis',
        component: () => import('@/views/BasisAnalysis.vue'),
        meta: { module: '基础分析' }
      },
      {
        path: 'stock-analysis',
        name: 'StockAnalysis',
        component: () => import('@/views/StockAnalysis.vue'),
        meta: { module: '库存分析' }
      },
      {
        path: 'sales-analysis',
        component: () => import('@/views/sales/SalesAnalysisLayout.vue'),
        redirect: '/sales-analysis/wide-table',
        meta: { module: '销售分析' },
        children: [
          {
            path: 'wide-table',
            name: 'SalesWideTable',
            component: () => import('@/views/sales/WideTable.vue')
          },
          {
            path: 'dashboard',
            name: 'SalesDashboard',
            component: () => import('@/views/sales/Dashboard.vue')
          },
          {
            path: 'indicator',
            name: 'SalesIndicator',
            component: () => import('@/views/sales/Indicator.vue')
          },
          {
            path: 'detail',
            name: 'SalesDetail',
            component: () => import('@/views/sales/SalesDetail.vue')
          },
          {
            path: 'flow',
            name: 'SalesFlow',
            component: () => import('@/views/sales/FlowAnalysis.vue')
          }
        ]
      },
      {
        path: 'repurchase',
        component: () => import('@/views/repurchase/RepurchasePage.vue'),
        redirect: '/repurchase/customer',
        meta: { module: '返单分析' },
        children: [
          {
            path: 'customer',
            redirect: '/repurchase/customer/overview'
          },
          {
            path: 'customer/overview',
            name: 'CustomerRetentionOverview',
            component: () => import('@/views/repurchase/CustomerRetentionOverview.vue')
          },
          {
            path: 'customer/detail',
            name: 'CustomerRetentionDetail',
            component: () => import('@/views/repurchase/CustomerRetentionDetail.vue')
          },
          {
            path: 'customer/churn',
            name: 'ChurnWarning',
            component: () => import('@/views/repurchase/ChurnWarning.vue')
          },
          {
            path: 'customer/new-customer',
            name: 'NewCustomerTracking',
            component: () => import('@/views/repurchase/NewCustomerTracking.vue')
          },
          {
            path: 'customer/value',
            name: 'CustomerValue',
            component: () => import('@/views/repurchase/CustomerValue.vue')
          },
          {
            path: 'product',
            redirect: '/repurchase/product/retention'
          },
          {
            path: 'product/retention',
            name: 'ProductRetention',
            component: () => import('@/views/repurchase/ProductRetention.vue')
          },
          {
            path: 'product/sales',
            name: 'ProductSalesTracking',
            component: () => import('@/views/repurchase/ProductSalesTracking.vue')
          },
          {
            path: 'product/new-product',
            name: 'NewProductWarning',
            component: () => import('@/views/repurchase/NewProductWarning.vue')
          }
        ]
      },
      {
        path: 'advanced',
        component: () => import('@/views/advanced/AdvancedPage.vue'),
        redirect: '/advanced/product-lifecycle',
        meta: { module: '高级分析' },
        children: [
          {
            path: 'product-lifecycle',
            name: 'ProductLifecycle',
            component: () => import('@/views/advanced/ProductLifecycle.vue')
          },
          {
            path: 'customer-lifecycle',
            name: 'CustomerLifecycle',
            component: () => import('@/views/advanced/CustomerLifecycle.vue')
          },
          {
            path: 'product-cluster',
            name: 'ProductCluster',
            component: () => import('@/views/advanced/ProductCluster.vue')
          },
          {
            path: 'customer-cluster',
            name: 'CustomerCluster',
            component: () => import('@/views/advanced/CustomerCluster.vue')
          }
        ]
      },
      {
        path: 'data-management',
        name: 'DataManagement',
        component: () => import('@/views/DataManagement.vue'),
        meta: { module: '信息维护' }
      },
      {
        path: 'permissions',
        name: 'Permissions',
        component: () => import('@/views/Permissions.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'system-log',
        name: 'SystemLog',
        component: () => import('@/views/SystemLog.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/alerts/AlertsPage.vue'),
        meta: { module: '预警通知' }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/reports/ReportsPage.vue'),
        meta: { module: '自定义报表' }
      },
      {
        path: 'settings',
        component: () => import('@/views/settings/SettingsLayout.vue'),
        redirect: '/settings/llm-config',
        children: [
          {
            path: 'llm-config',
            name: 'LlmConfig',
            component: () => import('@/views/settings/LlmConfig.vue'),
            meta: { requiresAdmin: true }
          }
        ]
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'Todo' })
  } else if (to.meta.requiresAdmin && !['admin', '创建人'].includes(authStore.role)) {
    ElMessage.error('您没有权限访问此页面')
    next(from?.fullPath || '/')
  } else if (to.meta.module && !authStore.hasModule(to.meta.module)) {
    ElMessage.error(`您没有「${to.meta.module}」模块的访问权限`)
    next({ name: 'Todo' })
  } else {
    next()
  }
})

export default router
