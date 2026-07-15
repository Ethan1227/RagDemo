<template>
  <div class="home">
    <el-alert
      title="AI 生成内容仅供参考，不构成正式法律意见"
      type="warning"
      description="本系统基于法律知识库为民事纠纷提供咨询与诉状生成辅助，输出内容请务必核实后使用。"
      show-icon
      :closable="false"
      class="home-alert"
    />

    <el-card class="welcome-card" shadow="never">
      <h2>欢迎，{{ authStore.username }}</h2>
      <p class="subtitle">
        本系统面向标的较小、事实清晰的民事纠纷，提供法律咨询、案件信息管理、证据识别与起诉状生成一站式服务。
      </p>
    </el-card>

    <el-row :gutter="20" class="feature-row">
      <el-col v-for="item in features" :key="item.name" :xs="24" :sm="12" :lg="8">
        <el-card class="feature-card" shadow="hover" @click="go(item.name)">
          <div class="feature-icon"><el-icon><component :is="item.icon" /></el-icon></div>
          <div class="feature-body">
            <div class="feature-title">
              {{ item.title }}
              <el-tag v-if="item.phase" size="small" type="info" effect="plain">
                {{ item.phase }}
              </el-tag>
            </div>
            <div class="feature-desc">{{ item.desc }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const features = [
  { name: 'consult', title: '法律咨询', icon: 'ChatDotRound', phase: '阶段 2', desc: '选择知识库，就诉讼时效、管辖、举证责任等问题智能问答。' },
  { name: 'knowledge', title: '知识库管理', icon: 'Collection', phase: '阶段 2', desc: '导入法律法规、司法解释、类案案例并向量化检索。' },
  { name: 'case', title: '案件信息', icon: 'Document', phase: '阶段 3', desc: '分步填写原被告、案由、诉讼请求与事实理由，支持暂存。' },
  { name: 'evidence', title: '证据材料', icon: 'UploadFilled', phase: '阶段 3', desc: '上传证据并 OCR 识别关键信息，支持分类标注。' },
  { name: 'complaint', title: '起诉状生成', icon: 'EditPen', phase: '阶段 3', desc: '结合案件信息与法律检索，一键生成规范起诉状草稿。' },
]

function go(name) {
  router.push({ name })
}
</script>

<style scoped>
.home-alert {
  margin-bottom: 20px;
}

.welcome-card {
  border: 1px solid var(--brand-border);
  margin-bottom: 20px;
}

.welcome-card h2 {
  margin: 0 0 8px;
  color: var(--brand-primary);
}

.subtitle {
  color: var(--brand-text-muted);
  margin: 0;
  line-height: 1.7;
}

.feature-row {
  margin-top: 4px;
}

.feature-card {
  margin-bottom: 20px;
  cursor: pointer;
  border: 1px solid var(--brand-border);
  transition: transform 0.15s ease;
}

.feature-card:hover {
  transform: translateY(-3px);
}

.feature-card :deep(.el-card__body) {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.feature-icon {
  font-size: 28px;
  color: var(--brand-primary);
  background: var(--el-color-primary-light-9);
  border-radius: 10px;
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.feature-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--brand-text);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.feature-desc {
  font-size: 13px;
  color: var(--brand-text-muted);
  line-height: 1.6;
}
</style>
