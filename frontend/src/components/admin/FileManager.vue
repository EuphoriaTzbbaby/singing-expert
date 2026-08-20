<template>
  <div class="panel">
    <div class="panel-header">
      <h2>文件管理</h2>
      <div class="actions">
        <input
          v-model="keyword"
          placeholder="搜索文件名…"
          @input="onSearch"
          class="search-input"
        />
        <button @click="load" :disabled="loading">{{ loading ? '加载中…' : '刷新' }}</button>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <table v-if="files.length">
      <thead>
        <tr>
          <th>ID</th>
          <th>文件名</th>
          <th>大小</th>
          <th>上传者</th>
          <th>分组</th>
          <th>上传时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="f in files" :key="f.id">
          <td>{{ f.id }}</td>
          <td>{{ f.original_name }}</td>
          <td>{{ formatSize(f.file_size) }}</td>
          <td>
            <span :class="['badge', f.owner_username ? 'private' : 'public']">
              {{ f.owner_username ?? '公共' }}
            </span>
          </td>
          <td>{{ f.group_name ?? '未分组' }}</td>
          <td>{{ formatDate(f.created_at) }}</td>
          <td class="ops">
            <button @click="onView(f)">查看</button>
            <button @click="onDownload(f)">下载</button>
            <button class="danger" :disabled="actionId === f.id" @click="onDelete(f)">
              {{ actionId === f.id ? '删除中…' : '删除' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">暂无文件</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { adminListFiles, deletePdf, getDownloadUrl } from '../../api'

const files = ref([])
const loading = ref(false)
const error = ref('')
const actionId = ref(null)
const keyword = ref('')
let timer = null

async function load(kw = keyword.value) {
  loading.value = true
  error.value = ''
  try {
    files.value = await adminListFiles(null, null, kw || undefined)
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

function onSearch() {
  clearTimeout(timer)
  timer = setTimeout(() => load(), 300)
}

function onView(f) {
  // 复用 /api/files/{id}/view 同源代理（管理员可见任意文件）
  window.open(`/api/files/${f.id}/view`, '_blank')
}

async function onDownload(f) {
  try {
    const url = await getDownloadUrl(f.id)
    const a = document.createElement('a')
    a.href = url
    a.download = f.original_name
    document.body.appendChild(a)
    a.click()
    a.remove()
  } catch (e) {
    window.alert(e?.response?.data?.detail || '下载失败')
  }
}

async function onDelete(f) {
  if (!window.confirm(`确定删除「${f.original_name}」吗？\nOSS 对象 + 数据库记录会一起删除，不可恢复。`)) return
  actionId.value = f.id
  try {
    await deletePdf(f.id)
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

onMounted(() => load(''))
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
.actions {
  display: flex;
  gap: 8px;
}
.search-input {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  outline: none;
  width: 220px;
}
.search-input:focus {
  border-color: #2563eb;
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
.ops button:hover {
  background: #e5e7eb;
}
.ops .danger {
  background: #ef4444;
  color: #fff;
}
.ops .danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.badge.public {
  background: #fef3c7;
  color: #92400e;
}
.badge.private {
  background: #dbeafe;
  color: #1e40af;
}
.error { color: #dc2626; font-size: 13px; }
.empty { color: #9ca3af; font-size: 13px; padding: 16px; text-align: center; }
</style>
