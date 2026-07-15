<template>
  <div class="placeholder">
    <el-result icon="info" :title="title" :sub-title="subTitle">
      <template #extra>
        <el-tag type="warning" effect="plain" size="large">
          {{ route.meta.phase || '开发中' }}
        </el-tag>
      </template>
    </el-result>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => `${route.meta.title} 功能开发中`)
const subTitle = computed(
  () => `该模块将在${route.meta.phase || '后续阶段'}交付，敬请期待。`,
)
</script>

<style scoped>
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}
</style>
