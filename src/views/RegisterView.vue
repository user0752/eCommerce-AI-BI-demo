<template>
  <div class="register-page">
    <div class="register-bg-decoration">
      <div class="bg-circle c1"></div>
      <div class="bg-circle c2"></div>
      <div class="bg-circle c3"></div>
    </div>

    <div class="register-card">
      <div class="register-header">
        <div class="register-icon">📝</div>
        <h1>用户注册</h1>
        <p class="register-subtitle">注册普通用户账号，体验数据分析功能</p>
      </div>

      <div class="register-form">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <div class="input-wrapper">
            <span class="input-icon">👤</span>
            <input
              type="text"
              v-model="username"
              placeholder="3-20个字符"
              @keydown.enter="handleRegister"
              class="form-input"
              maxlength="20"
            />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <div class="input-wrapper">
            <span class="input-icon">🔒</span>
            <input
              :type="showPassword ? 'text' : 'password'"
              v-model="password"
              placeholder="至少6个字符"
              @keydown.enter="handleRegister"
              class="form-input"
            />
            <button class="toggle-password" @click="showPassword = !showPassword">
              {{ showPassword ? '🙈' : '👁️' }}
            </button>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">确认密码</label>
          <div class="input-wrapper">
            <span class="input-icon">🔒</span>
            <input
              :type="showConfirm ? 'text' : 'password'"
              v-model="confirmPassword"
              placeholder="再次输入密码"
              @keydown.enter="handleRegister"
              class="form-input"
            />
            <button class="toggle-password" @click="showConfirm = !showConfirm">
              {{ showConfirm ? '🙈' : '👁️' }}
            </button>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">验证码</label>
          <div class="captcha-row">
            <div class="input-wrapper captcha-input">
              <span class="input-icon">🛡️</span>
              <input
                type="text"
                v-model="captchaInput"
                placeholder="请输入验证码"
                @keydown.enter="handleRegister"
                class="form-input"
                maxlength="4"
              />
            </div>
            <div class="captcha-image" @click="refreshCaptcha" title="点击刷新验证码">
              <img v-if="captchaImage" :src="captchaImage" alt="验证码" />
              <span v-else class="captcha-text-fallback">{{ captchaText }}</span>
            </div>
          </div>
        </div>

        <div v-if="errorMsg" class="error-message">{{ errorMsg }}</div>
        <div v-if="successMsg" class="success-message">{{ successMsg }}</div>

        <button
          class="register-btn"
          @click="handleRegister"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="btn-loading"></span>
          <span v-else>注 册</span>
        </button>

        <div class="register-footer">
          <span>已有账号？</span>
          <router-link to="/login" class="login-link">返回登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

export default {
  name: 'RegisterView',
  setup() {
    const router = useRouter()
    const username = ref('')
    const password = ref('')
    const confirmPassword = ref('')
    const captchaInput = ref('')
    const captchaImage = ref('')
    const captchaText = ref('')
    const showPassword = ref(false)
    const showConfirm = ref(false)
    const isLoading = ref(false)
    const errorMsg = ref('')
    const successMsg = ref('')

    async function refreshCaptcha() {
      try {
        const res = await api.getCaptcha()
        if (res.data && res.data.captcha) {
          captchaImage.value = res.data.captcha
          captchaText.value = ''
        } else if (res.data && res.data.captcha_text) {
          captchaImage.value = ''
          captchaText.value = res.data.captcha_text
        }
      } catch (err) {
        console.error('获取验证码失败:', err)
      }
    }

    async function handleRegister() {
      errorMsg.value = ''
      successMsg.value = ''

      if (!username.value.trim()) {
        errorMsg.value = '请输入用户名'
        return
      }
      if (username.value.trim().length < 3 || username.value.trim().length > 20) {
        errorMsg.value = '用户名长度需在3-20个字符之间'
        return
      }
      if (!password.value) {
        errorMsg.value = '请输入密码'
        return
      }
      if (password.value.length < 6) {
        errorMsg.value = '密码长度不能少于6个字符'
        return
      }
      if (password.value !== confirmPassword.value) {
        errorMsg.value = '两次输入的密码不一致'
        return
      }
      if (!captchaInput.value.trim()) {
        errorMsg.value = '请输入验证码'
        return
      }

      isLoading.value = true
      try {
        const res = await api.register({
          username: username.value.trim(),
          password: password.value,
          confirm_password: confirmPassword.value,
          captcha: captchaInput.value.trim()
        })

        if (res.code === 200) {
          const { token, user } = res.data
          sessionStorage.setItem('token', token)
          sessionStorage.setItem('user', JSON.stringify(user))
          successMsg.value = '注册成功，正在跳转...'
          setTimeout(() => {
            router.push('/')
          }, 1000)
        } else {
          errorMsg.value = res.message || '注册失败'
          refreshCaptcha()
        }
      } catch (err) {
        if (err.response && err.response.data) {
          errorMsg.value = err.response.data.message || '注册失败'
        } else {
          errorMsg.value = '网络错误，请检查后端服务是否启动'
        }
        refreshCaptcha()
      } finally {
        isLoading.value = false
      }
    }

    onMounted(() => {
      refreshCaptcha()
    })

    return {
      username, password, confirmPassword, captchaInput,
      captchaImage, captchaText,
      showPassword, showConfirm, isLoading,
      errorMsg, successMsg,
      refreshCaptcha, handleRegister
    }
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-neutral-bg);
  position: relative;
  overflow: hidden;
}

.register-bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
}

