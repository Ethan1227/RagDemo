<template>
  <div class="case-page">
    <!-- 左侧：案件列表 -->
    <el-card class="case-list-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>我的案件</span>
          <el-button type="primary" size="small" @click="createCase">
            <el-icon><Plus /></el-icon>&nbsp;新建
          </el-button>
        </div>
      </template>
      <el-empty v-if="cases.length === 0" description="暂无案件" :image-size="60" />
      <div
        v-for="c in cases"
        :key="c.id"
        class="case-item"
        :class="{ active: currentCase?.id === c.id }"
        @click="selectCase(c)"
      >
        <div class="case-item-main">
          <div class="case-title">{{ c.title }}</div>
          <div class="case-meta">
            <el-tag size="small" :type="c.status === 'complete' ? 'success' : 'info'" effect="plain">
              {{ c.status === 'complete' ? '已完成' : '草稿' }}
            </el-tag>
            <span v-if="c.cause" class="case-cause">{{ c.cause }}</span>
          </div>
        </div>
        <el-button link type="danger" size="small" @click.stop="removeCase(c)">删除</el-button>
      </div>
    </el-card>

    <!-- 右侧：Step 表单 -->
    <el-card class="form-card" shadow="never">
      <el-empty v-if="!currentCase" description="请选择或新建一个案件开始填写" />
      <template v-else>
        <el-steps :active="form.current_step" finish-status="success" align-center class="steps">
          <el-step title="当事人信息" />
          <el-step title="案由与诉求" />
          <el-step title="事实与法院" />
          <el-step title="确认提交" />
        </el-steps>

        <!-- 步骤 1：当事人 -->
        <div v-show="form.current_step === 0" class="step-body">
          <div class="party-section">
            <div class="party-head">
              <h4>原告</h4>
              <el-button size="small" @click="addParty('plaintiffs')">
                <el-icon><Plus /></el-icon>&nbsp;添加原告
              </el-button>
            </div>
            <PartyForm
              v-for="(p, i) in form.plaintiffs"
              :key="'p' + i"
              :party="p"
              :index="i"
              @remove="form.plaintiffs.splice(i, 1)"
            />
          </div>
          <div class="party-section">
            <div class="party-head">
              <h4>被告</h4>
              <el-button size="small" @click="addParty('defendants')">
                <el-icon><Plus /></el-icon>&nbsp;添加被告
              </el-button>
            </div>
            <PartyForm
              v-for="(p, i) in form.defendants"
              :key="'d' + i"
              :party="p"
              :index="i"
              @remove="form.defendants.splice(i, 1)"
            />
          </div>
        </div>

        <!-- 步骤 2：案由与诉讼请求 -->
        <div v-show="form.current_step === 1" class="step-body">
          <el-form label-width="90px">
            <el-form-item label="案由">
              <el-select v-model="form.cause" placeholder="请选择案由" filterable @change="onCauseChange">
                <el-option v-for="c in causes" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="诉讼请求">
              <el-input v-model="form.claims" type="textarea" :rows="5"
                placeholder="请分项列明诉讼请求，如：1. 判令被告偿还借款本金……" />
            </el-form-item>
          </el-form>

          <el-card v-if="recommendedLaws.length" class="law-card" shadow="never">
            <template #header>
              <span class="law-title"><el-icon><Reading /></el-icon>&nbsp;推荐参考法条（{{ form.cause }}）</span>
            </template>
            <div v-for="(law, i) in recommendedLaws" :key="i" class="law-item">
              <span class="law-ref">《{{ law.law }}》{{ law.article }}</span>
              <span class="law-summary">{{ law.summary }}</span>
            </div>
          </el-card>
        </div>

        <!-- 步骤 3：事实与法院 -->
        <div v-show="form.current_step === 2" class="step-body">
          <el-form label-width="90px">
            <el-form-item label="事实与理由">
              <el-input v-model="form.facts" type="textarea" :rows="8"
                placeholder="请陈述纠纷发生的经过、双方权利义务关系及被告违约/侵权事实" />
            </el-form-item>
            <el-form-item label="致送法院">
              <el-input v-model="form.court" placeholder="如：北京市朝阳区人民法院" />
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤 4：确认 -->
        <div v-show="form.current_step === 3" class="step-body">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="案由">{{ form.cause || '未填写' }}</el-descriptions-item>
            <el-descriptions-item label="原告">
              {{ form.plaintiffs.map((p) => p.name).filter(Boolean).join('、') || '未填写' }}
            </el-descriptions-item>
            <el-descriptions-item label="被告">
              {{ form.defendants.map((p) => p.name).filter(Boolean).join('、') || '未填写' }}
            </el-descriptions-item>
            <el-descriptions-item label="诉讼请求">{{ form.claims || '未填写' }}</el-descriptions-item>
            <el-descriptions-item label="致送法院">{{ form.court || '未填写' }}</el-descriptions-item>
            <el-descriptions-item label="关联证据">
              {{ relatedEvidenceCount }} 份（在"证据材料"页管理）
            </el-descriptions-item>
          </el-descriptions>
          <el-alert class="next-tip" type="success" :closable="false" show-icon
            title="信息填写完成后，可前往「起诉状生成」页一键生成起诉状草稿。" />
        </div>

        <!-- 操作栏 -->
        <div class="step-actions">
          <el-button v-if="form.current_step > 0" @click="prevStep">上一步</el-button>
          <el-button @click="saveDraft">暂存草稿</el-button>
          <el-button v-if="form.current_step < 3" type="primary" @click="nextStep">下一步</el-button>
          <el-button v-else type="success" @click="submitComplete">完成提交</el-button>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { caseApi } from '@/api/case'
