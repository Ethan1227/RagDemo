<template>
  <AuthShell>
    <div class="auth-head">
      <h2>登录</h2>
      <p>使用账号密码登录系统</p>
    </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="账号" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入账号"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="onSubmit"
          />
        </el-form-item>

        <el-form-item label="图形验证码" prop="captcha_code">
          <div class="captcha-row">
            <el-input
              v-model="form.captcha_code"
              placeholder="请输入验证码"
              :prefix-icon="Key"
            />
            <img
              class="captcha-img"
              :src="captchaImage"
              alt="验证码"
              title="点击刷新验证码"
              @click="refreshCaptcha"
            />
          </div>
        </el-form-item>

        <el-form-item class="auth-actions">
          <el-button type="primary" :loading="loading" @click="onSubmit">
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-switch">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
  </AuthShell>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Key } from '@element-plus/icons-vue'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import AuthShell from '@/components/AuthShell.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)
const captchaImage = ref('')
const form = reactive({
  username: '',
  password: '',
  captcha_id: '',
  captcha_code: '',
})

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

async function refreshCaptcha() {
  const data = await authApi.getCaptcha()
  form.captcha_id = data.captcha_id
  captchaImage.value = data.image
  form.captcha_code = ''
}

async function onSubmit() {
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await authStore.login({ ...form })
      ElMessage.success('登录成功')
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    } catch (e) {
      // 登录失败后刷新验证码
      refreshCaptcha()
    } finally {
      loading.value = false
    }
  })
}

onMounted(refreshCaptcha)
</script>
