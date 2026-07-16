<template>
  <el-drawer
    :model-value="modelValue"
    :title="title"
    :size="440"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-empty v-if="citations.length === 0" description="暂无引用来源" :image-size="60" />
    <div v-else class="source-list">
      <div
        v-for="c in citations"
        :key="c.index"
        :ref="(el) => setItemRef(c.index, el)"
        class="source-item"
        :class="{ active: c.index === activeIndex }"
      >
        <div class="source-head">
          <span class="source-badge">{{ c.index }}</span>
          <span class="source-name">{{ c.kb_name }} / {{ c.filename }}</span>
          <el-tag size="small" effect="plain" class="source-score">相关度 {{ c.score }}</el-tag>
        </div>
        <div class="source-snippet">{{ c.snippet }}…</div>
      </div>
    </div>
    <div class="source-footer">来源片段截取自知识库原文，供核对 AI 回答依据使用。</div>
  </el-drawer>
</template>

<script setup>
/**
 * 溯源面板：抽屉式展示 AI 回答 / 文书生成所引用的知识库来源。
 * citations 项结构与后端 SSE citations 事件一致：
 * { index, kb_name, filename, score, snippet }
 */
import { nextTick, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  citations: { type: Array, default: () => [] },
  activeIndex: { type: Number, default: null },
  title: { type: String, default: '引用来源溯源' },
})

defineEmits(['update:modelValue'])

const itemRefs = new Map()

function setItemRef(index, el) {
  if (el) itemRefs.set(index, el)
  else itemRefs.delete(index)
}

// 打开面板或切换角标时，滚动定位到对应来源
watch(
  () => [props.modelValue, props.activeIndex],
  ([visible, index]) => {
    if (!visible || index == null) return
    nextTick(() => {
      itemRefs.get(index)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }
)
</script>

<style scoped>
.source-item {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-base);
  padding: 12px;
  margin-bottom: 12px;
  background: var(--color-bg-card);
  transition: border-color 0.2s, background-color 0.2s;
}

.source-item.active {
  border-color: var(--color-primary);
  background: var(--el-color-primary-light-9);
}

.source-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-badge {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  line-height: 20px;
  text-align: center;
  border-radius: var(--radius-base);
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
}

.source-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-score {
  flex-shrink: 0;
}

.source-snippet {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--color-text-muted);
  white-space: pre-wrap;
}

.source-footer {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-muted);
  border-top: 1px dashed var(--color-border);
  padding-top: 10px;
}
</style>
