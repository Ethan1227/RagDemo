<template>
  <div class="kb-page">
    <!-- 左侧：知识库列表 -->
    <el-card class="kb-list-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>知识库</span>
          <el-button type="primary" size="small" @click="createDialogVisible = true">
            <el-icon><Plus /></el-icon>&nbsp;新建
          </el-button>
        </div>
      </template>

      <el-empty v-if="kbList.length === 0" description="暂无知识库，请先创建" />
      <div
        v-for="kb in kbList"
        :key="kb.id"
        class="kb-item"
        :class="{ active: currentKb?.id === kb.id }"
        @click="selectKb(kb)"
      >
        <div class="kb-item-main">
          <el-icon class="kb-icon"><Collection /></el-icon>
          <div>
            <div class="kb-name">{{ kb.name }}</div>
            <div class="kb-meta">
              <el-tag size="small" :type="kb.retrieval_type === 'hybrid' ? 'warning' : 'info'" effect="plain">
                {{ kb.retrieval_type === 'hybrid' ? '混合检索' : '稠密检索' }}
              </el-tag>
              <span class="kb-count">{{ kb.document_count }} 个文档</span>
            </div>
          </div>
        </div>
        <el-button
          link
          type="danger"
          size="small"
          @click.stop="removeKb(kb)"
        >删除</el-button>
      </div>
    </el-card>

    <!-- 右侧：文档管理 -->
    <el-card class="doc-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ currentKb ? `文档列表 —— ${currentKb.name}` : '文档列表' }}</span>
          <el-button
            type="primary"
            size="small"
            :disabled="!currentKb"
            @click="uploadDialogVisible = true"
          >
            <el-icon><UploadFilled /></el-icon>&nbsp;上传文档
          </el-button>
        </div>
      </template>

      <el-empty v-if="!currentKb" description="请先在左侧选择一个知识库" />
      <el-table v-else :data="documents" stripe>
        <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="file_type" label="类型" width="70">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.file_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'done'" type="success" size="small">已完成</el-tag>
            <el-tag v-else-if="row.status === 'parsing'" type="warning" size="small">
              <el-icon class="is-loading"><Loading /></el-icon>&nbsp;解析中
            </el-tag>
            <el-tooltip v-else :content="row.error_msg" placement="top">
              <el-tag type="danger" size="small">失败</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="块数" width="70" />
        <el-table-column label="切块/重叠" width="100">
          <template #default="{ row }">{{ row.chunk_size }}/{{ row.chunk_overlap }}</template>
        </el-table-column>
        <el-table-column label="上传时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              :disabled="row.status !== 'done'"
              @click="goPreview(row)"
            >预览</el-button>
            <el-button link type="danger" size="small" @click="removeDocument(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建知识库对话框 -->
    <el-dialog v-model="createDialogVisible" title="新建知识库" width="480px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="createForm.name" placeholder="如：法律法规库 / 类案案例库" maxlength="128" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" maxlength="512" />
        </el-form-item>
        <el-form-item label="检索方式">
          <el-radio-group v-model="createForm.retrieval_type">
            <el-radio value="dense">稠密向量检索</el-radio>
            <el-radio value="hybrid">混合检索（向量 + 关键词）</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 上传文档对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传文档并配置解析参数" width="520px">
      <el-upload
        drag
        :auto-upload="false"
        :limit="1"
        :on-change="onFileChange"
        :on-remove="() => (uploadFile = null)"
        accept=".pdf,.docx,.md,.markdown,.txt"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PDF / Word(.docx) / Markdown / TXT，不超过 50MB（图片类型将在阶段 3 支持）
          </div>
        </template>
      </el-upload>
      <el-form label-width="110px" class="upload-params">
        <el-form-item label="切块大小(字符)">
          <el-input-number v-model="uploadParams.chunkSize" :min="64" :max="4096" :step="64" />
        </el-form-item>
        <el-form-item label="重叠大小(字符)">
          <el-input-number v-model="uploadParams.chunkOverlap" :min="0" :max="1024" :step="10" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!uploadFile" @click="submitUpload">
          上传并解析
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { kbApi } from '@/api/kb'

