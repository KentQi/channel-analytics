<template>
  <div ref="chartRef" class="pareto-chart"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  // 数据
  data: {
    type: Array,
    default: () => []
  },
  // 柱状图颜色
  barColor: {
    type: String,
    default: '#409eff'
  },
  // 折线图颜色
  lineColor: {
    type: String,
    default: '#67c23a'
  },
  // 标题
  title: {
    type: String,
    default: ''
  },
  // X轴名称
  xAxisName: {
    type: String,
    default: ''
  },
  // Y轴名称（左侧，柱状图）
  yAxisName: {
    type: String,
    default: ''
  },
  // Y轴名称（右侧，折线图）
  yAxisNameRight: {
    type: String,
    default: '累计占比'
  },
  // 柱状图名称
  barName: {
    type: String,
    default: '数量'
  },
  // 折线图名称
  lineName: {
    type: String,
    default: '累计占比'
  },
  // 高度
  height: {
    type: String,
    default: '400px'
  },
  // 是否显示网格
  showGrid: {
    type: Boolean,
    default: true
  },
  // 是否显示图例
  showLegend: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['click', 'hover'])

const chartRef = ref(null)
let chartInstance = null

// 初始化图表
function initChart() {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

// 更新图表数据
function updateChart() {
  if (!chartInstance) return

  const categories = props.data.map(item => item.name || item.category || item.key || '')
  const barData = props.data.map(item => item.value || item.count || item.amount || 0)

  // 计算累计占比
  const total = barData.reduce((sum, val) => sum + val, 0)
  let cumulative = 0
  const lineData = barData.map(val => {
    cumulative += val
    return total > 0 ? (cumulative / total) * 100 : 0
  })

  const option = {
    title: {
      text: props.title,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 500
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: function(params) {
        let result = params[0].axisValue + '<br/>'
        params.forEach(param => {
          const value = param.seriesName === '累计占比'
            ? param.value.toFixed(2) + '%'
            : (typeof param.value === 'number' ? param.value.toLocaleString() : param.value)
          result += `${param.marker} ${param.seriesName}: ${value}<br/>`
        })
        return result
      }
    },
    legend: props.showLegend ? {
      data: [props.barName, props.lineName],
      top: 30
    } : undefined,
    grid: props.showGrid ? {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    } : undefined,
    xAxis: {
      type: 'category',
      data: categories,
      name: props.xAxisName,
      nameLocation: 'end',
      nameGap: 10,
      axisLabel: {
        rotate: categories.length > 10 ? 45 : 0,
        interval: 'auto'
      }
    },
    yAxis: [
      {
        type: 'value',
        name: props.yAxisName,
        position: 'left',
        axisLabel: {
          formatter: (val) => {
            if (val >= 10000) {
              return (val / 10000).toFixed(0) + '万'
            }
            return val.toLocaleString()
          }
        }
      },
      {
        type: 'value',
        name: props.yAxisNameRight,
        position: 'right',
        min: 0,
        max: 100,
        axisLabel: {
          formatter: '{value}%'
        }
      }
    ],
    series: [
      {
        name: props.barName,
        type: 'bar',
        data: barData,
        itemStyle: {
          color: props.barColor
        },
        barMaxWidth: 50
      },
      {
        name: props.lineName,
        type: 'line',
        yAxisIndex: 1,
        data: lineData,
        smooth: true,
        itemStyle: {
          color: props.lineColor
        },
        lineStyle: {
          width: 2
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: props.lineColor + '40' },
            { offset: 1, color: props.lineColor + '10' }
          ])
        },
        symbol: 'circle',
        symbolSize: 6
      }
    ],
    dataZoom: categories.length > 15 ? [
      {
        type: 'inside',
        start: 0,
        end: 100 / (categories.length / 15) * 100
      }
    ] : undefined
  }

  chartInstance.setOption(option)
}

// 窗口大小变化时重绘图表
function handleResize() {
  chartInstance?.resize()
}

// 绑定事件
function bindEvents() {
  chartInstance?.on('click', (params) => {
    emit('click', params)
  })

  chartInstance?.on('mouseover', (params) => {
    emit('hover', params)
  })
}

// 监听数据变化
watch(
  () => props.data,
  () => {
    nextTick(() => {
      updateChart()
    })
  },
  { deep: true }
)

// 监听窗口大小变化
onMounted(() => {
  initChart()
  bindEvents()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})

// 暴露方法
defineExpose({
  getChart: () => chartInstance,
  resize: handleResize,
  updateData: updateChart
})
</script>

<style scoped>
.pareto-chart {
  width: 100%;
  height: v-bind(height);
}
</style>
