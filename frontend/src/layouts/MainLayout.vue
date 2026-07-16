<template>
  <el-container class="layout">
    <el-aside class="layout-aside" width="220px">
      <div class="aside-brand">
        <img src="/favicon.svg" alt="logo" />
        <span>法律智能助手</span>
      </div>
      <el-menu :default-active="activeMenu" router class="aside-menu">
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
        <div class="main-inner">
          <router-view />
        </div>
      </el-main>

      <AiNotice class="layout-disclaimer" />
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import AiNotice from '@/components/AiNotice.vue'

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
  background: linear-gradient(
    180deg,
    var(--color-primary-dark) 0%,
    var(--color-primary) 100%
  );
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
  background: transparent;
}

/* 深色侧栏上的菜单项：白色系分级，避免硬编码品牌色 */
.aside-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.72);
}

.aside-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.aside-menu :deep(.el-menu-item.is-active) {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
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
  font-size: var(--font-size-h3);
  font-weight: 600;
  color: var(--brand-primary);
}

.header-user {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--brand-text-muted);
  font-size: var(--font-size-base);
}

.layout-main {
  background: var(--brand-bg);
  padding: 24px;
}

/* 内容区限宽居中（1280px），两侧留白 */
.main-inner {
  max-width: var(--content-max-width);
  margin: 0 auto;
  height: 100%;
}

.layout-disclaimer {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-bottom: none;
  justify-content: center;
}
</style>
