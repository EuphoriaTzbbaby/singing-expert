<template>
  <div class="app">
    <!-- 未登录 → 登录页 -->
    <LoginView v-if="!currentUser" @logged-in="onLoggedIn" />

    <!-- 已登录 → 主界面 -->
    <template v-else>
      <header class="app-header">
        <h1>📄 PDF 工具</h1>
        <div class="user-bar">
          <span class="user-name">{{ currentUser.username }}</span>
          <!-- 仅管理员可见：进入管理端 -->
          <button
            v-if="currentUser.is_admin && view === 'user'"
            class="admin-btn"
            @click="enterAdmin"
          >管理端</button>
          <!-- 所有登录用户可见：进入账号设置 -->
          <button
            v-if="view === 'user'"
            class="account-btn"
            @click="enterAccount"
          >账号</button>
          <!-- 所有登录用户可见：进入词汇记忆 -->
          <button
            v-if="view === 'user'"
            class="vocab-btn"
            @click="enterVocab"
          >词汇记忆</button>
          <!-- 所有登录用户可见：进入学习统计 -->
          <button
            v-if="view === 'user'"
            class="stats-btn"
            @click="enterStats"
          >学习统计</button>
          <!-- 管理端/账号视图下：返回用户端 -->
          <button
            v-if="view !== 'user'"
            class="back-btn"
            @click="backToUser"
          >← 返回用户端</button>
          <button class="logout-btn" @click="onLogout">退出</button>
        </div>
      </header>

      <!-- 管理端视图 -->
      <main v-if="view === 'admin'" class="app-body">
        <AdminView />
      </main>

      <!-- 账号视图 -->
      <main v-else-if="view === 'account'" class="app-body">
        <AccountView @logged-out="onLogout" />
      </main>

      <!-- 词汇记忆视图 -->
      <main v-else-if="view === 'vocab'" class="app-body">
        <VocabView />
      </main>

      <!-- 学习统计视图 -->
      <main v-else-if="view === 'stats'" class="app-body">
        <StatsView />
      </main>

      <!-- 用户端视图 -->
      <main v-else class="app-body">
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
import { nextTick, onMounted, ref } from 'vue'
import AccountView from './components/AccountView.vue'
import AdminView from './components/AdminView.vue'
import GroupSidebar from './components/GroupSidebar.vue'
import LoginView from './components/LoginView.vue'
import PdfList from './components/PdfList.vue'
import UploadPanel from './components/UploadPanel.vue'
import VocabView from './components/VocabView.vue'
import StatsView from './components/StatsView.vue'
import { clearToken, getMe, getToken } from './api'

const sidebarRef = ref(null)
const listRef = ref(null)
const currentGroup = ref(undefined)
const groups = ref([])
const currentUser = ref(null) // { id, username, is_admin }
const view = ref('user') // 'user' | 'admin' | 'account' | 'vocab'

// 启动时检查登录状态
onMounted(async () => {
  const token = getToken()
  if (!token) return
  try {
    const user = await getMe()
    currentUser.value = user
  } catch {
    clearToken()
  }
})

function onLoggedIn(user) {
  currentUser.value = user
  view.value = 'user'
}

function onLogout() {
  clearToken()
  currentUser.value = null
  view.value = 'user'
  currentGroup.value = undefined
  groups.value = []
}

function enterAdmin() {
  view.value = 'admin'
}

function enterAccount() {
  view.value = 'account'
}

function enterVocab() {
  view.value = 'vocab'
}

function enterStats() {
  view.value = 'stats'
}

function backToUser() {
  view.value = 'user'
  // 管理员可能在管理端/账号端改了用户/文件，返回时刷新用户端列表
  nextTick(() => refresh())
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
  overflow-x: hidden;
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
.admin-btn {
  background: #10b981;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
}
.admin-btn:hover {
  background: #059669;
}
.account-btn {
  background: #6366f1;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
}
.account-btn:hover {
  background: #4f46e5;
}
.vocab-btn {
  background: #8b5cf6;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
}
.vocab-btn:hover {
  background: #7c3aed;
}
.stats-btn {
  background: #0ea5e9;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
}
.stats-btn:hover {
  background: #0284c7;
}
.back-btn {
  background: #6b7280;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
}
.back-btn:hover {
  background: #4b5563;
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
