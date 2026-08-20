<template>
  <div class="app">
    <!-- 未登录 → 登录页 -->
    <LoginView v-if="!currentUser" @logged-in="onLoggedIn" />

    <!-- 已登录 → 主界面 -->
    <template v-else>
      <header class="app-header">
        <h1>📄 PDF 工具</h1>
        <div class="user-bar">
          <span class="user-name">{{ currentUser }}</span>
          <button class="logout-btn" @click="onLogout">退出</button>
        </div>
      </header>

      <main class="app-body">
        <GroupSidebar ref="sidebarRef" @change="onGroupChange" @loaded="onGroupsLoaded" />
        <div class="app-main">
          <UploadPanel :groups="groups" :current-group="currentGroup" @uploaded="refresh" />
          <PdfList ref="listRef" :group-id="currentGroup" @groups-updated="refreshGroups" />
        </div>
      </main>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import GroupSidebar from './components/GroupSidebar.vue'
import LoginView from './components/LoginView.vue'
import PdfList from './components/PdfList.vue'
import UploadPanel from './components/UploadPanel.vue'
import { clearToken, getMe, getToken } from './api'

const sidebarRef = ref(null)
const listRef = ref(null)
const currentGroup = ref(undefined)
const groups = ref([])
const currentUser = ref(null)

// 启动时检查登录状态
onMounted(async () => {
  const token = getToken()
  if (!token) return
  try {
    const user = await getMe()
    currentUser.value = user.username
  } catch {
    clearToken()
  }
})

function onLoggedIn(username) {
  currentUser.value = username
}

function onLogout() {
  clearToken()
  currentUser.value = null
  currentGroup.value = undefined
  groups.value = []
}

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
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}
.app-header h1 {
  font-size: 28px;
  color: #2563eb;
}
.user-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-name {
  font-size: 14px;
  color: #4b5563;
}
.logout-btn {
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
}
.logout-btn:hover {
  background: #dc2626;
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
