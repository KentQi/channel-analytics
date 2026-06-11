import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as alertsApi from '@/api/alerts'

export const useAlertsStore = defineStore('alerts', () => {
  // State
  const rules = ref([])
  const history = ref([])
  const notifications = ref([])
  const stats = ref({
    total_rules: 0,
    enabled_rules: 0,
    triggered_this_month: 0,
    unacknowledged_count: 0,
    unread_notifications: 0,
  })
  const loading = ref(false)
  const error = ref(null)

  // Computed
  const unreadCount = computed(() => stats.value.unread_notifications)

  // Actions
  async function fetchRules(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await alertsApi.getAlertRules(params)
      rules.value = data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createRule(ruleData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await alertsApi.createAlertRule(ruleData)
      rules.value.unshift(data)
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateRule(ruleId, ruleData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await alertsApi.updateAlertRule(ruleId, ruleData)
      const idx = rules.value.findIndex(r => r.id === ruleId)
      if (idx !== -1) rules.value[idx] = data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteRule(ruleId) {
    loading.value = true
    error.value = null
    try {
      await alertsApi.deleteAlertRule(ruleId)
      rules.value = rules.value.filter(r => r.id !== ruleId)
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function testRule(ruleId) {
    const { data } = await alertsApi.testAlertRule(ruleId)
    return data
  }

  async function fetchHistory(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await alertsApi.getAlertHistory(params)
      history.value = data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function acknowledgeAlert(historyId, acknowledgedBy) {
    await alertsApi.acknowledgeAlert(historyId, acknowledgedBy)
    const idx = history.value.findIndex(h => h.id === historyId)
    if (idx !== -1) {
      history.value[idx].is_acknowledged = true
      history.value[idx].acknowledged_by = acknowledgedBy
    }
  }

  async function fetchNotifications(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await alertsApi.getNotifications(params)
      notifications.value = data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function markAsRead(notificationId) {
    await alertsApi.markNotificationRead(notificationId)
    const idx = notifications.value.findIndex(n => n.id === notificationId)
    if (idx !== -1) {
      notifications.value[idx].is_read = true
    }
  }

  async function fetchStats() {
    try {
      const { data } = await alertsApi.getAlertStats()
      stats.value = data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  return {
    // State
    rules,
    history,
    notifications,
    stats,
    loading,
    error,
    // Computed
    unreadCount,
    // Actions
    fetchRules,
    createRule,
    updateRule,
    deleteRule,
    testRule,
    fetchHistory,
    acknowledgeAlert,
    fetchNotifications,
    markAsRead,
    fetchStats,
  }
})
