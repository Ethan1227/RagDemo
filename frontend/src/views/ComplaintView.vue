<template>
  <div class="complaint-page">
    <el-alert class="disclaimer" type="warning" :closable="false" show-icon
      title="AI 生成内容仅供参考，请核实后使用" description="生成的起诉状为辅助草稿，正式使用前请务必核对当事人信息、诉讼请求与法律依据，必要时咨询执业律师。" />

    <div class="complaint-body">
      <!-- 左：控制区 -->
      <el-card class="control-card" shadow="never">
        <el-form label-position="top">
          <el-form-item label="选择案件">
            <el-select v-model="selectedCaseId" placeholder="请选择已填写的案件" @change="onCaseChange">
              <el-option v-for="c in cases" :key="c.id"
                :label="`${c.title}${c.cause ? '（' + c.cause + '）' : ''}`" :value="c.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="知识库增强（可选）">
            <el-select v-model="selectedKbIds" multiple collapse-tags placeholder="可选，用于补充法条检索">
              <el-option v-for="kb in kbList" :key="kb.id" :label="kb.name" :value="kb.id" />
            </el-select>
          </el-form-item>
          <el-button type="primary" :loading="generating" :disabled="!selectedCaseId" @click="generate" style="width: 100%">
            <el-icon><MagicStick /></el-icon>&nbsp;{{ content ? '重新生成' : '生成起诉状' }}
          </el-button>
        </el-form>

        <div v-if="laws.length" class="laws">
          <div class="laws-title">本案推荐法条</div>
          <div v-for="(l, i) in laws" :key="i" class="law-line">
            《{{ l.law }}》{{ l.article }}
          </div>
        </div>

        <el-divider />
        <div class="history">
          <div class="history-title">历史起诉状</div>
          <el-empty v-if="history.length === 0" description="暂无" :image-size="50" />
          <div v-for="h in history" :key="h.id" class="history-item" @click="loadComplaint(h)">
            <span>{{ h.cause || '起诉状' }} #{{ h.id }}</span>
            <el-button link type="danger" size="small" @click.stop="removeComplaint(h)">删除</el-button>
          </div>
        </div>
      </el-card>

      <!-- 右：文书编辑/预览 -->
      <el-card class="doc-card" shadow="never">
        <template #header>
          <div class="doc-header">
            <span>起诉状{{ editing ? '（编辑中）' : '' }}</span>
            <div class="doc-actions">
              <el-button size="small" :disabled="!content" @click="editing = !editing">
                {{ editing ? '预览' : '编辑' }}
              </el-button>
              <el-button size="small" type="primary" :disabled="!content || !currentComplaintId" @click="save">
                保存
              </el-button>
              <el-button size="small" :disabled="!currentComplaintId" @click="exportWord">导出 Word</el-button>
              <el-button size="small" :disabled="!content" @click="printPdf">打印 / PDF</el-button>
            </div>
          </div>
        </template>

        <el-empty v-if="!content && !generating" description="请选择案件并生成起诉状" />
        <div v-else-if="generating && !content" class="generating">正在生成起诉状草稿…</div>

        <el-input v-else-if="editing" v-model="content" type="textarea" :rows="24" class="editor" />
        <div v-else ref="printArea" class="doc-preview" v-html="renderedContent" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { complaintApi, streamGenerate } from '@/api/complaint'
import { caseApi } from '@/api/case'
import { kbApi } from '@/api/kb'

const cases = ref([])
const kbList = ref([])
const history = ref([])
const selectedCaseId = ref(null)
const selectedKbIds = ref([])
const laws = ref([])

const content = ref('')
const currentComplaintId = ref(null)
const generating = ref(false)
const editing = ref(false)
const printArea = ref(null)

const renderedContent = computed(() => DOMPurify.sanitize(marked.parse(content.value || '')))

async function loadCases() {
  cases.value = await caseApi.list()
}

async function onCaseChange(caseId) {
  content.value = ''
  currentComplaintId.value = null
  laws.value = []
  await loadHistory(caseId)
}

async function loadHistory(caseId) {
  history.value = caseId ? await complaintApi.list(caseId) : []
}

async function generate() {
  generating.value = true
  editing.value = false
  content.value = ''
  laws.value = []
  try {
    await streamGenerate(selectedCaseId.value, selectedKbIds.value, {
      onLaws(l) { laws.value = l },
      onDelta(delta) { content.value += delta },
      onDone(e) {
        currentComplaintId.value = e.complaint_id
        loadHistory(selectedCaseId.value)
      },
      onError(detail) { ElMessage.error(detail) },
    })
    ElMessage.success('生成完成')
  } catch (e) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    generating.value = false
  }
}

async function loadComplaint(h) {
  const data = await complaintApi.get(h.id)
  content.value = data.content
  currentComplaintId.value = data.id
  laws.value = []
  editing.value = false
}

async function save() {
  await complaintApi.update(currentComplaintId.value, content.value)
  ElMessage.success('已保存')
  editing.value = false
}

function exportWord() {
  window.open(complaintApi.exportDocxUrl(currentComplaintId.value), '_blank')
}

function printPdf() {
  const html = renderedContent.value
  const win = window.open('', '_blank')
  win.document.write(`<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
    <title>民事起诉状</title>
    <style>
      body { font-family: '宋体', SimSun, serif; font-size: 15px; line-height: 2; padding: 40px 60px; color: #000; }
      h1 { text-align: center; font-family: '黑体', SimHei; font-size: 24px; }
      h2, h3 { font-family: '黑体', SimHei; }
      p { text-indent: 2em; margin: 8px 0; }
    </style></head><body>${html}</body></html>`)
  win.document.close()
  win.focus()
  setTimeout(() => win.print(), 300)
}

async function removeComplaint(h) {
  try {
    await ElMessageBox.confirm('确定删除该起诉状草稿吗？', '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await complaintApi.remove(h.id)
  if (currentComplaintId.value === h.id) {
    content.value = ''
    currentComplaintId.value = null
  }
  await loadHistory(selectedCaseId.value)
  ElMessage.success('已删除')
}

onMounted(async () => {
  await loadCases()
  kbList.value = await kbApi.listKb()
})
</script>

<style scoped>
.disclaimer {
  margin-bottom: 16px;
}
.complaint-body {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.control-card {
  width: 300px;
  flex-shrink: 0;
}
.doc-card {
  flex: 1;
  min-width: 0;
}
.laws {
  margin-top: 16px;
  background: #fbfaf5;
  border: 1px solid #efe3c3;
  border-radius: 8px;
  padding: 10px 12px;
}
.laws-title,
.history-title {
  font-weight: 600;
  color: var(--brand-primary);
  font-size: 13px;
  margin-bottom: 8px;
}
.law-line {
  font-size: 12px;
  color: #8a6d3b;
  padding: 3px 0;
}
.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.history-item:hover {
  background: var(--el-color-primary-light-9);
}
.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: var(--brand-primary);
}
.doc-actions {
  display: flex;
  gap: 6px;
}
.generating {
  color: var(--brand-text-muted);
  font-style: italic;
  padding: 40px;
  text-align: center;
}
.editor :deep(textarea) {
  font-family: 'Courier New', monospace;
  line-height: 1.9;
}
.doc-preview {
  padding: 20px 30px;
  line-height: 2;
  font-size: 15px;
  min-height: 400px;
}
.doc-preview :deep(h1) {
  text-align: center;
  font-size: 22px;
}
.doc-preview :deep(p) {
  text-indent: 2em;
}
</style>
