import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as reportApi from '@/api/customReport'

export const useCustomReportStore = defineStore('customReport', () => {
  // State
  const templates = ref([])
  const currentTemplate = ref(null)
  const previewData = ref([])
  const previewFields = ref([])
  const previewFieldDisplayNames = ref({})
  const previewTotal = ref(0)
  const tables = ref([])
  const tableFields = ref({})
  const loading = ref(false)
  const error = ref(null)

  // Computed
  const myTemplates = computed(() => templates.value)

  // Actions
  async function fetchTables() {
    try {
      const { data } = await reportApi.getAvailableTables()
      tables.value = data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  async function fetchTableFields(tableName) {
    if (tableFields.value[tableName]) {
      return tableFields.value[tableName]
    }
    try {
      const { data } = await reportApi.getTableFields(tableName)
      tableFields.value[tableName] = data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  async function fetchTemplates() {
    loading.value = true
    error.value = null
    try {
      const { data } = await reportApi.getReports()
      templates.value = data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchTemplate(templateId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await reportApi.getReport(templateId)
      currentTemplate.value = data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createTemplate(templateData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await reportApi.createReport(templateData)
      templates.value.unshift(data)
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateTemplate(templateId, templateData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await reportApi.updateReport(templateId, templateData)
      const idx = templates.value.findIndex(t => t.id === templateId)
      if (idx !== -1) templates.value[idx] = data
      if (currentTemplate.value?.id === templateId) {
        currentTemplate.value = data
      }
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteTemplate(templateId) {
    loading.value = true
    error.value = null
    try {
      await reportApi.deleteReport(templateId)
      templates.value = templates.value.filter(t => t.id !== templateId)
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function preview(config, page = 1, pageSize = 100) {
    loading.value = true
    error.value = null
    try {
      const { data } = await reportApi.previewReport({ ...config, page, page_size: pageSize })
      previewData.value = data.data || []
      previewFields.value = data.fields || []
      previewFieldDisplayNames.value = data.field_display_names || {}
      previewTotal.value = data.total || 0
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function executeTemplate(templateId, page = 1, pageSize = 100) {
    loading.value = true
    error.value = null
    try {
      const { data } = await reportApi.executeReport(templateId, { page, page_size: pageSize })
      previewData.value = data.data || []
      previewFields.value = data.fields || []
      previewFieldDisplayNames.value = data.field_display_names || {}
      previewTotal.value = data.total || 0
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function shareTemplate(templateId, targetUsers, targetRoles) {
    try {
      await reportApi.shareReport(templateId, {
        target_users: targetUsers,
        target_roles: targetRoles,
      })
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  function clearPreview() {
    previewData.value = []
    previewFields.value = []
    previewTotal.value = 0
  }

  return {
    // State
    templates,
    currentTemplate,
    previewData,
    previewFields,
    previewFieldDisplayNames,
    previewTotal,
    tables,
    tableFields,
    loading,
    error,
    // Computed
    myTemplates,
    // Actions
    fetchTables,
    fetchTableFields,
    fetchTemplates,
    fetchTemplate,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    preview,
    executeTemplate,
    shareTemplate,
    clearPreview,
  }
})
