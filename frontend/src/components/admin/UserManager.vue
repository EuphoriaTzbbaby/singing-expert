<template>
  <div class="panel">
    <div class="panel-header">
      <h2>用户管理</h2>
      <button @click="load" :disabled="loading">{{ loading ? '加载中…' : '刷新' }}</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <table v-if="users.length">
      <thead>
        <tr>
          <th>ID</th>
          <th>用户名</th>
          <th>角色</th>
          <th>文件数</th>
          <th>存储</th>
          <th>注册时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id" :class="{ self: u.id === me?.id }">
          <td>{{ u.id }}</td>
          <td>
            {{ u.username }}
            <span v-if="u.id === me?.id" class="self-tag">（你）</span>
          </td>
          <td>
            <span :class="['badge', u.is_admin ? 'admin' : 'user']">
              {{ u.is_admin ? '管理员' : '普通用户' }}
            </span>
          </td>
          <td>{{ u.file_count }}</td>
          <td>{{ formatSize(u.storage_bytes) }}</td>
          <td>{{ formatDate(u.created_at) }}</td>
          <td class="ops">
            <button
              :disabled="u.id === me?.id || actionId === u.id"
              @click="onToggleAdmin(u)"
            >{{ u.is_admin ? '取消管理员' : '设为管理员' }}</button>
            <button
              :disabled="u.id === me?.id || actionId === u.id"
              @click="onResetPwd(u)"
            >重置密码</button>
            <button
              class="danger"
              :disabled="u.id === me?.id || actionId === u.id"
              @click="onDelete(u)"
            >删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">暂无用户</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import {
  adminDeleteUser,
  adminListUsers,
  adminResetPassword,
  adminSetAdmin,
  getMe,
} from '../../api'

const users = ref([])
const me = ref(null) // 当前管理员自己，用于禁用自操作
const loading = ref(false)
const error = ref('')
const actionId = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [list, self] = await Promise.all([adminListUsers(), getMe()])
    users.value = list
    me.value = self
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

async function onToggleAdmin(u) {
  const ok = window.confirm(`确定将「${u.username}」${u.is_admin ? '取消' : '设为'}管理员？`)
  if (!ok) return
  actionId.value = u.id
  try {
    await adminSetAdmin(u.id, { is_admin: !u.is_admin })
    u.is_admin = !u.is_admin
  } catch (e) {
    window.alert(e?.response?.data?.detail || '操作失败')
  } finally {
    actionId.value = null
  }
}

async function onResetPwd(u) {
  const pwd = window.prompt(`为「${u.username}」设置新密码（至少 6 位）：`)
  if (pwd === null) return
  if (pwd.length < 6) {
    window.alert('密码至少 6 位')
    return
  }
  actionId.value = u.id
  try {
    await adminResetPassword(u.id, { new_password: pwd })
    window.alert('密码已重置')
  } catch (e) {
    window.alert(e?.response?.data?.detail || '重置失败')
  } finally {
    actionId.value = null
  }
}

async function onDelete(u) {
  const ok = window.confirm(
    `确定删除用户「${u.username}」吗？\n` +
    `该用户的 ${u.file_count} 个私有文件会一并从 OSS 和数据库删除。\n此操作不可恢复。`
  )
  if (!ok) return
  actionId.value = u.id
  try {
    const res = await adminDeleteUser(u.id)
    if (res.failed_oss_keys?.length) {
      window.alert(`用户已删除，但有 ${res.failed_oss_keys.length} 个 OSS 对象删除失败，需手动清理`)
    }
    await load()
  } catch (e) {
    window.alert(e?.response?.data?.detail || '删除失败')
  } finally {
    actionId.value = null
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

onMounted(load)
</script>

<style scoped>
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.panel-header h2 {
  font-size: 18px;
  color: #1f2937;
}
.panel-header button {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
}
.panel-header button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  overflow: hidden;
}
th, td {
  padding: 10px 14px;
  text-align: left;
  font-size: 13px;
  border-bottom: 1px solid #f3f4f6;
}
th {
  background: #f9fafb;
  color: #6b7280;
  font-weight: 600;
}
tr.self {
  background: #fffbeb;
}
.self-tag {
  color: #d97706;
  font-size: 12px;
}
.badge {
  display: inline-block;
  padding: 2px 8px;
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
.ops {
  display: flex;
  gap: 6px;
}
.ops button {
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 6px;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 12px;
}
.ops button:hover:not(:disabled) {
  background: #e5e7eb;
}
.ops button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ops .danger {
  background: #ef4444;
  color: #fff;
}
.ops .danger:disabled {
  opacity: 0.6;
}
.error { color: #dc2626; font-size: 13px; }
.empty { color: #9ca3af; font-size: 13px; padding: 16px; text-align: center; }
</style>
