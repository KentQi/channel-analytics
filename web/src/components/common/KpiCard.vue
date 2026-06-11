<template>
  <div class="kpi-card" :class="{ 'kpi-card--clickable': clickable }" @click="handleClick">
    <div class="kpi-card__header">
      <span class="kpi-card__label">{{ label }}</span>
      <slot name="extra"></slot>
    </div>

    <div class="kpi-card__body">
      <span v-if="prefix" class="kpi-card__prefix">{{ prefix }}</span>
      <span class="kpi-card__value">{{ formattedValue }}</span>
      <span v-if="suffix" class="kpi-card__suffix">{{ suffix }}</span>
    </div>

    <div v-if="showChange && changeValue !== null" class="kpi-card__footer">
      <div class="kpi-card__change" :class="changeClass">
        <el-icon v-if="changeValue > 0" class="kpi-card__change-icon"><ArrowUp /></el-icon>
        <el-icon v-else-if="changeValue < 0" class="kpi-card__change-icon"><ArrowDown /></el-icon>
        <span>{{ changeText }}</span>
      </div>
      <span v-if="changeLabel" class="kpi-card__change-label">{{ changeLabel }}</span>
    </div>

    <slot name="footer"></slot>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  // 标签
  label: {
    type: String,
    required: true
  },
  // 数值
  value: {
    type: [Number, String],
    default: 0
  },
  // 前缀（如货币符号 ¥）
  prefix: {
    type: String,
    default: ''
  },
  // 后缀（如 %）
  suffix: {
    type: String,
    default: ''
  },
  // 格式化类型：number, currency, percent, custom
  formatType: {
    type: String,
    default: 'number'
  },
  // 小数位数
  decimals: {
    type: Number,
    default: 2
  },
  // 千分位分隔符
  thousandSeparator: {
    type: Boolean,
    default: true
  },
  // 变化值（同比/环比）
  changeValue: {
    type: Number,
    default: null
  },
  // 变化类型：up(上涨), down(下跌), auto(根据正负自动判断)
  changeType: {
    type: String,
    default: 'auto'
  },
  // 变化标签（如 "同比" 或 "环比"）
  changeLabel: {
    type: String,
    default: ''
  },
  // 是否显示变化
  showChange: {
    type: Boolean,
    default: true
  },
  // 是否可点击
  clickable: {
    type: Boolean,
    default: false
  },
  // 是否为逆指标（下降代表好的表现）
  inverseIndicator: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

// 格式化数值
const formattedValue = computed(() => {
  if (props.value === null || props.value === undefined) {
    return '--'
  }

  const numValue = typeof props.value === 'string' ? parseFloat(props.value) : props.value

  if (isNaN(numValue)) {
    return props.value
  }

  switch (props.formatType) {
    case 'currency':
      return formatCurrency(numValue)
    case 'percent':
      return formatNumber(numValue, props.decimals) + '%'
    case 'integer':
      return formatNumber(numValue, 0)
    case 'number':
    default:
      return formatNumber(numValue, props.decimals)
  }
})

// 格式化数字（添加千分位）
function formatNumber(num, decimals = 2) {
  const fixed = num.toFixed(decimals)
  if (props.thousandSeparator) {
    const parts = fixed.split('.')
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    return parts.join('.')
  }
  return fixed
}

// 格式化货币
function formatCurrency(num) {
  const fixed = num.toFixed(props.decimals)
  const parts = fixed.split('.')
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return parts.join('.')
}

// 变化样式类
const changeClass = computed(() => {
  if (props.changeValue === null || props.changeValue === 0) {
    return 'kpi-card__change--neutral'
  }

  const isPositive = props.changeValue > 0

  if (props.changeType === 'up') {
    return isPositive ? 'kpi-card__change--up' : 'kpi-card__change--down'
  } else if (props.changeType === 'down') {
    return isPositive ? 'kpi-card__change--down' : 'kpi-card__change--up'
  } else {
    // auto 模式：根据 inverseIndicator 判断
    if (props.inverseIndicator) {
      return isPositive ? 'kpi-card__change--down' : 'kpi-card__change--up'
    }
    return isPositive ? 'kpi-card__change--up' : 'kpi-card__change--down'
  }
})

// 变化文本
const changeText = computed(() => {
  if (props.changeValue === null) return ''

  const absValue = Math.abs(props.changeValue)
  const formattedValue = formatNumber(absValue, 2)

  if (props.formatType === 'percent') {
    return `${formattedValue}%`
  }

  return `${formattedValue}${props.suffix || ''}`
})

// 点击处理
function handleClick() {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<style scoped>
.kpi-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.kpi-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #00d9c0, #06b6d4);
  opacity: 0;
  transition: opacity 0.25s ease;
}

.kpi-card--clickable {
  cursor: pointer;
}

.kpi-card--clickable:hover {
  border-color: rgba(0, 217, 192, 0.3);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.kpi-card--clickable:hover::before {
  opacity: 1;
}

.kpi-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.kpi-card__label {
  font-size: 13px;
  color: #909399;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.kpi-card__body {
  display: flex;
  align-items: baseline;
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.kpi-card__prefix {
  font-size: 16px;
  color: #909399;
  margin-right: 2px;
}

.kpi-card__suffix {
  font-size: 16px;
  color: #909399;
  margin-left: 4px;
}

.kpi-card__footer {
  display: flex;
  align-items: center;
  margin-top: 12px;
  font-size: 13px;
}

.kpi-card__change {
  display: flex;
  align-items: center;
  gap: 2px;
  font-weight: 600;
}

.kpi-card__change-icon {
  font-size: 12px;
}

.kpi-card__change--up {
  color: #67c23a;
}

.kpi-card__change--down {
  color: #f56c6c;
}

.kpi-card__change--neutral {
  color: #909399;
}

.kpi-card__change-label {
  color: #909399;
  margin-left: 8px;
}
</style>
