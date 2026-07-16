<template>
  <div class="ai-notice" :class="tone">
    <el-icon class="ai-notice-icon">
      <WarningFilled v-if="tone === 'warning'" />
      <InfoFilled v-else />
    </el-icon>
    <span class="ai-notice-text"><slot>{{ DEFAULT_TEXT }}</slot></span>
  </div>
</template>

<script setup>
/**
 * 合规提示条（浅灰底/浅橙底 + 图标 + 小字）。
 * 用于 AI 生成内容的免责声明，全站统一样式，不可被忽略但不过分打扰。
 * tone: info（浅灰，默认）| warning（浅橙，用于文书生成等关键页面）
 */
const DEFAULT_TEXT =
  '以上内容仅供参考，不构成正式法律意见，具体案件建议咨询执业律师。'

defineProps({
  tone: {
    type: String,
    default: 'info',
    validator: (v) => ['info', 'warning'].includes(v),
  },
})
</script>

<style scoped>
.ai-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: var(--font-size-sm);
  line-height: 1.6;
  border-radius: var(--radius-base);
}

.ai-notice.info {
  background: var(--el-color-primary-light-9);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.ai-notice.warning {
  background: var(--el-color-warning-light-9);
  color: var(--color-warning);
  border: 1px solid var(--el-color-warning-light-9);
}

.ai-notice-icon {
  flex-shrink: 0;
}
</style>
