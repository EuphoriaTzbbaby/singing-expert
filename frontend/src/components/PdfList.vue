<template>
  <section class="pdf-list">
    <div class="header">
      <h2 class="title">已上传文件</h2>
      <button class="refresh-btn" :disabled="loading" @click="load">刷新</button>
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
          <button
            class="btn-view"
            :disabled="actionId === f.id"
            @click="onView(f)"
          >
            {{ actionId === f.id ? '生成中…' : '查看' }}
          </button>
          <button
            class="btn-download"
            :disabled="actionId === f.id"
            @click="onDownload(f)"
          >
            下载
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
import { onMounted, ref } from 'vue'
import { getDownloadUrl, getViewUrl, listPdfs } from '../api'

const files = ref([])
const loading = ref(false)
const actionId = ref(null)
const viewerUrl = ref('')
const viewerName = ref('')

async function load() {
  loading.value = true
  try {
    const { data } = await listPdfs()
    files.value = data
  } finally {
    loading.value = false
  }
}

async function onView(f) {
  actionId.value = f.id
  try {
    const url = await getViewUrl(f.id)
    viewerName.value = f.original_name
    viewerUrl.value = url
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

onMounted(load)
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
}
.title {
  font-size: 18px;
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
}
.btn-view,
.btn-download {
  color: #fff;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.btn-view {
  background: #2563eb;
}
.btn-download {
  background: #6b7280;
}
.btn-view:hover:not(:disabled) {
  background: #1d4ed8;
}
.btn-download:hover:not(:disabled) {
  background: #4b5563;
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
