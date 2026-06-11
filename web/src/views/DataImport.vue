<template>
  <div class="data-import">
    <div class="page-header">
      <h2>数据导入</h2>
      <p class="page-desc">依次上传 5 个源文件（文件名前缀：YYYYMMDD_）</p>
    </div>

    <!-- 5 个文件上传区 -->
    <div v-for="(f, idx) in sourceFiles" :key="f.key" class="file-section">
      <el-divider v-if="idx > 0" />
      <div class="file-block">
        <div class="file-block-header">
          <span class="file-type-label">{{ f.name }}</span>
          <el-tag
            v-if="getFile(f.key)"
            type="success"
            size="small"
          >
            {{ getFile(f.key).original_name || getFile(f.key).filename }}
            ({{ formatSize(getFile(f.key).size || getFile(f.key).file_size) }})
          </el-tag>
          <el-tag v-else type="info" size="small">未上传（{{ f.expectedName }}）</el-tag>
        </div>

        <div class="file-block-body">
          <el-upload
            class="upload-area"
            drag
            accept=".xlsx"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="(file) => doUpload(f.key, file)"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">仅支持 .xlsx 格式</div>
            </template>
          </el-upload>

          <div v-if="getFile(f.key)" class="file-actions">
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(f.key)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 文件状态总览 -->
    <div class="status-overview">
      <h3>文件状态总览</h3>
      <div v-for="f in sourceFiles" :key="f.key" class="status-row">
        <span v-if="getFile(f.key)">✅ {{ f.name }} — 已就绪</span>
        <span v-else>⭕ {{ f.name }} — 未上传</span>
      </div>
    </div>

    <!-- 底部操作 -->
    <div class="bottom-bar">
      <template v-if="allUploaded">
        <el-result icon="success" title="5 个源文件已全部就绪" sub-title="可以开始执行 ETL 任务" />
        <div class="bottom-actions">
          <el-button type="primary" size="large" @click="$router.push('/etl')">
            跳转 ETL 执行 →
          </el-button>
        </div>
      </template>
      <template v-else>
        <el-alert
          title="仍有文件缺失"
          type="warning"
          :closable="false"
          show-icon
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadFile, getFileList, deleteFile } from '@/api/etl'

const router = useRouter()

const sourceFiles = [
  { key: '请购单', name: '请购单', expectedName: '请购单.xlsx' },
  { key: '采购单', name: '采购单', expectedName: '采购单.xlsx' },
  { key: '入库单', name: '入库单', expectedName: '入库单.xlsx' },
  { key: '销售出库单', name: '销售出库单', expectedName: '销售出库单.xlsx' },
  { key: '现存量', name: '现存量', expectedName: '现存量.xlsx' },
]

const fileList = ref([])
const uploading = ref(false)

function getFile(key) {
  return fileList.value.find(f => {
    // 优先使用 file_type 字段匹配
    if (f.file_type === key) return true
    // 兼容原来的文件名包含匹配
    const name = (f.original_name || f.filename || '').toLowerCase()
    const k = key.toLowerCase()
    // 精确匹配
    if (name.includes(k)) return true
    // 文件名变体匹配
    const variants = {
      '入库单': ['采购入库', '入库'],
      '销售出库单': ['销售出库'],
      '现存量': ['现存量查询', '库存查询', '现存量'],
      '请购单': ['请购'],
      '采购单': ['采购单'],
    }
    const altNames = variants[key] || []
    return altNames.some(alt => name.includes(alt.toLowerCase()))
  })
}

const allUploaded = computed(() => {
  return sourceFiles.every(f => !!getFile(f.key))
})

function formatSize(bytes) {
  if (!bytes) return '0 KB'
  const kb = bytes / 1024
  if (kb < 1024) return kb.toFixed(1) + ' KB'
  return (kb / 1024).toFixed(1) + ' MB'
}

async function loadFileList() {
  try {
    const res = await getFileList()
    fileList.value = res.data?.files || res.data || []
  } catch (e) {
    fileList.value = []
  }
}

async function doUpload(sourceKey, uploadFileObj) {
  const file = uploadFileObj.raw
  if (!file) return

  const ext = file.name.split('.').pop().toLowerCase()
  if (ext !== 'xlsx') {
    ElMessage.error('仅支持 .xlsx 格式文件')
    return
  }

  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await uploadFile(fd)
    const data = res.data || {}
    const rows = data.rows || data.row_count || ''
    const size = formatSize(data.size || file.size)
    ElMessage.success(`上传成功${rows ? '，共 ' + rows + ' 行' : ''}，大小 ${size}`)
    await loadFileList()
  } catch (e) {
    ElMessage.error(`上传失败: ${e.response?.data?.detail || e.message}`)
  } finally {
    uploading.value = false
  }
}

async function handleDelete(sourceKey) {
  try {
    await ElMessageBox.confirm(`确定要删除「${sourceKey}」文件吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    const target = getFile(sourceKey)
    if (target) {
      await deleteFile(target.id || target.file_id)
      ElMessage.success('删除成功')
      await loadFileList()
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadFileList()
})
</script>

<style scoped>
.data-import {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
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

.file-section {
  margin-bottom: 0;
}

.file-section .el-divider {
  margin: 16px 0;
}

.file-block {
  padding: 12px 0;
}

.file-block-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.file-type-label {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.file-block-body {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.upload-area {
  flex: 1;
}

.file-actions {
  display: flex;
  align-items: center;
  padding-top: 20px;
}

.status-overview {
  margin-top: 24px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.status-overview h3 {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
}

.status-row {
  padding: 4px 0;
  font-size: 14px;
  color: #606266;
}

.bottom-bar {
  margin-top: 24px;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
}

.bottom-actions {
  text-align: center;
  margin-top: 16px;
}
</style>
