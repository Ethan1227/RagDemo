<template>
  <div class="consult-page">
    <!-- 左侧：会话列表 -->
    <div class="session-panel">
      <el-button type="primary" class="new-session-btn" @click="createSession">
        <el-icon><Plus /></el-icon>&nbsp;新建对话
      </el-button>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: currentSession?.id === s.id }"
          @click="selectSession(s)"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span class="session-name">{{ s.name }}</span>
          <el-dropdown trigger="click" @click.stop>
            <el-icon class="session-more" @click.stop><MoreFilled /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="renameSession(s)">重命名</el-dropdown-item>
                <el-dropdown-item divided @click="removeSession(s)">
                  <span style="color: var(--el-color-danger)">删除会话</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <!-- 中栏：对话区 -->
    <div class="chat-panel">
      <!-- 会话头：会话名 + 参数面板开关 -->
      <div class="chat-header" v-if="currentSession">
        <span class="chat-title">{{ currentSession.name }}</span>
        <el-button text @click="settingsOpen = !settingsOpen">
          <el-icon><Setting /></el-icon>&nbsp;{{ settingsOpen ? '收起参数' : '模型与参数' }}
        </el-button>
      </div>

      <!-- 消息区 -->
      <div ref="messagesRef" class="messages">
        <el-empty
          v-if="messages.length === 0"
          description="您好，我是法律咨询助手。可咨询诉讼时效、管辖法院、举证责任、诉讼费用、诉讼流程等问题。"
        />
        <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
          <div class="bubble">
            <div
              v-if="msg.role === 'assistant'"
              class="md"
              v-html="renderWithCitations(answerBody(msg), msg.citations)"
              @click="onAnswerClick($event, msg)"
            />
            <div v-else class="plain">{{ msg.content }}</div>

            <!-- 引用来源：点击行内 [n] 角标或此入口打开溯源面板 -->
            <div v-if="msg.citations?.length" class="citation-entry" @click="openSourcePanel(msg)">
              <el-icon><Link /></el-icon>
              <span>引用来源（{{ msg.citations.length }}）· 查看溯源</span>
            </div>

            <!-- 回答末尾统一免责提示条 -->
            <AiNotice v-if="hasNotice(msg)" class="answer-notice" />
          </div>
        </div>
        <div v-if="streaming && !messages.at(-1)?.content" class="message assistant">
          <div class="bubble typing">正在检索知识库并思考…</div>
        </div>
      </div>

      <!-- 输入区：快捷咨询标签 + 文本框 -->
      <div class="composer">
        <div class="quick-tags">
          <el-tag
            v-for="t in QUICK_TOPICS"
            :key="t.label"
            class="quick-tag"
            effect="plain"
            @click="question = t.template"
          >{{ t.label }}</el-tag>
        </div>
        <div class="input-area">
          <el-input
            v-model="question"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="请输入您的法律问题，Enter 发送，Shift+Enter 换行"
            @keydown.enter.exact.prevent="send"
          />
          <el-button
            type="primary"
            class="send-btn"
            :loading="streaming"
            :disabled="!currentSession"
            @click="send"
          >发 送</el-button>
        </div>
      </div>
    </div>

    <!-- 右栏（可折叠）：模型与参数设置面板 -->
    <div v-show="settingsOpen" class="settings-panel">
      <div class="settings-title">模型与参数</div>
      <el-form label-position="top" size="small">
        <el-form-item label="知识库（可多选）">
          <el-checkbox-group v-model="settingsForm.kb_ids" class="kb-checks" @change="saveSettings">
            <el-checkbox v-for="kb in kbList" :key="kb.id" :value="kb.id">{{ kb.name }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="模型">
          <el-select v-model="settingsForm.model" @change="saveSettings">
            <el-option label="qwen-max" value="qwen-max" />
            <el-option label="qwen-plus" value="qwen-plus" />
            <el-option label="qwen-turbo" value="qwen-turbo" />
          </el-select>
        </el-form-item>
        <el-form-item :label="`温度 ${settingsForm.temperature}`">
          <el-slider v-model="settingsForm.temperature" :min="0" :max="2" :step="0.1" @change="saveSettings" />
        </el-form-item>
        <el-form-item :label="`Top P ${settingsForm.top_p}`">
          <el-slider v-model="settingsForm.top_p" :min="0.1" :max="1" :step="0.05" @change="saveSettings" />
        </el-form-item>
        <el-form-item label="最长输出 token">
          <el-input-number v-model="settingsForm.max_tokens" :min="256" :max="8192" :step="256" @change="saveSettings" />
        </el-form-item>
        <el-form-item label="历史对话轮数">
          <el-input-number v-model="settingsForm.history_rounds" :min="0" :max="20" @change="saveSettings" />
        </el-form-item>
      </el-form>
    </div>

    <!-- 溯源面板：展示当前选中回答的引用来源 -->
    <SourcePanel
      v-model="sourceVisible"
      :citations="sourceCitations"
      :active-index="sourceActiveIndex"
    />
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { chatApi, streamChat } from '@/api/chat'
import { kbApi } from '@/api/kb'
import { renderWithCitations, splitDisclaimer } from '@/utils/citation'
import SourcePanel from '@/components/SourcePanel.vue'
import AiNotice from '@/components/AiNotice.vue'

// 常见咨询类型快捷模板（点击填充输入框，用户补充案情后发送）
const QUICK_TOPICS = [
  { label: '诉讼时效', template: '请问我的纠纷是否已过诉讼时效？情况如下：' },
  { label: '管辖法院', template: '请问这类纠纷应向哪个法院起诉，管辖法院如何确定？情况如下：' },
  { label: '举证责任', template: '请问这类案件的举证责任如何分配，我需要准备哪些证据？情况如下：' },
  { label: '诉讼费用', template: '请问提起这类诉讼需要缴纳多少诉讼费，如何计算？诉讼标的额为：' },
  { label: '诉讼流程', template: '请问民事诉讼的完整流程和大致时间周期是怎样的？' },
]

const sessions = ref([])
const currentSession = ref(null)
const messages = ref([])
const kbList = ref([])
const question = ref('')
const streaming = ref(false)
const messagesRef = ref(null)
const settingsOpen = ref(true)

// 溯源面板状态
const sourceVisible = ref(false)
const sourceCitations = ref([])
const sourceActiveIndex = ref(null)

const settingsForm = reactive({
  kb_ids: [],
  model: 'qwen-max',
  temperature: 0.7,
  top_p: 0.8,
  max_tokens: 2048,
  history_rounds: 5,
})

/** 回答正文（剥离末尾免责声明，由 AiNotice 统一展示） */
function answerBody(msg) {
  return splitDisclaimer(msg.content).body
}

function hasNotice(msg) {
  return splitDisclaimer(msg.content).hasDisclaimer
}

/** 点击回答正文中的 [n] 角标时，打开溯源面板并定位到第 n 条来源 */
function onAnswerClick(event, msg) {
  const ref = event.target.closest('.citation-ref')
  if (!ref) return
  openSourcePanel(msg, Number(ref.dataset.index))
}

function openSourcePanel(msg, index = null) {
  sourceCitations.value = msg.citations || []
  sourceActiveIndex.value = index
  sourceVisible.value = true
}

function syncSettings(session) {
  settingsForm.kb_ids = [...(session.kb_ids || [])]
  settingsForm.model = session.model
  settingsForm.temperature = session.temperature
  settingsForm.top_p = session.top_p
  settingsForm.max_tokens = session.max_tokens
  settingsForm.history_rounds = session.history_rounds
}

async function loadSessions() {
  sessions.value = await chatApi.listSessions()
  if (sessions.value.length === 0) {
    const created = await chatApi.createSession()
    sessions.value = [created]
  }
  if (!currentSession.value) {
    await selectSession(sessions.value[0])
  }
}

async function selectSession(session) {
  currentSession.value = session
  syncSettings(session)
  const history = await chatApi.listMessages(session.id)
  messages.value = history.map((m) => ({
    role: m.role,
    content: m.content,
    citations: m.citations || [],
  }))
  scrollToBottom()
}

async function createSession() {
  const created = await chatApi.createSession()
  sessions.value.unshift(created)
  await selectSession(created)
}

async function renameSession(session) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的会话名称', '重命名会话', {
      inputValue: session.name,
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '名称不能为空',
    })
    const updated = await chatApi.updateSession(session.id, { name: value.trim() })
    session.name = updated.name
    ElMessage.success('已重命名')
  } catch {
    /* 用户取消 */
  }
}