const router = useRouter()

const kbList = ref([])
const currentKb = ref(null)
const documents = ref([])

const createDialogVisible = ref(false)
const creating = ref(false)
const createForm = reactive({ name: '', description: '', retrieval_type: 'dense' })

const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const uploadParams = reactive({ chunkSize: 512, chunkOverlap: 50 })

let pollTimer = null

async function loadKbList() {
  kbList.value = await kbApi.listKb()
}

async function selectKb(kb) {
  currentKb.value = kb
  await loadDocuments()
}

async function loadDocuments() {
  if (!currentKb.value) return
  documents.value = await kbApi.listDocuments(currentKb.value.id)
  // 存在解析中的文档时轮询刷新状态（2 秒间隔）
  const hasParsing = documents.value.some((d) => d.status === 'parsing')
  clearTimeout(pollTimer)
  if (hasParsing) {
    pollTimer = setTimeout(loadDocuments, 2000)
  }
}

async function submitCreate() {
  if (!createForm.name.trim()) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  creating.value = true
  try {
    await kbApi.createKb({ ...createForm })
    ElMessage.success('知识库创建成功')
    createDialogVisible.value = false
    Object.assign(createForm, { name: '', description: '', retrieval_type: 'dense' })
    await loadKbList()
  } finally {
    creating.value = false
  }
}

async function removeKb(kb) {
  try {
    await ElMessageBox.confirm(
      `确定删除知识库「${kb.name}」吗？其下所有文档与向量数据将一并删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await kbApi.deleteKb(kb.id)
  ElMessage.success('已删除')
  if (currentKb.value?.id === kb.id) {
    currentKb.value = null
    documents.value = []
  }
  await loadKbList()
}

function onFileChange(file) {
  uploadFile.value = file.raw
}

async function submitUpload() {
  if (uploadParams.chunkOverlap >= uploadParams.chunkSize) {
    ElMessage.warning('重叠大小必须小于切块大小')
    return
  }
  uploading.value = true
  try {
    await kbApi.uploadDocument(
      currentKb.value.id,
      uploadFile.value,
      uploadParams.chunkSize,
      uploadParams.chunkOverlap,
    )
    ElMessage.success('上传成功，正在后台解析')
    uploadDialogVisible.value = false
    uploadFile.value = null
    await loadDocuments()
    await loadKbList()
  } finally {
    uploading.value = false
  }
}

async function removeDocument(doc) {
  try {
    await ElMessageBox.confirm(`确定删除文档「${doc.filename}」及其全部文档块吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await kbApi.deleteDocument(doc.id)
  ElMessage.success('已删除')
  await loadDocuments()
  await loadKbList()
}

function goPreview(doc) {
  router.push({ name: 'knowledge-preview', params: { docId: doc.id }, query: { filename: doc.filename } })
}

function formatTime(value) {
  return value ? value.replace('T', ' ').slice(0, 19) : ''
}

onMounted(loadKbList)
onUnmounted(() => clearTimeout(pollTimer))
</script>

<style scoped>
.kb-page {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.kb-list-card {
  width: 320px;
  flex-shrink: 0;
}

.doc-card {
  flex: 1;
  min-width: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: var(--brand-primary);
}

.kb-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  margin-bottom: 6px;
}

.kb-item:hover {
  background: var(--el-color-primary-light-9);
}

.kb-item.active {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-7);
}

.kb-item-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.kb-icon {
  font-size: 20px;
  color: var(--brand-primary);
  flex-shrink: 0;
}

.kb-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--brand-text);
}

.kb-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.kb-count {
  font-size: 12px;
  color: var(--brand-text-muted);
}

.upload-params {
  margin-top: 16px;
}
</style>
