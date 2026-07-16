<template>
  <AuthShell>
    <div class="auth-head">
      <h2>注册新账号</h2>
      <p>创建账号以使用法律咨询与诉状生成服务</p>
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
            placeholder="3-32 位，不含空格"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="至少 6 位"
            :prefix-icon="Lock"
            show-password
          />
          <!-- 密码强度：细窄进度条 + 文字（灰→橙→绿） -->
          <div v-if="strength.level > 0" class="pwd-strength">
            <div class="pwd-track">
              <div class="pwd-fill" :class="`level-${strength.level}`" />
            </div>
            <span class="pwd-label" :class="`level-${strength.level}`">{{ strength.label }}</span>
          </div>
        </el-form-item>

        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            type="password"
            placeholder="请再次输入密码"
            :prefix-icon="Lock"
            show-password
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
            注 册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-switch">
        已有账号？<router-link to="/login">返回登录</router-link>
      </div>
  </AuthShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Key } from '@element-plus/icons-vue'
import { authApi } from '@/api/auth'
import AuthShell from '@/components/AuthShell.vue'
import { scorePassword } from '@/utils/password'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const captchaImage = ref('')
const form = reactive({
  username: '',
  password: '',
  confirm_password: '',
  captcha_id: '',
  captcha_code: '',
})

const strength = computed(() => scorePassword(form.password))

function validateConfirm(rule, value, callback) {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { min: 3, max: 32, message: '账号长度为 3-32 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度为 6-64 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    // change 触发：输入过程中即时提示不一致，不用弹窗打断
    { validator: validateConfirm, trigger: ['blur', 'change'] },
  ],
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
      await authApi.register({ ...form })
      ElMessage.success('注册成功，请登录')
      router.push({ name: 'login' })
    } catch (e) {
      refreshCaptcha()
    } finally {
      loading.value = false
    }
  })
}

onMounted(refreshCaptcha)
</script>

<style scoped>
/* 密码强度：细窄进度条 + 文字，颜色克制（灰→橙→绿） */
.pwd-strength {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  margin-top: 6px;
}

.pwd-track {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: var(--color-border);
  overflow: hidden;
}

.pwd-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.2s, background-color 0.2s;
}

.pwd-fill.level-1 {
  width: 33%;
  background: var(--color-text-placeholder);
}

.pwd-fill.level-2 {
  width: 66%;
  background: var(--color-warning);
}

.pwd-fill.level-3 {
  width: 100%;
  background: var(--color-success);
}

.pwd-label {
  font-size: var(--font-size-sm);
  line-height: 1;
}

.pwd-label.level-1 {
  color: var(--color-text-muted);
}

.pwd-label.level-2 {
  color: var(--color-warning);
}

.pwd-label.level-3 {
  color: var(--color-success);
}
</style>
