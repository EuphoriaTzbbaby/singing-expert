<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">📄 PDF 工具</h1>
      <p class="login-subtitle">{{ isRegister ? '注册新账号' : '登录' }}</p>

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
import { login, register } from '../api'

const emit = defineEmits(['logged-in'])

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
    const data = isRegister.value
      ? await register(u, p)
      : await login(u, p)
    emit('logged-in', data.username)
  } catch (err) {
    error.value = err?.response?.data?.detail || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
}
.login-card {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  width: 360px;
  max-width: 90vw;
}
.login-title {
  font-size: 26px;
  color: #2563eb;
  text-align: center;
}
.login-subtitle {
  color: #6b7280;
  text-align: center;
  margin: 4px 0 24px;
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
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  outline: none;
}
.form-field input:focus {
  border-color: #2563eb;
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
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 12px;
  font-size: 15px;
  cursor: pointer;
}
.submit-btn:hover:not(:disabled) {
  background: #1d4ed8;
}
.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.toggle-text {
  text-align: center;
  color: #2563eb;
  margin-top: 20px;
  cursor: pointer;
  font-size: 13px;
}
</style>
