<template>
  <section class="pdf-list">
    <div class="header">
      <h2 class="title">{{ headerTitle }}</h2>
      <div class="header-actions">
        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索文件名…"
          @input="onSearch"
        />
        <button class="refresh-btn" :disabled="loading" @click="load()">刷新</button>
      </div>
    </div>

    <div v-if="loading" class="state">加载中…</div>
    <div v-else-if="!files.length" class="state empty">还没有文件，先上传一个吧</div>

    <ul v-else class="list">
      <li v-for="f in files" :key="f.id" class="item">
        <div class="info">
          <div class="name">📄 {{ f.original_name }}</div>
          <div class="meta">
            {{ formatSize(f.file_size) }} · {{ formatDate(f.created_at) }}
          </div>
        </div>
        <div class="actions">
          <select
            class="move-select"
            :value="f.group_id ?? ''"
            @change="onMove(f, $event)"
            title="移动到分组"
          >
            <option value="">— 未分组 —</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">📁 {{ g.name }}</option>
          </select>
          <button class="btn-rename" :disabled="actionId === f.id" @click="onRename(f)">重命名</button>
          <button class="btn-view" :disabled="actionId === f.id" @click="onView(f)">查看</button>
          <button class="btn-download" :disabled="actionId === f.id" @click="onDownload(f)">下载</button>
          <button class="btn-delete" :disabled="actionId === f.id" @click="onDelete(f)">
            {{ actionId === f.id ? '删除中…' : '删除' }}
          </button>
        </div>
      </li>
    </ul>

    <!-- PDF 在线查看弹窗 -->
    <div v-if="viewerUrl" class="viewer-overlay" @click.self="closeViewer">
      <div class="viewer-inner">
        <header class="viewer-header">
          <span class="viewer-title">{{ viewerName }}</span>
          <button class="close-btn" @click="closeViewer">✕ 关闭</button>
        </header>
        <iframe :src="viewerUrl" class="viewer-iframe" title="PDF 预览"></iframe>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { deletePdf, getDownloadUrl, listGroups, listPdfs, updateFile } from '../api'

const props = defineProps({
  groupId: { type: [Number, undefined], default: undefined },
})

const emit = defineEmits(['groups-updated'])

const files = ref([])
const groups = ref([])
const loading = ref(false)
const actionId = ref(null)
const viewerUrl = ref('')
const viewerName = ref('')
const keyword = ref('')
let searchTimer = null

const headerTitle = computed(() => {
  if (props.groupId === undefined) return '已上传文件'
  if (props.groupId === 0) return '未分组文件'
  const g = groups.value.find((x) => x.id === props.groupId)
  return g ? g.name : '已上传文件'
})

async function load(gid = props.groupId, kw = keyword.value) {
  loading.value = true
  try {
    const { data } = await listPdfs(gid, kw)
    files.value = data
  } finally {
    loading.value = false
  }
}

async function loadGroups() {
  const { data } = await listGroups()
  groups.value = data
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => load(props.groupId, keyword.value), 300)
}

async function onMove(f, e) {
  const val = e.target.value
  const targetGroupId = val ? Number(val) : null
  try {
    await updateFile(f.id, { group_id: targetGroupId })
    f.group_id = targetGroupId
    await loadGroups()
    emit('groups-updated')
  } catch (err) {
    const msg = err?.response?.data?.detail || '移动失败'
    window.alert(`移动失败：${msg}`)
    await load()
  }
}

async function onRename(f) {
  const newName = window.prompt('输入新的文件名：', f.original_name)
  if (newName === null) return
  const trimmed = newName.trim()
  if (!trimmed || trimmed === f.original_name) return
  actionId.value = f.id
  try {
    await updateFile(f.id, { original_name: trimmed })
    f.original_name = trimmed
  } catch (err) {
    const msg = err?.response?.data?.detail || '重命名失败'
    window.alert(`重命名失败：${msg}`)
  } finally {
    actionId.value = null
  }
}

async function onView(f) {
  actionId.value = f.id
  try {
    viewerName.value = f.original_name
    viewerUrl.value = `/api/files/${f.id}/view`
  } finally {
    actionId.value = null
  }
}

async function onDownload(f) {
  actionId.value = f.id
  try {
    const url = await getDownloadUrl(f.id)
    const a = document.createElement('a')
    a.href = url
    a.download = f.original_name
    document.body.appendChild(a)
    a.click()
    a.remove()
  } finally {
    actionId.value = null
  }
}

async function onDelete(f) {
  const ok = window.confirm(
    `确定删除「${f.original_name}」吗？\n\n` +
      `文件大小：${formatSize(f.file_size)}\n` +
      `上传时间：${formatDate(f.created_at)}\n\n` +
      `这个操作会同时删除阿里云 OSS 里的文件对象 + 数据库记录，\n` +
      `删除后无法恢复，请确认。`
  )
  if (!ok) return
  actionId.value = f.id
  try {
    await deletePdf(f.id)
    await load(props.groupId)
    await loadGroups()
    emit('groups-updated')
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '删除失败'
    window.alert(`删除失败：${msg}`)
  } finally {
    actionId.value = null
  }
}

function closeViewer() {
  viewerUrl.value = ''
  viewerName.value = ''
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function formatDate(s) {
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => {
  load()
  loadGroups()
})

defineExpose({ load })
</script>

<style scoped>
.pdf-list {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
.title {
  font-size: 18px;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.search-input {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  outline: none;
  width: 180px;
}
.search-input:focus {
  border-color: #2563eb;
}
.refresh-btn {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.state {
  color: #6b7280;
  text-align: center;
  padding: 32px;
}
.state.empty {
  color: #9ca3af;
}
.list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  gap: 12px;
  flex-wrap: wrap;
}
.item:hover {
  border-color: #cbd5e1;
  background: #f9fafb;
}
.info {
  flex: 1;
  min-width: 0;
}
.name {
  font-size: 14px;
  color: #1f2937;
  word-break: break-all;
}
.meta {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}
.actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  align-items: center;
}
.move-select {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 12px;
  color: #6b7280;
  background: #fff;
  cursor: pointer;
  outline: none;
}
.move-select:focus {
  border-color: #2563eb;
}
.btn-rename,
.btn-view,
.btn-download,
.btn-delete {
  color: #fff;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.btn-rename {
  background: #059669;
}
.btn-view {
  background: #2563eb;
}
.btn-download {
  background: #6b7280;
}
.btn-delete {
  background: #dc2626;
}
.btn-rename:hover:not(:disabled) {
  background: #047857;
}
.btn-view:hover:not(:disabled) {
  background: #1d4ed8;
}
.btn-download:hover:not(:disabled) {
  background: #4b5563;
}
.btn-delete:hover:not(:disabled) {
  background: #b91c1c;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.viewer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.viewer-inner {
  width: 90vw;
  height: 88vh;
  background: #fff;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  font-size: 14px;
}
.viewer-title {
  word-break: break-all;
}
.close-btn {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  flex-shrink: 0;
}
.viewer-iframe {
  flex: 1;
  border: none;
  width: 100%;
}
</style>
