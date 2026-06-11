<template>
  <div class="llm-config-page">
    <div class="page-header">
      <h2>大模型 API 配置</h2>
      <p class="page-desc">配置 MiniMax 大模型 API，用于商品生命周期分析中的 AI 运营建议生成。</p>
    </div>

    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>MiniMax API 设置</span>
          <el-tag v-if="config.api_key_set" type="success" size="small">已配置</el-tag>
          <el-tag v-else type="warning" size="small">未配置</el-tag>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        label-position="top"
        class="config-form"
      >
        <el-form-item label="API Key" prop="minimax_api_key">
          <el-input
            v-model="form.minimax_api_key"
            type="password"
            show-password
            placeholder="请输入 MiniMax API Key"
            clearable
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
          <div class="form-tip">
            在 <el-link type="primary" href="https://platform.minimaxi.com" target="_blank">MiniMax 开放平台</el-link> 获取 API Key
          </div>
        </el-form-item>

        <el-form-item label="API 地址" prop="minimax_base_url">
          <el-input
            v-model="form.minimax_base_url"
            placeholder="https://api.minimaxi.com/anthropic"
            clearable
          >
            <template #prefix>
              <el-icon><Link /></el-icon>
            </template>
          </el-input>
          <div class="form-tip">MiniMax Anthropic 兼容接口地址，默认 https://api.minimaxi.com/anthropic（国际用户为 https://api.minimax.io/anthropic）</div>
        </el-form-item>

        <el-form-item label="模型名称" prop="minimax_model">
          <el-select
            v-model="form.minimax_model"
            filterable
            allow-create
            placeholder="选择或输入模型名称"
            style="width: 100%"
          >
            <el-option value="MiniMax-M3" label="MiniMax-M3（最新旗舰）" />
            <el-option value="MiniMax-M2.7" label="MiniMax-M2.7（高性能）" />
            <el-option value="MiniMax-M2.7-highspeed" label="MiniMax-M2.7-highspeed（高速版）" />
            <el-option value="MiniMax-M2.5" label="MiniMax-M2.5（性价比）" />
            <el-option value="MiniMax-M2.1" label="MiniMax-M2.1（编程优化）" />
            <el-option value="MiniMax-M2" label="MiniMax-M2（高效编码）" />
          </el-select>
          <div class="form-tip">支持手动输入自定义模型名称</div>
        </el-form-item>

        <el-form-item>
          <div class="form-actions">
            <el-button type="primary" @click="handleSave" :loading="saving">
              保存配置
            </el-button>
            <el-button @click="handleTest" :loading="testing" :disabled="!config.api_key_set">
              测试连接
            </el-button>
            <el-button @click="handleRefresh">
              刷新
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 测试结果 -->
    <el-card v-if="testResult" class="test-result-card" :class="{ 'test-success': testResult.success, 'test-fail': !testResult.success }">
      <template #header>
        <div class="card-header">
          <span>连接测试结果</span>
          <el-tag :type="testResult.success ? 'success' : 'danger'" size="small">
            {{ testResult.success ? '成功' : '失败' }}
          </el-tag>
        </div>
      </template>
      <div class="test-result-content">
        <p><strong>消息：</strong>{{ testResult.message }}</p>
        <p v-if="testResult.model"><strong>模型：</strong>{{ testResult.model }}</p>
        <p v-if="testResult.tokens_used"><strong>消耗Token：</strong>{{ testResult.tokens_used }}</p>
      </div>
    </el-card>

    <!-- 使用说明 -->
    <el-card class="help-card">
      <template #header>
        <span>使用说明</span>
      </template>
      <div class="help-content">
        <h4>如何获取 MiniMax API Key？</h4>
        <ol>
          <li>访问 <el-link type="primary" href="https://platform.minimaxi.com" target="_blank">MiniMax 开放平台</el-link></li>
          <li>注册/登录账号</li>
          <li>在「API Keys」页面创建新的 API Key</li>
          <li>将 API Key 粘贴到上方输入框</li>
        </ol>

        <h4>配置后如何使用？</h4>
        <p>配置完成后，在 <strong>高级分析 → 商品生命周期</strong> 页面中，点击表格中的「AI建议」按钮，系统将自动调用大模型为每个商品生成个性化运营建议。</p>

        <h4>支持的模型</h4>
        <ul>
          <li><code>MiniMax-M3</code> — 最新旗舰模型，推荐使用</li>
          <li><code>MiniMax-M2.7</code> — 高性能模型</li>
          <li><code>MiniMax-M2.7-highspeed</code> — 高速版，速度大幅提升</li>
          <li><code>MiniMax-M2.5</code> — 顶尖性能与极致性价比</li>
          <li><code>MiniMax-M2.1</code> — 强大编程能力</li>
          <li><code>MiniMax-M2</code> — 高效编码与Agent</li>
        </ul>

        <h4>API 地址说明</h4>
        <ul>
          <li>国内用户：<code>https://api.minimaxi.com/anthropic</code></li>
          <li>国际用户：<code>https://api.minimax.io/anthropic</code></li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, Link } from '@element-plus/icons-vue'
