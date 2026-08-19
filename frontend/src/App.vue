<template>
  <div class="app">
    <header class="app-header">
      <h1>📄 PDF 工具</h1>
      <p class="subtitle">上传 · 在线查看 · 下载</p>
    </header>

    <main class="app-main">
      <UploadPanel @uploaded="refresh" />
      <PdfList ref="listRef" />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UploadPanel from './components/UploadPanel.vue'
import PdfList from './components/PdfList.vue'

const listRef = ref(null)

function refresh() {
  listRef.value?.load()
}
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #f5f7fa;
  color: #1f2937;
}
.app {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
}
.app-header {
  text-align: center;
  margin-bottom: 32px;
}
.app-header h1 {
  font-size: 28px;
  color: #2563eb;
}
.subtitle {
  color: #6b7280;
  margin-top: 4px;
}
.app-main {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
