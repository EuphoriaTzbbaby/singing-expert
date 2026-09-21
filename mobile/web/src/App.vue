<template>
  <div class="app">
    <!-- 未登录 → 登录页 -->
    <LoginView v-if="!currentUser" @logged-in="onLoggedIn" />

    <!-- 已登录 → 主界面 -->
    <template v-else>
      <header class="app-header">
        <h1>词汇记忆</h1>
        <div class="user-bar">
          <span class="user-name">{{ currentUser.username }}</span>
          <button class="logout-btn" @click="onLogout">退出</button>
        </div>
      </header>

      <main class="app-body">
        <VocabView v-if="activeView === 'vocab'" />
        <StatsView v-else-if="activeView === 'stats'" />
        <AccountView v-else-if="activeView === 'account'" @logged-out="onLogout" />
        <AdminView v-else-if="activeView === 'admin'" />
      </main>

      <nav class="tabbar">
        <button
          v-for="t in tabs"
          :key="t.key"
          type="button"
          class="tab"
          :class="{ active: activeView === t.key }"
          @click="view = t.key"
        >{{ t.label }}</button>
      </nav>
    </template>
  </div>
</template>

<script setup>
import { Capacitor } from '@capacitor/core'
import { App as CapacitorApp } from '@capacitor/app'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AccountView from './components/AccountView.vue'
import AdminView from './components/AdminView.vue'
import LoginView from './components/LoginView.vue'
import StatsView from './components/StatsView.vue'
import VocabView from './components/VocabView.vue'
import { clearToken, getMe, getToken } from './api'

const currentUser = ref(null) // { id, username, is_admin }
const view = ref('vocab') // 'vocab' | 'stats' | 'account' | 'admin'

// 底部标签栏。管理员会多出一个「管理」。
const tabs = computed(() => {
  const list = [
    { key: 'vocab', label: '词汇' },
    { key: 'stats', label: '统计' },
    { key: 'account', label: '账号' },
  ]
  if (currentUser.value?.is_admin) list.push({ key: 'admin', label: '管理' })
  return list
})

// 兜底：退出登录 / 被取消管理员后，不要停在无权访问的页面上
const activeView = computed(() => {
  const allowed = tabs.value.map((t) => t.key)
  return allowed.includes(view.value) ? view.value : 'vocab'
})

let backListener = null

onMounted(async () => {
  const token = getToken()
  if (token) {
    try {
      currentUser.value = await getMe()
    } catch {
      clearToken()
    }
  }

  // 安卓物理返回键：先退回「词汇」首页，已经是首页才退出 App。
  // 不接管的话，返回键会直接关掉 App，背单词中途很容易误触。
  if (Capacitor.isNativePlatform()) {
    backListener = await CapacitorApp.addListener('backButton', () => {
      if (activeView.value !== 'vocab') {
        view.value = 'vocab'
        return
      }
      CapacitorApp.exitApp()
    })
  }
})

onBeforeUnmount(() => {
  backListener?.remove()
})

function onLoggedIn(user) {
  currentUser.value = user
  view.value = 'vocab'
}

function onLogout() {
  clearToken()
  currentUser.value = null
  view.value = 'vocab'
}
</script>
