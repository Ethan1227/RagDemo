<template>
  <div class="auth-split">
    <!-- 左：品牌视觉区（深蓝底 + 线性天平图形） -->
    <div class="brand-pane">
      <div class="brand-inner">
        <svg
          class="brand-figure"
          viewBox="0 0 120 120"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          aria-hidden="true"
        >
          <circle cx="60" cy="14" r="4" />
          <line x1="60" y1="18" x2="60" y2="86" />
          <line x1="24" y1="30" x2="96" y2="30" />
          <line x1="24" y1="30" x2="14" y2="54" />
          <line x1="24" y1="30" x2="34" y2="54" />
          <path d="M10 54 A14 14 0 0 0 38 54" />
          <line x1="96" y1="30" x2="86" y2="54" />
          <line x1="96" y1="30" x2="106" y2="54" />
          <path d="M82 54 A14 14 0 0 0 110 54" />
          <line x1="42" y1="92" x2="78" y2="92" />
          <line x1="34" y1="100" x2="86" y2="100" />
        </svg>
        <h1 class="brand-name">民事纠纷诉状生成与咨询系统</h1>
        <p class="brand-tagline">专业 · 严谨 · 可信赖的法律智能助手</p>
      </div>
    </div>

    <!-- 右：表单区 -->
    <div class="form-pane">
      <div class="form-inner">
        <slot />
      </div>
      <div class="form-footer">
        AI 生成内容仅供参考，不构成正式法律意见 · © 2026 民事纠纷诉状生成与咨询系统
      </div>
    </div>
  </div>
</template>

<script setup>
// 登录/注册页共用的左右分栏外壳：左品牌视觉区，右表单插槽。
</script>

<style scoped>
.auth-split {
  display: flex;
  min-height: 100vh;
}

.brand-pane {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    160deg,
    var(--color-primary-dark) 0%,
    var(--color-primary) 60%,
    var(--color-primary-light) 100%
  );
  color: rgba(255, 255, 255, 0.85);
}

.brand-inner {
  text-align: center;
  padding: 40px;
  /* 视觉重心居中偏上 */
  transform: translateY(-6vh);
}

.brand-figure {
  width: 120px;
  height: 120px;
  opacity: 0.9;
}

.brand-name {
  font-size: var(--font-size-h1);
  font-weight: 600;
  letter-spacing: 2px;
  margin: 28px 0 10px;
  color: #fff;
}

.brand-tagline {
  font-size: var(--font-size-base);
  color: rgba(255, 255, 255, 0.65);
  letter-spacing: 4px;
  margin: 0;
}

.form-pane {
  width: 480px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-card);
  border-left: 1px solid var(--color-border);
}

.form-inner {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 40px 56px;
  /* 视觉重心居中偏上 */
  padding-bottom: 14vh;
}

.form-footer {
  padding: 14px 24px;
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  border-top: 1px solid var(--color-border);
}

/* 窄屏：品牌区收起，仅保留表单 */
@media (max-width: 860px) {
  .brand-pane {
    display: none;
  }
  .form-pane {
    width: 100%;
    border-left: none;
  }
}
</style>
