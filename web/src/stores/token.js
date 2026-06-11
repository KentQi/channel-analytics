import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useTokenStore = defineStore('token', () => {
  // Token usage tracking
  const inputTokens = ref(0)
  const outputTokens = ref(0)
  const cacheTokens = ref(0)
  const totalTokens = ref(0)
  const maxTokens = ref(1000000) // 1M default max context

  // Context length tracking
  const contextLength = ref(0)
  const maxContextLength = ref(1000000) // 1M tokens

  // Computed values
  const contextUsagePercent = computed(() => {
    return Math.round((contextLength.value / maxContextLength.value) * 100)
  })

  const totalUsagePercent = computed(() => {
    return Math.round((totalTokens.value / maxTokens.value) * 100)
  })

  const formattedInputTokens = computed(() => formatTokens(inputTokens.value))
  const formattedOutputTokens = computed(() => formatTokens(outputTokens.value))
  const formattedCacheTokens = computed(() => formatTokens(cacheTokens.value))
  const formattedTotalTokens = computed(() => formatTokens(totalTokens.value))
  const formattedContextLength = computed(() => formatTokens(contextLength.value))
  const formattedMaxContext = computed(() => formatTokens(maxContextLength.value))

  function formatTokens(tokens) {
    if (tokens >= 1000000) {
      return (tokens / 1000000).toFixed(1) + 'M'
    } else if (tokens >= 1000) {
      return (tokens / 1000).toFixed(1) + 'K'
    }
    return tokens.toString()
  }

  function updateTokenUsage(data) {
    if (data.inputTokens !== undefined) inputTokens.value = data.inputTokens
    if (data.outputTokens !== undefined) outputTokens.value = data.outputTokens
    if (data.cacheTokens !== undefined) cacheTokens.value = data.cacheTokens
    if (data.totalTokens !== undefined) totalTokens.value = data.totalTokens
    if (data.maxTokens !== undefined) maxTokens.value = data.maxTokens
  }

  function updateContextLength(length, max) {
    contextLength.value = length
    if (max !== undefined) maxContextLength.value = max
  }

  function reset() {
    inputTokens.value = 0
    outputTokens.value = 0
    cacheTokens.value = 0
    totalTokens.value = 0
    contextLength.value = 0
  }

  return {
    inputTokens,
    outputTokens,
    cacheTokens,
    totalTokens,
    maxTokens,
    contextLength,
    maxContextLength,
    contextUsagePercent,
    totalUsagePercent,
    formattedInputTokens,
    formattedOutputTokens,
    formattedCacheTokens,
    formattedTotalTokens,
    formattedContextLength,
    formattedMaxContext,
    updateTokenUsage,
    updateContextLength,
    reset
  }
})