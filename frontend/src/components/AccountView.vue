<template>
  <section class="account-view">
    <!-- 个人资料 -->
    <div class="card">
      <h2>个人资料</h2>
      <button class="refresh-btn" @click="loadProfile" :disabled="profileLoading">
        {{ profileLoading ? '加载中…' : '刷新' }}
      </button>
      <p v-if="profileError" class="error">{{ profileError }}</p>
      <table v-if="profile" class="kv-table">
        <tr><td>用户 ID</td><td>{{ profile.id }}</td></tr>
        <tr><td>用户名</td><td>{{ profile.username }}</td></tr>
        <tr>
          <td>角色</td>
          <td>
            <span :class="['badge', profile.is_admin ? 'admin' : 'user']">
              {{ profile.is_admin ? '管理员' : '普通用户' }}
            </span>
          </td>
        </tr>
        <tr><td>注册时间</td><td>{{ formatDate(profile.created_at) }}</td></tr>
        <tr><td>上传文件数</td><td>{{ profile.file_count }}</td></tr>
        <tr><td>占用存储</td><td>{{ formatSize(profile.storage_bytes) }}</td></tr>
      </table>
    </div>

    <!-- 修改密码 -->
    <div class="card">
      <h2>修改密码</h2>
      <form @submit.prevent="onChangePassword">
        <div class="form-field">
          <label>旧密码</label>
          <input
            v-model="oldPwd"
            type="password"
            autocomplete="current-password"
            placeholder="输入当前密码"
            :disabled="pwdLoading"
          />
        </div>
        <div class="form-field">
          <label>新密码</label>
          <input
            v-model="newPwd"
            type="password"
            autocomplete="new-password"
            placeholder="至少 6 位"
            :disabled="pwdLoading"
          />
        </div>
        <div class="form-field">
          <label>确认新密码</label>
          <input
            v-model="confirmPwd"
            type="password"
            autocomplete="new-password"
            placeholder="再输一次新密码"
            :disabled="pwdLoading"
          />
        </div>
        <p v-if="pwdError" class="error">{{ pwdError }}</p>
        <p v-if="pwdSuccess" class="success">{{ pwdSuccess }}</p>
        <button type="submit" class="primary-btn" :disabled="pwdLoading">
          {{ pwdLoading ? '提交中…' : '修改密码' }}
        </button>
      </form>
    </div>

    <!-- 注销账号 -->
    <div class="card danger-card">
      <h2>注销账号</h2>
      <p class="warning">
        ⚠️ 注销后账号不可恢复，你上传的 {{ profile?.file_count ?? 0 }} 个私有文件
        （共 {{ formatSize(profile?.storage_bytes ?? 0) }}）会从 OSS 和数据库一并删除。
      </p>
      <form @submit.prevent="onDeleteSelf">
        <div class="form-field">
          <label>当前密码</label>
          <input
            v-model="deletePwd"
            type="password"
            autocomplete="current-password"
            placeholder="输入当前密码确认注销"
            :disabled="deleteLoading"
          />
        </div>
        <p v-if="deleteError" class="error">{{ deleteError }}</p>
        <button type="submit" class="danger-btn" :disabled="deleteLoading">
          {{ deleteLoading ? '处理中…' : '确认注销账号' }}
        </button>
      </form>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { changePassword, deleteSelf, getProfile } from '../api'

const emit = defineEmits(['logged-out'])

const profile = ref(null)
const profileLoading = ref(false)
const profileError = ref('')

const oldPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')
const pwdLoading = ref(false)
const pwdError = ref('')
const pwdSuccess = ref('')

const deletePwd = ref('')
const deleteLoading = ref(false)
const deleteError = ref('')

async function loadProfile() {
  profileLoading.value = true
  profileError.value = ''
  try {
    profile.value = await getProfile()
  } catch (e) {
    profileError.value = e?.response?.data?.detail || '加载失败'
  } finally {
    profileLoading.value = false
  }
}

async function onChangePassword() {
  pwdError.value = ''
  pwdSuccess.value = ''
  if (!oldPwd.value || !newPwd.value || !confirmPwd.value) {
    pwdError.value = '请填写完整'
    return
  }
  if (newPwd.value.length < 6) {
    pwdError.value = '新密码至少 6 位'
    return
  }
  if (newPwd.value !== confirmPwd.value) {
    pwdError.value = '两次输入的新密码不一致'
    return
  }
  if (oldPwd.value === newPwd.value) {
    pwdError.value = '新密码不能与旧密码相同'
    return
  }
  pwdLoading.value = true
  try {
    await changePassword({ old_password: oldPwd.value, new_password: newPwd.value })
    pwdSuccess.value = '密码已修改，下次登录请使用新密码'
    oldPwd.value = ''
    newPwd.value = ''
    confirmPwd.value = ''
  } catch (e) {
    pwdError.value = e?.response?.data?.detail || '修改失败'
  } finally {
    pwdLoading.value = false
  }
}

async function onDeleteSelf() {
  deleteError.value = ''
  if (!deletePwd.value) {
    deleteError.value = '请输入当前密码确认'
    return
  }
  const ok = window.confirm(
    '最后确认：注销账号不可恢复，所有私有文件会被永久删除。继续吗？'
  )
  if (!ok) return
  deleteLoading.value = true
  try {
    const res = await deleteSelf({ password: deletePwd.value })
    if (res.failed_oss_keys?.length) {
      window.alert(`账号已注销，但有 ${res.failed_oss_keys.length} 个 OSS 对象删除失败，请联系管理员清理`)
    } else {
      window.alert('账号已注销，即将退出登录')
    }
    emit('logged-out')
  } catch (e) {
    deleteError.value = e?.response?.data?.detail || '注销失败'
  } finally {
    deleteLoading.value = false
  }
}

function formatSize(b) {
  if (!b) return '0 B'
  const u = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let v = b
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++ }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${u[i]}`
}

function formatDate(s) {
  if (!s) return ''
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', { hour12: false })
}

onMounted(loadProfile)
</script>

<style scoped>
.account-view {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  position: relative;
}
.card h2 {
  font-size: 18px;
  color: #1f2937;
  margin-bottom: 16px;
}
.danger-card {
  border: 1px solid #fecaca;
}
.refresh-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 14px;
  cursor: pointer;
  font-size: 12px;
}
.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.kv-table {
  width: 100%;
  border-collapse: collapse;
}
.kv-table td {
  padding: 8px 0;
  font-size: 14px;
  border-bottom: 1px solid #f3f4f6;
}
.kv-table td:first-child {
  color: #6b7280;
  width: 140px;
}
.kv-table td:last-child {
  color: #1f2937;
}
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
}
.badge.admin {
  background: #fee2e2;
  color: #991b1b;
}
.badge.user {
  background: #e5e7eb;
  color: #374151;
}
.form-field {
  margin-bottom: 14px;
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
  max-width: 360px;
}
.form-field input:focus {
  border-color: #2563eb;
}
.form-field input:disabled {
  background: #f9fafb;
  cursor: not-allowed;
}
.primary-btn {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
}
.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.danger-btn {
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
}
.danger-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.warning {
  background: #fef3c7;
  color: #92400e;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 16px;
}
.error { color: #dc2626; font-size: 13px; margin-bottom: 8px; }
.success { color: #059669; font-size: 13px; margin-bottom: 8px; }
</style>
