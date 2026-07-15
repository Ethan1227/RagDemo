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

    <!-- 右侧：对话区 -->
    <div class="chat-panel">
      <!-- 工具栏：知识库多选 + 模型 + 推理参数 -->
      <div class="toolbar" v-if="currentSession">
        <el-select
          v-model="settingsForm.kb_ids"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="选择知识库（可多选）"
          class="kb-select"
          @change="saveSettings"
        >
          <el-option v-for="kb in kbList" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>

        <el-select v-model="settingsForm.model" class="model-select" @change="saveSettings">
          <el-option label="qwen-max" value="qwen-max" />
          <el-option label="qwen-plus" value="qwen-plus" />
          <el-option label="qwen-turbo" value="qwen-turbo" />
        </el-select>

        <el-popover placement="bottom-end" :width="320" trigger="click">
          <template #reference>
            <el-button>
              <el-icon><Setting /></el-icon>&nbsp;推理参数
            </el-button>
          </template>
          <el-form label-width="110px" size="small">
            <el-form-item :label="`温度 ${settingsForm.temperature}`">
              <el-slider v-model="settingsForm.temperature" :min="0" :max="2" :step="0.1" @change="saveSettings" />
            </el-form-item>
            <el-form-item :label="`Top P ${settingsForm.top_p}`">
              <el-slider v-model="settingsForm.top_p" :min="0.1" :max="1" :step="0.05" @change="saveSettings" />
            </el-form-item>
            <el-form-item label="最长输出">
              <el-input-number v-model="settingsForm.max_tokens" :min="256" :max="8192" :step="256" @change="saveSettings" />
            </el-form-item>
            <el-form-item label="历史对话轮数">
              <el-input-number v-model="settingsForm.history_rounds" :min="0" :max="20" @change="saveSettings" />
            </el-form-item>
          </el-form>
        </el-popover>
      </div>

      <!-- 消息区 -->
      <div ref="messagesRef" class="messages">
        <el-empty
          v-if="messages.length === 0"
          description="您好，我是法律咨询助手。可咨询诉讼时效、管辖法院、举证责任、诉讼费用、诉讼流程等问题。"
        />
        <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
          <div class="bubble">
            <div v-if="msg.role === 'assistant'" class="md" v-html="renderMarkdown(msg.content)" />
            <div v-else class="plain">{{ msg.content }}</div>

            <!-- 引用来源 -->
            <el-collapse v-if="msg.citations?.length" class="citations">
              <el-collapse-item :title="`引用来源（${msg.citations.length}）`">
                <div v-for="c in msg.citations" :key="c.index" class="citation-item">
                  <div class="citation-title">
                    [{{ c.index }}] {{ c.kb_name }} / {{ c.filename }}
                    <el-tag size="small" effect="plain">相关度 {{ c.score }}</el-tag>
                  </div>
                  <div class="citation-snippet">{{ c.snippet }}…</div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
        <div v-if="streaming && !messages.at(-1)?.content" class="message assistant">
          <div class="bubble typing">正在检索知识库并思考…</div>
        </div>
      </div>

      <!-- 输入区 -->
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
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { chatApi, streamChat } from '@/api/chat'
import { kbApi } from '@/api/kb'

const sessions = ref([])
const currentSession = ref(null)
const messages = ref([])
const kbList = ref([])
const question = ref('')
const streaming = ref(false)
const messagesRef = ref(null)

const settingsForm = reactive({
  kb_ids: [],
  model: 'qwen-max',
  temperature: 0.7,
  top_p: 0.8,
  max_tokens: 2048,
  history_rounds: 5,
})

function renderMarkdown(text) {
  return DOMPurify.sanitize(marked.parse(text || ''))
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
  border-radius: 10px;
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
  border-radius: 10px;
}

.toolbar {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--brand-border);
}

.kb-select {
  flex: 1;
  max-width: 380px;
}

.model-select {
  width: 140px;
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
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.75;
}

.message.user .bubble {
  background: var(--brand-primary);
  color: #fff;
  white-space: pre-wrap;
}

.message.assistant .bubble {
  background: #f4f6f9;
  color: var(--brand-text);
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

.citations {
  margin-top: 10px;
  --el-collapse-header-height: 34px;
}

.citation-item {
  padding: 8px 0;
  border-bottom: 1px dashed var(--brand-border);
}

.citation-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--brand-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.citation-snippet {
  font-size: 12px;
  color: var(--brand-text-muted);
  margin-top: 4px;
  line-height: 1.6;
}

.input-area {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border-top: 1px solid var(--brand-border);
  align-items: flex-end;
}

.send-btn {
  height: 72px;
  width: 90px;
}
</style>
