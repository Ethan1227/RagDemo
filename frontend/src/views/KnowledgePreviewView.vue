<template>
  <div class="preview-page">
    <el-page-header @back="router.back()">
      <template #content>
        <span class="page-title">文档块预览 —— {{ filename }}</span>
      </template>
    </el-page-header>

    <!-- 文档信息条：克制展示基本信息，不抢内容焦点 -->
    <div class="doc-infobar">
      <span v-if="kbName">所属知识库：{{ kbName }}</span>
      <span v-if="chunkSize">切块参数：{{ chunkSize }} / 重叠 {{ chunkOverlap }}</span>
      <span>总块数：{{ total }}</span>
    </div>

    <el-empty v-if="!loading && chunks.length === 0" description="该文档暂无文档块" />

    <div class="chunk-list" v-loading="loading">
      <el-card v-for="chunk in chunks" :key="chunk.id" class="chunk-card" shadow="hover">
        <template #header>
          <div class="chunk-header">
            <span class="chunk-index">块 #{{ chunk.chunk_index + 1 }}</span>
            <span class="chunk-chars">{{ chunk.char_count }} 字符</span>
            <div class="chunk-actions">
              <el-button link type="primary" size="small" @click="openEdit(chunk)">编辑</el-button>
              <el-button link type="danger" size="small" @click="removeChunk(chunk)">删除</el-button>
            </div>
          </div>
        </template>
        <div class="chunk-content">{{ chunk.content }}</div>
      </el-card>
    </div>

    <el-pagination
      v-if="total > 0"
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      class="pager"
      @current-change="loadChunks"
    />

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑文档块" width="640px">
      <el-alert
        title="保存后将自动重新向量化并同步到向量数据库"
        type="info"
        :closable="false"
        class="edit-tip"
      />
      <el-input v-model="editContent" type="textarea" :rows="10" maxlength="8192" show-word-limit />
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { kbApi } from '@/api/kb'

const route = useRoute()
const router = useRouter()

const docId = Number(route.params.docId)
const filename = ref(route.query.filename || `文档 ${docId}`)
const kbName = ref(route.query.kb || '')
const chunkSize = ref(route.query.size || '')
const chunkOverlap = ref(route.query.overlap || '')

const chunks = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)

const editDialogVisible = ref(false)
const editContent = ref('')
const editingChunk = ref(null)
const saving = ref(false)

async function loadChunks() {
  loading.value = true
  try {
    const data = await kbApi.listChunks(docId, page.value, pageSize)
    chunks.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openEdit(chunk) {
  editingChunk.value = chunk
  editContent.value = chunk.content
  editDialogVisible.value = true
}

async function submitEdit() {
  if (!editContent.value.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }
  saving.value = true
  try {
    await kbApi.updateChunk(editingChunk.value.id, editContent.value)
    ElMessage.success('已保存并重新向量化')
    editDialogVisible.value = false
    await loadChunks()
  } finally {
    saving.value = false
  }
}

async function removeChunk(chunk) {
  try {
    await ElMessageBox.confirm('确定删除该文档块吗？向量数据将同步删除。', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await kbApi.deleteChunk(chunk.id)
  ElMessage.success('已删除')
  await loadChunks()
}

onMounted(loadChunks)
</script>

<style scoped>
.page-title {
  font-weight: 600;
  color: var(--brand-primary);
}

.doc-infobar {
  display: flex;
  gap: 24px;
  margin-top: 14px;
  padding: 8px 14px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.chunk-list {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chunk-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chunk-index {
  font-weight: 600;
  color: var(--brand-primary);
}

.chunk-chars {
  font-size: 12px;
  color: var(--brand-text-muted);
}

.chunk-actions {
  margin-left: auto;
}

.chunk-content {
  font-size: 13px;
  line-height: 1.8;
  color: var(--brand-text);
  white-space: pre-wrap;
  word-break: break-all;
}

.pager {
  margin-top: 18px;
  justify-content: center;
}

.edit-tip {
  margin-bottom: 12px;
}
</style>