import { evidenceApi } from '@/api/evidence'
import PartyForm from '@/components/PartyForm.vue'

const cases = ref([])
const currentCase = ref(null)
const causes = ref([])
const recommendedLaws = ref([])
const relatedEvidenceCount = ref(0)

const form = reactive({
  current_step: 0,
  cause: '',
  plaintiffs: [],
  defendants: [],
  claims: '',
  facts: '',
  court: '',
})

function emptyParty() {
  return { name: '', id_card: '', address: '', phone: '' }
}

function loadForm(c) {
  form.current_step = c.current_step || 0
  form.cause = c.cause || ''
  form.plaintiffs = c.plaintiffs?.length ? JSON.parse(JSON.stringify(c.plaintiffs)) : [emptyParty()]
  form.defendants = c.defendants?.length ? JSON.parse(JSON.stringify(c.defendants)) : [emptyParty()]
  form.claims = c.claims || ''
  form.facts = c.facts || ''
  form.court = c.court || ''
}

async function loadCases() {
  cases.value = await caseApi.list()
}

async function selectCase(c) {
  currentCase.value = await caseApi.get(c.id)
  loadForm(currentCase.value)
  if (form.cause) await onCauseChange(form.cause)
  const evs = await evidenceApi.list(c.id)
  relatedEvidenceCount.value = evs.length
}

async function createCase() {
  const created = await caseApi.create('未命名案件')
  await loadCases()
  await selectCase(created)
  ElMessage.success('已新建案件')
}

async function removeCase(c) {
  try {
    await ElMessageBox.confirm(`确定删除案件「${c.title}」吗？`, '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await caseApi.remove(c.id)
  if (currentCase.value?.id === c.id) currentCase.value = null
  await loadCases()
  ElMessage.success('已删除')
}

function addParty(key) {
  form[key].push(emptyParty())
}

async function onCauseChange(cause) {
  if (!cause) {
    recommendedLaws.value = []
    return
  }
  const data = await caseApi.recommendLaw(cause)
  recommendedLaws.value = data.items
}

function buildPayload() {
  return {
    current_step: form.current_step,
    cause: form.cause,
    plaintiffs: form.plaintiffs,
    defendants: form.defendants,
    claims: form.claims,
    facts: form.facts,
    court: form.court,
  }
}

async function saveDraft() {
  await caseApi.update(currentCase.value.id, buildPayload())
  await loadCases()
  ElMessage.success('草稿已暂存')
}

async function nextStep() {
  if (form.current_step < 3) form.current_step += 1
  await caseApi.update(currentCase.value.id, buildPayload())
}

function prevStep() {
  if (form.current_step > 0) form.current_step -= 1
}

async function submitComplete() {
  await caseApi.update(currentCase.value.id, { ...buildPayload(), status: 'complete' })
  await loadCases()
  ElMessage.success('案件信息已完成，可前往起诉状生成页')
}

onMounted(async () => {
  causes.value = await caseApi.listCauses()
  await loadCases()
})
</script>

<style scoped>
.case-page {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.case-list-card {
  width: 300px;
  flex-shrink: 0;
}
.form-card {
  flex: 1;
  min-width: 0;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: var(--brand-primary);
}
.case-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 6px;
  border: 1px solid transparent;
}
.case-item:hover,
.case-item.active {
  background: var(--el-color-primary-light-9);
}
.case-item.active {
  border-color: var(--el-color-primary-light-7);
}
.case-title {
  font-weight: 600;
  font-size: 14px;
}
.case-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}
.case-cause {
  font-size: 12px;
  color: var(--brand-text-muted);
}
.steps {
  margin-bottom: 24px;
}
.step-body {
  min-height: 260px;
}
.party-section {
  margin-bottom: 20px;
}
.party-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.party-head h4 {
  margin: 0;
  color: var(--brand-primary);
}
.law-card {
  background: #fbfaf5;
  border: 1px solid #efe3c3;
}
.law-title {
  font-weight: 600;
  color: #8a6d3b;
  display: flex;
  align-items: center;
}
.law-item {
  padding: 6px 0;
  border-bottom: 1px dashed #efe3c3;
  font-size: 13px;
}
.law-ref {
  font-weight: 600;
  color: var(--brand-primary);
  margin-right: 8px;
}
.law-summary {
  color: var(--brand-text-muted);
}
.next-tip {
  margin-top: 16px;
}
.step-actions {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  gap: 12px;
}
</style>