async function removeSession(session) {
  try {
    await ElMessageBox.confirm(`确定删除会话「${session.name}」及其全部消息吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await chatApi.deleteSession(session.id)
  sessions.value = sessions.value.filter((s) => s.id !== session.id)
  if (currentSession.value?.id === session.id) {
    currentSession.value = null
    messages.value = []
    if (sessions.value.length > 0) {
      await selectSession(sessions.value[0])
    } else {
      await loadSessions()
    }
  }
  ElMessage.success('已删除')
}

async function saveSettings() {
  if (!currentSession.value) return
  const updated = await chatApi.updateSession(currentSession.value.id, { ...settingsForm })
  Object.assign(currentSession.value, updated)
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function send() {
  const q = question.value.trim()
  if (!q || streaming.value || !currentSession.value) return
  question.value = ''
  messages.value.push({ role: 'user', content: q, citations: [] })
  const assistantMsg = reactive({ role: 'assistant', content: '', citations: [] })
  messages.value.push(assistantMsg)
  streaming.value = true
  scrollToBottom()

  try {
    await streamChat(currentSession.value.id, q, {
      onCitations(citations) {
        assistantMsg.citations = citations
      },
      onDelta(content) {
        assistantMsg.content += content
        scrollToBottom()
      },
      onError(detail) {
        ElMessage.error(detail)
        if (!assistantMsg.content) {
          assistantMsg.content = `⚠️ ${detail}`
        }
      },
    })
  } catch (e) {
    ElMessage.error(e.message || '发送失败')
    if (!assistantMsg.content) {
      assistantMsg.content = `⚠️ ${e.message || '发送失败'}`
    }
  } finally {
    streaming.value = false
    scrollToBottom()
  }
}

onMounted(async () => {
  kbList.value = await kbApi.listKb()
  await loadSessions()
})
</script>

<style scoped>
.consult-page {
  display: flex;
  gap: 16px;
  height: calc(100vh - 170px);
}

/* ---- 会话侧栏 ---- */
.session-panel {
  width: 230px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid var(--brand-border);
  border-radius: var(--radius-base);
  padding: 12px;
  display: flex;
  flex-direction: column;
}

.new-session-btn {
  width: 100%;
  margin-bottom: 12px;
}

.session-list {
  overflow-y: auto;
  flex: 1;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--brand-text);
  font-size: 13px;
  margin-bottom: 4px;
}

.session-item:hover {
  background: var(--el-color-primary-light-9);
}

.session-item.active {
  background: var(--el-color-primary-light-9);
  color: var(--brand-primary);
  font-weight: 600;
}

.session-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-more {
  color: var(--brand-text-muted);
}

/* ---- 对话区 ---- */
.chat-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--brand-border);
  border-radius: var(--radius-base);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--brand-border);
}

.chat-title {
  font-size: var(--font-size-h3);
  font-weight: 600;
  color: var(--brand-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 18px 22px;
}

.message {
  display: flex;
  margin-bottom: 16px;
}

.message.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.75;
}

.message.user .bubble {
  background: var(--brand-primary);
  color: #fff;
  white-space: pre-wrap;
}

/* AI 回答：白底卡片 + 细边框，文档质感而非气泡感 */
.message.assistant .bubble {
  background: var(--color-bg-card);
  color: var(--brand-text);
  border: 1px solid var(--brand-border);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-card);
  max-width: 88%;
}

.answer-notice {
  margin-top: 10px;
}

.bubble.typing {
  color: var(--brand-text-muted);
  font-style: italic;
}

.md :deep(p) {
  margin: 6px 0;
}

.md :deep(h1),
.md :deep(h2),
.md :deep(h3) {
  font-size: 15px;
  margin: 10px 0 6px;
}

.md :deep(ol),
.md :deep(ul) {
  padding-left: 20px;
}

.md :deep(hr) {
  border: none;
  border-top: 1px dashed var(--brand-border);
  margin: 10px 0;
}

/* 行内引用角标（v-html 注入，需 :deep） */
.md :deep(.citation-ref) {
  display: inline-block;
  min-width: 16px;
  padding: 0 3px;
  margin: 0 2px;
  text-align: center;
  font-size: 11px;
  line-height: 16px;
  border-radius: var(--radius-base);
  background: var(--el-color-primary-light-9);
  color: var(--color-primary);
  border: 1px solid var(--el-color-primary-light-7);
  cursor: pointer;
  user-select: none;
}

.md :deep(.citation-ref:hover) {
  background: var(--color-primary);
  color: #fff;
}

/* 回答底部溯源入口 */
.citation-entry {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 10px;
  padding: 4px 10px;
  font-size: 12px;
  color: var(--color-primary);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: var(--radius-base);
  cursor: pointer;
  background: var(--color-bg-card);
}

.citation-entry:hover {
  background: var(--el-color-primary-light-9);
}

.composer {
  border-top: 1px solid var(--brand-border);
  padding: 10px 16px 14px;
}

.quick-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.quick-tag {
  cursor: pointer;
}

.input-area {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.send-btn {
  height: 72px;
  width: 90px;
}

/* ---- 右栏：模型与参数（可折叠） ---- */
.settings-panel {
  width: 260px;
  flex-shrink: 0;
  background: var(--color-bg-card);
  border: 1px solid var(--brand-border);
  border-radius: var(--radius-base);
  padding: 14px 16px;
  overflow-y: auto;
}

.settings-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--brand-primary);
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--brand-border);
}

.kb-checks {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
</style>
