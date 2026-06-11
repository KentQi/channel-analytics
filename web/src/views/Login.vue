<template>
  <div class="login-container">
    <canvas ref="canvasRef" class="particle-canvas"></canvas>
    <div class="login-box">
      <div class="login-header">
        <h1>销售分析系统</h1>
        <p>请登录以继续</p>
      </div>
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-button"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="demo-hint">
        <p>🚀 <strong>Demo 账号</strong>(首次体验可直接登录):</p>
        <p>管理员: <code>admin</code> / <code>admin123</code></p>
        <p>业务: <code>alice</code> / <code>admin123</code> · <code>bob</code> / <code>admin123</code> · <code>charlie</code> / <code>admin123</code> · <code>diana</code> / <code>admin123</code></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const canvasRef = ref(null)

const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
    loading.value = true

    await authStore.login(loginForm.username, loginForm.password)

    ElMessage.success('登录成功')

    // 默认跳到销售概览(不是 /,避免落到待办页造成"看起来像 bug")
    const redirect = route.query.redirect || '/sales-analysis/dashboard'
    router.push(redirect)
  } catch (error) {
    if (error !== false) {
      console.error('登录失败:', error)
    }
  } finally {
    loading.value = false
  }
}

// ==================== Canvas 粒子动画 ====================
let animationId = null
let particles = []
let ctx = null
let canvas = null

class Particle {
  constructor(canvas) {
    this.x = Math.random() * canvas.width
    this.y = Math.random() * canvas.height
    this.vx = (Math.random() - 0.5) * 0.5
    this.vy = (Math.random() - 0.5) * 0.5
    this.radius = Math.random() * 2 + 1
    this.color = `rgba(255, 255, 255, ${Math.random() * 0.5 + 0.3})`
  }

  update(canvas) {
    this.x += this.vx
    this.y += this.vy

    if (this.x < 0 || this.x > canvas.width) this.vx = -this.vx
    if (this.y < 0 || this.y > canvas.height) this.vy = -this.vy
  }

  draw(ctx) {
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.fill()
  }
}

function initParticles() {
  if (!canvas) return
  const particleCount = Math.floor((canvas.width * canvas.height) / 15000)
  particles = []
  for (let i = 0; i < particleCount; i++) {
    particles.push(new Particle(canvas))
  }
}

function drawLines() {
  if (!ctx || !canvas) return
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < 120) {
        ctx.beginPath()
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.strokeStyle = `rgba(255, 255, 255, ${0.3 * (1 - distance / 120)})`
        ctx.lineWidth = 1
        ctx.stroke()
      }
    }
  }
}

function animate() {
  if (!ctx || !canvas) return
  ctx.fillStyle = 'rgba(26, 26, 26, 0.1)'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  particles.forEach(p => {
    p.update(canvas)
    p.draw(ctx)
  })

  drawLines()
  animationId = requestAnimationFrame(animate)
}

function initCanvas() {
  canvas = canvasRef.value
  if (!canvas) return

  ctx = canvas.getContext('2d')

  function resize() {
    if (!canvas) return
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
    initParticles()
  }

  resize()
  window.addEventListener('resize', resize)
  animate()
}

onMounted(() => {
  initCanvas()
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('resize', () => {})
})
</script>

<style scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%);
}

.particle-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.login-box {
  position: relative;
  z-index: 1;
  width: 400px;
  padding: 40px;
  background-color: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
}

.demo-hint {
  margin-top: 20px;
  padding: 12px 16px;
  background: #f0f9ff;
  border-left: 3px solid #00d9c0;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: #475569;
}

.demo-hint code {
  background: #fff;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: 'Menlo', 'Monaco', monospace;
  color: #00b39e;
  border: 1px solid #e0e7ff;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 24px;
  color: #303133;
  margin-bottom: 8px;
}

.login-header p {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.login-form {
  margin-top: 24px;
}

.login-button {
  width: 100%;
}
</style>
