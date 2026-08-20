<template>
  <div class="app">
    <header class="app-header">
      <h1>📄 PDF 工具</h1>
      <p class="subtitle">上传 · 分组 · 在线查看 · 下载</p>
    </header>

    <main class="app-body">
      <GroupSidebar ref="sidebarRef" @change="onGroupChange" @loaded="onGroupsLoaded" />
      <div class="app-main">
        <UploadPanel :groups="groups" :current-group="currentGroup" @uploaded="refresh" />
        <PdfList ref="listRef" :group-id="currentGroup" @groups-updated="refreshGroups" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import GroupSidebar from './components/GroupSidebar.vue'
import UploadPanel from './components/UploadPanel.vue'
import PdfList from './components/PdfList.vue'

const sidebarRef = ref(null)
const listRef = ref(null)
const currentGroup = ref(undefined)
const groups = ref([])

function onGroupChange(groupId) {
  currentGroup.value = groupId
  listRef.value?.load(groupId)
}

function onGroupsLoaded(gList) {
  groups.value = gList
}

function refresh() {
  listRef.value?.load(currentGroup.value)
  sidebarRef.value?.load()
}

function refreshGroups() {
  sidebarRef.value?.load()
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}
.app-header {
  text-align: center;
  margin-bottom: 28px;
}
.app-header h1 {
  font-size: 28px;
  color: #2563eb;
}
.subtitle {
  color: #6b7280;
  margin-top: 4px;
}
.app-body {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
}
</style>
