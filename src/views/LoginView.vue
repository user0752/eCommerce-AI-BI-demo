<template>
  <div class="login-page">
    <div class="login-bg-decoration">
      <div class="bg-circle c1"></div>
      <div class="bg-circle c2"></div>
      <div class="bg-circle c3"></div>
    </div>

    <div class="login-card">
      <div class="login-header">
        <div class="login-icon">🌏</div>
        <h1>黔数智析</h1>
        <p class="login-subtitle">基于本地大模型的区域电商智能可视化分析平台</p>
      </div>

      <div class="login-form">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <div class="input-wrapper">
            <span class="input-icon">👤</span>
            <input
              type="text"
              v-model="username"
              placeholder="请输入用户名"
              @keydown.enter="handleLogin"
              class="form-input"
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
              placeholder="请输入密码"
              @keydown.enter="handleLogin"
              class="form-input"
            />
            <button class="toggle-password" @click="showPassword = !showPassword">
              {{ showPassword ? '🙈' : '👁️' }}
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
                @keydown.enter="handleLogin"
                class="form-input"
                maxlength="4"
              />
            </div>
            <div class="captcha-image" @click="refreshCaptcha" :title="'点击刷新验证码'">
              <img v-if="captchaImage" :src="captchaImage" alt="验证码" />
              <span v-else class="captcha-text-fallback">{{ captchaText }}</span>
            </div>
          </div>
        </div>

        <div class="form-options">
          <label class="remember-me">
            <input type="checkbox" v-model="rememberMe" />
            <span>记住登录状态</span>
          </label>
        </div>

        <div v-if="errorMsg" class="error-message">{{ errorMsg }}</div>

        <button
          class="login-btn"
          @click="handleLogin"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="btn-loading"></span>
          <span v-else>登 录</span>
        </button>

        <div class="login-footer">
          <span>还没有账号？</span>
          <router-link to="/register" class="register-link">立即注册</router-link>
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
  name: 'LoginView',
  setup() {
    const router = useRouter()
    const username = ref('')
    const password = ref('')
    const captchaInput = ref('')
    const captchaImage = ref('')
    const captchaText = ref('')
    const showPassword = ref(false)
    const rememberMe = ref(false)
    const isLoading = ref(false)
    const errorMsg = ref('')

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

    async function handleLogin() {
      errorMsg.value = ''

      if (!username.value.trim()) {
        errorMsg.value = '请输入用户名'
        return
      }
      if (!password.value.trim()) {
        errorMsg.value = '请输入密码'
        return
      }
      if (!captchaInput.value.trim()) {
        errorMsg.value = '请输入验证码'
        return
      }

      isLoading.value = true
      try {
        const res = await api.login({
          username: username.value.trim(),
          password: password.value,
          captcha: captchaInput.value.trim(),
          remember: rememberMe.value
        })

        if (res.code === 200) {
          const { token, user } = res.data
          const storage = rememberMe.value ? localStorage : sessionStorage
          storage.setItem('token', token)
          storage.setItem('user', JSON.stringify(user))
          if (!rememberMe.value) {
            localStorage.removeItem('token')
            localStorage.removeItem('user')
          }
          router.push('/')
        } else {
          errorMsg.value = res.message || '登录失败'
          refreshCaptcha()
        }
      } catch (err) {
        if (err.response && err.response.data) {
          errorMsg.value = err.response.data.message || '登录失败'
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
      username, password, captchaInput,
      captchaImage, captchaText,
      showPassword, rememberMe, isLoading, errorMsg,
      refreshCaptcha, handleLogin
    }
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-neutral-bg);
  position: relative;
  overflow: hidden;
}

.login-bg-decoration {
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
  background: rgba(0, 217, 255, 0.06);
  top: -10%; left: -10%;
  animation: floatSlow 20s ease-in-out infinite alternate;
}

.c2 {
  width: 400px; height: 400px;
  background: rgba(114, 46, 209, 0.05);
  bottom: -10%; right: -5%;
  animation: floatSlow 25s ease-in-out infinite alternate-reverse;
}

.c3 {
  width: 300px; height: 300px;
  background: rgba(24, 144, 255, 0.04);
  top: 50%; left: 60%;
  animation: floatSlow 18s ease-in-out infinite alternate;
}

@keyframes floatSlow {
  0% { transform: translate(0, 0); }
  100% { transform: translate(-30px, -20px); }
}

.login-card {
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

.login-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--color-accent-gradient);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
}

.login-header {
  text-align: center;
  margin-bottom: var(--spacing-2xl);
}

.login-icon {
  font-size: 3rem;
  display: inline-block;
  margin-bottom: var(--spacing-m);
  filter: drop-shadow(0 0 20px rgba(0, 217, 255, 0.3));
  animation: float 4s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.login-header h1 {
  font-family: var(--font-family-display);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  background: linear-gradient(135deg, #F0F4F8 30%, #00D9FF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: var(--spacing-xs);
  letter-spacing: -0.02em;
}

.login-subtitle {
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
  border-color: rgba(0, 217, 255, 0.4);
  box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.08), var(--shadow-glow);
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
  border-color: rgba(0, 217, 255, 0.3);
  box-shadow: var(--shadow-glow);
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
  color: #00D9FF;
  letter-spacing: 4px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-l);
}

.remember-me {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  cursor: pointer;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  user-select: none;
}

.remember-me input[type="checkbox"] {
  width: 14px;
  height: 14px;
  accent-color: #00D9FF;
  cursor: pointer;
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

.login-btn {
  width: 100%;
  padding: 12px;
  background: var(--color-accent-gradient);
  color: var(--color-neutral-text-inverse);
  border: none;
  border-radius: var(--radius-s);
  font-size: var(--font-size-m);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--transition-spring);
  box-shadow: var(--shadow-glow);
  position: relative;
  overflow: hidden;
  letter-spacing: 0.1em;
}

.login-btn::after {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
  transition: left 0.6s;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.01);
  box-shadow: var(--shadow-glow-strong);
}

.login-btn:hover::after {
  left: 100%;
}

.login-btn:disabled {
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

.login-footer {
  text-align: center;
  margin-top: var(--spacing-xl);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.register-link {
  color: #00D9FF;
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  margin-left: var(--spacing-xs);
  transition: all var(--transition-fast);
}

.register-link:hover {
  text-decoration: underline;
  text-shadow: 0 0 8px rgba(0, 217, 255, 0.3);
}
</style>
