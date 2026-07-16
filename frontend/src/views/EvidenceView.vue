<template>
  <div class="evidence-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>证据材料</span>
          <el-button type="primary" size="small" @click="uploadDialog = true">
            <el-icon><UploadFilled /></el-icon>&nbsp;上传证据
          </el-button>
        </div>
      </template>

      <el-alert type="info" :closable="false" show-icon class="tip"
        title="支持图片(png/jpg/bmp)、PDF、TXT；上传后自动 OCR 识别并抽取金额/日期/当事人等关键信息。" />

      <el-table :data="evidences" stripe>
        <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.name || row.filename }}</template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="100">
          <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.category }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="file_type" label="类型" width="70" />
        <el-table-column label="OCR 状态" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.ocr_status === 'done'" type="success" size="small">已识别</el-tag>
            <el-tag v-else-if="row.ocr_status === 'failed'" type="danger" size="small">失败</el-tag>
            <el-tag v-else type="warning" size="small">
              <el-icon class="is-loading"><Loading /></el-icon>&nbsp;处理中
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联案件" width="90">
          <template #default="{ row }">{{ caseTitle(row.case_id) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button link type="danger" size="small" @click="removeEvidence(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog v-model="uploadDialog" title="上传证据材料" width="520px">
      <el-upload drag :auto-upload="false" :limit="1" :on-change="(f) => (uploadFile = f.raw)"
        :on-remove="() => (uploadFile = null)" accept=".png,.jpg,.jpeg,.bmp,.pdf,.txt">
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">图片 / PDF / TXT，不超过 20MB</div>
        </template>
      </el-upload>
      <el-form label-width="90px" class="upload-form">
        <el-form-item label="证据分类">
          <el-select v-model="uploadForm.category">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联案件">
          <el-select v-model="uploadForm.caseId" clearable placeholder="可选">
            <el-option v-for="c in cases" :key="c.id" :label="c.title" :value="c.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!uploadFile" @click="submitUpload">
          上传并识别
        </el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="证据详情" size="46%">
      <div v-if="detail" class="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="名称">{{ detail.name || detail.filename }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ detail.category }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusText(detail.ocr_status) }}</el-descriptions-item>
        </el-descriptions>

        <el-alert v-if="detail.ocr_status === 'failed'" type="error" :closable="false"
          class="detail-block" :title="'识别失败：' + detail.error_msg" />

        <template v-if="detail.ocr_status === 'done'">
          <h4 class="detail-title">抽取的关键信息（可修正）</h4>
          <el-form label-width="80px">
            <el-form-item label="当事人">
              <el-input v-model="editParties" placeholder="多个用、分隔" />
            </el-form-item>
            <el-form-item label="金额">
              <el-input v-model="editAmounts" placeholder="多个用、分隔" />
            </el-form-item>
            <el-form-item label="日期">
              <el-input v-model="editDates" placeholder="多个用、分隔" />
            </el-form-item>
            <el-form-item label="摘要">
              <el-input v-model="editSummary" type="textarea" :rows="2" />
            </el-form-item>
            <el-button type="primary" size="small" @click="saveExtracted">保存修正</el-button>
          </el-form>

          <h4 class="detail-title">OCR 识别全文</h4>
          <div class="ocr-text">{{ detail.ocr_text || '（无文本）' }}</div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { evidenceApi } from '@/api/evidence'
import { caseApi } from '@/api/case'

const evidences = ref([])
const cases = ref([])
const categories = ref([])

const uploadDialog = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const uploadForm = reactive({ category: '书证', caseId: null })

const detailVisible = ref(false)
const detail = ref(null)
const editParties = ref('')
const editAmounts = ref('')
const editDates = ref('')
const editSummary = ref('')

let pollTimer = null

function caseTitle(cid) {
  if (cid == null) return '—'
  return cases.value.find((c) => c.id === cid)?.title || `#${cid}`
}

function statusText(s) {
  return { pending: '待处理', processing: '识别中', done: '已识别', failed: '失败' }[s] || s
}

async function loadEvidences() {
  evidences.value = await evidenceApi.list()
  const processing = evidences.value.some((e) => ['pending', 'processing'].includes(e.ocr_status))
  clearTimeout(pollTimer)
  if (processing) pollTimer = setTimeout(loadEvidences, 2500)
}

async function submitUpload() {
  uploading.value = true
  try {
    await evidenceApi.upload(uploadFile.value, uploadForm.category, '', uploadForm.caseId)
    ElMessage.success('上传成功，正在后台识别')
    uploadDialog.value = false
    uploadFile.value = null
    await loadEvidences()
  } finally {
    uploading.value = false
  }
}

async function removeEvidence(row) {
  try {
    await ElMessageBox.confirm(`确定删除证据「${row.name || row.filename}」吗？`, '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await evidenceApi.remove(row.id)
  ElMessage.success('已删除')
  await loadEvidences()
}

async function openDetail(row) {
  detail.value = await evidenceApi.get(row.id)
  const ex = detail.value.extracted || {}
  editParties.value = (ex.parties || []).join('、')
  editAmounts.value = (ex.amounts || []).join('、')
  editDates.value = (ex.dates || []).join('、')
  editSummary.value = ex.summary || ''
  detailVisible.value = true
}

function splitField(v) {
  return v.split(/[、,，]/).map((s) => s.trim()).filter(Boolean)
}

async function saveExtracted() {
  const extracted = {
    parties: splitField(editParties.value),
    amounts: splitField(editAmounts.value),
    dates: splitField(editDates.value),
    summary: editSummary.value,
  }
  await evidenceApi.update(detail.value.id, { extracted })
  ElMessage.success('已保存修正')
  await loadEvidences()
}

onMounted(async () => {
  categories.value = await evidenceApi.listCategories()
  cases.value = await caseApi.list()
  await loadEvidences()
})
onUnmounted(() => clearTimeout(pollTimer))
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: var(--brand-primary);
}
.tip {
  margin-bottom: 16px;
}
.upload-form {
  margin-top: 16px;
}
.detail-title {
  color: var(--brand-primary);
  margin: 18px 0 10px;
}
.detail-block {
  margin-top: 16px;
}
.ocr-text {
  background: #f4f6f9;
  border-radius: 8px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 320px;
  overflow-y: auto;
}
</style>
