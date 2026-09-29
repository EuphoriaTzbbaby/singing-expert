<template>
  <div class="login-page">
    <div class="login-orbit orbit-one"></div>
    <div class="login-orbit orbit-two"></div>
    <div class="login-card">
      <div class="brand-mark">C</div>
      <p class="brand-name">cdwswb</p>
      <h1 class="login-title">{{ isRegister ? '创建你的空间' : '欢迎回来' }}</h1>
      <p class="login-subtitle">{{ isRegister ? '建立一个属于你的学习工作台' : '登录以继续你的知识之旅' }}</p>

      <form @submit.prevent="onSubmit">
        <div class="form-field">
          <label>用户名</label>
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            placeholder="输入用户名"
            :disabled="loading"
          />
        </div>

        <div class="form-field">
          <label>密码</label>
          <input
            v-model="password"
            type="password"
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
            placeholder="输入密码"
            :disabled="loading"
          />
        </div>

        <p v-if="isRegister" class="hint">密码至少 6 位</p>

        <p v-if="error" class="error">{{ error }}</p>

        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? '处理中…' : isRegister ? '注册' : '登录' }}
        </button>
      </form>

      <p class="toggle-text" @click="isRegister = !isRegister">
        {{ isRegister ? '已有账号？去登录' : '没有账号？去注册' }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { getMe, login, register } from '../api'
import { setCachedUser } from '../router'

const router = useRouter()

const isRegister = ref(false)
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  error.value = ''
  const u = username.value.trim()
  const p = password.value
  if (!u || !p) {
    error.value = '用户名和密码不能为空'
    return
  }
  if (isRegister.value && p.length < 6) {
    error.value = '密码至少 6 位'
    return
  }

  loading.value = true
  try {
    // 登录/注册成功后，再调一次 /api/auth/me 拿完整 user 对象（含 is_admin）
    await (isRegister.value ? register(u, p) : login(u, p))
    const me = await getMe()
    setCachedUser(me)
    router.push('/')
  } catch (err) {
    error.value = err?.response?.data?.detail || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 48px);
  overflow: hidden;
  background: radial-gradient(circle at 15% 15%, #e8edff 0, transparent 36%), #f5f5f7;
}
.login-card {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, .86);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, .8);
  border-radius: 28px;
  padding: 42px;
  box-shadow: 0 24px 70px rgba(40, 45, 70, .12);
  width: 410px;
  max-width: 90vw;
}
.brand-mark {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  margin: 0 auto 12px;
  border-radius: 14px;
  background: #1d1d1f;
  color: #fff;
  font-size: 23px;
  font-weight: 700;
}
.brand-name { text-align: center; letter-spacing: .2em; font-size: 11px; color: #6e6e73; margin-bottom: 30px; }
.login-title {
  font-size: 30px;
  letter-spacing: -.04em;
  color: #1d1d1f;
  text-align: center;
}
.login-subtitle {
  color: #6e6e73;
  text-align: center;
  margin: 8px 0 30px;
}
.form-field {
  margin-bottom: 16px;
}
.form-field label {
  display: block;
  font-size: 13px;
  color: #4b5563;
  margin-bottom: 6px;
}
.form-field input {
  width: 100%;
  border: 1px solid #d2d2d7;
  border-radius: 12px;
  padding: 13px 14px;
  font-size: 14px;
  outline: none;
}
.form-field input:focus {
  border-color: #1d1d1f;
  box-shadow: 0 0 0 3px rgba(29, 29, 31, .1);
}
.hint {
  font-size: 12px;
  color: #9ca3af;
  margin: -8px 0 16px;
}
.error {
  color: #dc2626;
  font-size: 13px;
  margin-bottom: 12px;
}
.submit-btn {
  width: 100%;
  background: #1d1d1f;
  color: #fff;
  border: none;
  border-radius: 999px;
  padding: 13px;
  font-size: 15px;
  cursor: pointer;
}
.submit-btn:hover:not(:disabled) {
  background: #424245;
}
.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.toggle-text {
  text-align: center;
  color: #6e6e73;
  margin-top: 20px;
  cursor: pointer;
  font-size: 13px;
}
.toggle-text:hover { color: #1d1d1f; }
.login-orbit { position: absolute; border-radius: 50%; filter: blur(2px); opacity: .55; }
.orbit-one { width: 360px; height: 360px; background: #dbe3ff; top: -110px; left: -100px; }
.orbit-two { width: 280px; height: 280px; background: #e8ddff; right: -70px; bottom: -90px; }
</style>