.c1 {
  width: 500px; height: 500px;
  background: rgba(114, 46, 209, 0.06);
  top: -10%; right: -10%;
  animation: floatSlow 20s ease-in-out infinite alternate;
}

.c2 {
  width: 400px; height: 400px;
  background: rgba(0, 217, 255, 0.05);
  bottom: -10%; left: -5%;
  animation: floatSlow 25s ease-in-out infinite alternate-reverse;
}

.c3 {
  width: 300px; height: 300px;
  background: rgba(24, 144, 255, 0.04);
  top: 40%; left: 50%;
  animation: floatSlow 18s ease-in-out infinite alternate;
}

@keyframes floatSlow {
  0% { transform: translate(0, 0); }
  100% { transform: translate(-30px, -20px); }
}

.register-card {
  width: 420px;
  max-width: 92vw;
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-radius: var(--radius-xl);
  border: 1px solid var(--glass-border);
  padding: var(--spacing-3xl);
  box-shadow: var(--shadow-xl);
  position: relative;
  z-index: 1;
  animation: cardFadeIn 0.6s cubic-bezier(0.2, 0, 0, 1);
}

@keyframes cardFadeIn {
  from { opacity: 0; transform: translateY(24px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.register-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(135deg, #722ED1, #1890FF, #00D9FF);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
}

.register-header {
  text-align: center;
  margin-bottom: var(--spacing-2xl);
}

.register-icon {
  font-size: 3rem;
  display: inline-block;
  margin-bottom: var(--spacing-m);
  filter: drop-shadow(0 0 20px rgba(114, 46, 209, 0.3));
  animation: float 4s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.register-header h1 {
  font-family: var(--font-family-display);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  background: linear-gradient(135deg, #F0F4F8 30%, #722ED1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: var(--spacing-xs);
  letter-spacing: -0.02em;
}

.register-subtitle {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
}

.form-group {
  margin-bottom: var(--spacing-l);
}

.form-label {
  display: block;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xs);
  letter-spacing: 0.02em;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: var(--spacing-m);
  font-size: var(--font-size-s);
  z-index: 1;
  pointer-events: none;
}

.form-input {
  width: 100%;
  padding: 10px 16px 10px 40px;
  border-radius: var(--radius-s);
  border: 1px solid var(--color-neutral-border);
  background: var(--color-neutral-surface);
  color: var(--text-primary);
  font-size: var(--font-size-s);
  font-family: var(--font-family-base);
  outline: none;
  transition: all var(--transition-normal);
}

.form-input:focus {
  border-color: rgba(114, 46, 209, 0.4);
  box-shadow: 0 0 0 3px rgba(114, 46, 209, 0.08), 0 0 20px rgba(114, 46, 209, 0.1);
  background: var(--color-neutral-surface-raised);
}

.form-input::placeholder {
  color: var(--text-tertiary);
}

.toggle-password {
  position: absolute;
  right: var(--spacing-m);
  background: none;
  border: none;
  cursor: pointer;
  font-size: var(--font-size-s);
  padding: 4px;
  line-height: 1;
  opacity: 0.6;
  transition: opacity var(--transition-fast);
}

.toggle-password:hover {
  opacity: 1;
}

.captcha-row {
  display: flex;
  gap: var(--spacing-m);
  align-items: stretch;
}

.captcha-input {
  flex: 1;
}

.captcha-image {
  width: 120px;
  height: 42px;
  border-radius: var(--radius-s);
  border: 1px solid var(--color-neutral-border);
  background: var(--color-neutral-surface);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.captcha-image:hover {
  border-color: rgba(114, 46, 209, 0.3);
  box-shadow: 0 0 20px rgba(114, 46, 209, 0.1);
}

.captcha-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.captcha-text-fallback {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: #722ED1;
  letter-spacing: 4px;
}

.error-message {
  background: rgba(235, 47, 150, 0.1);
  border: 1px solid rgba(235, 47, 150, 0.2);
  color: #EB2F96;
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--radius-s);
  font-size: var(--font-size-xs);
  margin-bottom: var(--spacing-l);
  text-align: center;
}

.success-message {
  background: rgba(82, 196, 26, 0.1);
  border: 1px solid rgba(82, 196, 26, 0.2);
  color: #52C41A;
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--radius-s);
  font-size: var(--font-size-xs);
  margin-bottom: var(--spacing-l);
  text-align: center;
}

.register-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #722ED1, #1890FF);
  color: var(--color-neutral-text-inverse);
  border: none;
  border-radius: var(--radius-s);
  font-size: var(--font-size-m);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--transition-spring);
  box-shadow: 0 0 20px rgba(114, 46, 209, 0.15), 0 0 60px rgba(114, 46, 209, 0.05);
  position: relative;
  overflow: hidden;
  letter-spacing: 0.1em;
}

.register-btn::after {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
  transition: left 0.6s;
}

.register-btn:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.01);
  box-shadow: 0 0 30px rgba(114, 46, 209, 0.25), 0 0 80px rgba(114, 46, 209, 0.08);
}

.register-btn:hover::after {
  left: 100%;
}

.register-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

.btn-loading {
  display: inline-block;
  width: 18px; height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.register-footer {
  text-align: center;
  margin-top: var(--spacing-xl);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.login-link {
  color: #722ED1;
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  margin-left: var(--spacing-xs);
  transition: all var(--transition-fast);
}

.login-link:hover {
  text-decoration: underline;
  text-shadow: 0 0 8px rgba(114, 46, 209, 0.3);
}
</style>
