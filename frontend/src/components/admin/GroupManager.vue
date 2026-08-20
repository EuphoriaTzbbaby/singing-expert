<template>
  <div class="panel">
    <div class="panel-header">
      <h2>分组管理</h2>
      <button @click="load" :disabled="loading">{{ loading ? '加载中…' : '刷新' }}</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <table v-if="groups.length">
      <thead>
        <tr>
          <th>ID</th>
          <th>分组名</th>
          <th>所属用户</th>
          <th>文件数</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="g in groups" :key="g.id">
          <td>{{ g.id }}</td>
          <td>{{ g.name }}</td>
          <td>
            <span :class="['badge', g.owner_username ? 'private' : 'public']">
              {{ g.owner_username ?? '公共' }}
            </span>
          </td>
          <td>{{ g.file_count }}</td>
          <td>{{ formatDate(g.created_at) }}</td>
          <td>
            <button class="danger" :disabled="actionId === g.id" @click="onDelete(g)">
              {{ actionId === g.id ? '删除中…' : '删除' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">暂无分组</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { adminListGroups, deleteGroup } from '../../api'

const groups = ref([])
const loading = ref(false)
const error = ref('')
const actionId = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    groups.value = await adminListGroups()
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

async function onDelete(g) {
  if (!window.confirm(`确定删除分组「${g.name}」吗？\n该分组下的文件会移动到「未分组」。`)) return
  actionId.value = g.id
  try {
    await deleteGroup(g.id)
    await load()
  } catch (e) {
    window.alert(e?.response?.data?.detail || '删除失败')
  } finally {
    actionId.value = null
  }
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
.danger {
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 4px 12px;
  cursor: pointer;
  font-size: 12px;
}
.danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.error { color: #dc2626; font-size: 13px; }
.empty { color: #9ca3af; font-size: 13px; padding: 16px; text-align: center; }
</style>
