<template>
  <el-container class="layout">
    <el-aside class="layout-aside" width="220px">
      <div class="aside-brand">
        <img src="/favicon.svg" alt="logo" />
        <span>法律智能助手</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="transparent"
        text-color="#c9d6e5"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon><span>首页</span>
        </el-menu-item>
        <el-menu-item index="/consult">
          <el-icon><ChatDotRound /></el-icon><span>法律咨询</span>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Collection /></el-icon><span>知识库管理</span>
        </el-menu-item>
        <el-menu-item index="/case">
          <el-icon><Document /></el-icon><span>案件信息</span>
        </el-menu-item>
        <el-menu-item index="/evidence">
          <el-icon><UploadFilled /></el-icon><span>证据材料</span>
        </el-menu-item>
        <el-menu-item index="/complaint">
          <el-icon><EditPen /></el-icon><span>起诉状生成</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-title">{{ currentTitle }}</div>
        <div class="header-user">
          <el-icon><UserFilled /></el-icon>
          <span>{{ authStore.username }}</span>
          <el-button link type="primary" @click="onLogout">退出登录</el-button>
        </div>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>

      <div class="disclaimer-bar">
        ⚖️ 本系统由 AI 生成内容仅供参考，不构成正式法律意见，具体案件建议咨询执业律师。
      </div>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '首页')

async function onLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
    authStore.logout()
    ElMessage.success('已退出登录')
    router.push({ name: 'login' })
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.layout {
  height: 100vh;
}

.layout-aside {
  background: linear-gradient(180deg, #142a45 0%, #1d3a5f 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.aside-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.aside-brand img {
  width: 30px;
  height: 30px;
}

.layout-aside :deep(.el-menu) {
  border-right: none;
  padding-top: 8px;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid var(--brand-border);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--brand-primary);
}

.header-user {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--brand-text-muted);
  font-size: 14px;
}

.layout-main {
  background: var(--brand-bg);
  padding: 24px;
}
</style>