import { getLlmConfig, updateLlmConfig, testLlmConnection } from '@/api/sysConfig'

const formRef = ref(null)
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

const config = reactive({
  api_key_set: false,
})

const form = reactive({
  minimax_api_key: '',
  minimax_base_url: 'https://api.minimaxi.com/anthropic',
  minimax_model: 'MiniMax-M3',
})

const rules = {
  minimax_base_url: [
    { required: true, message: '请输入 API 地址', trigger: 'blur' },
  ],
  minimax_model: [
    { required: true, message: '请输入或选择模型名称', trigger: 'change' },
  ],
}

async function loadConfig() {
  try {
    const res = await getLlmConfig()
    const data = res.data?.data || res.data || {}
    config.api_key_set = data.minimax_api_key_set || false
    form.minimax_api_key = ''  // 不回填密码
    form.minimax_base_url = data.minimax_base_url || 'https://api.minimaxi.com/anthropic'
    form.minimax_model = data.minimax_model || 'MiniMax-M3'
    testResult.value = null
  } catch (e) {
    console.error('加载LLM配置失败:', e)
    ElMessage.error('加载配置失败')
  }
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const payload = {
      minimax_base_url: form.minimax_base_url,
      minimax_model: form.minimax_model,
    }
    // 只有用户输入了新的 API Key 才提交
    if (form.minimax_api_key && !form.minimax_api_key.includes('****')) {
      payload.minimax_api_key = form.minimax_api_key
    }

    await updateLlmConfig(payload)
    ElMessage.success('配置已保存')
    await loadConfig()
  } catch (e) {
    console.error('保存LLM配置失败:', e)
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testing.value = true
  testResult.value = null
  try {
    const res = await testLlmConnection()
    testResult.value = res.data?.data || res.data || {}
    if (testResult.value.success) {
      ElMessage.success('连接测试成功！')
    } else {
      ElMessage.warning('连接测试失败，请检查配置')
    }
  } catch (e) {
    testResult.value = {
      success: false,
      message: e.response?.data?.detail || e.message || '测试失败',
    }
    ElMessage.error('连接测试失败')
  } finally {
    testing.value = false
  }
}

function handleRefresh() {
  loadConfig()
  ElMessage.info('已刷新')
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.llm-config-page {
  max-width: 800px;
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
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

.config-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.config-form {
  max-width: 600px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.5;
}

.form-actions {
  display: flex;
  gap: 12px;
}

.test-result-card {
  margin-bottom: 20px;
}

.test-success {
  border-left: 3px solid #67C23A;
}

.test-fail {
  border-left: 3px solid #F56C6C;
}

.test-result-content p {
  margin: 8px 0;
  font-size: 14px;
  color: #303133;
}

.help-card {
  margin-bottom: 20px;
}

.help-content h4 {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 16px 0 8px;
}

.help-content h4:first-child {
  margin-top: 0;
}

.help-content p,
.help-content li {
  font-size: 14px;
  color: #606266;
  line-height: 1.8;
}

.help-content code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: #409EFF;
}
</style>
