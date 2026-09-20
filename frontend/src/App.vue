<template>
  <div class="app">
    <!-- 登录页：全屏独立布局，不带 header -->
    <RouterView v-if="route.name === 'login'" />

    <!-- 已登录 → 主界面 -->
    <template v-else>
      <header class="app-header">
        <h1>📄 PDF 工具</h1>
        <div class="user-bar">
          <span v-if="currentUser" class="user-name">{{ currentUser.username }}</span>
          <!-- 仅管理员可见：进入管理端 -->
          <RouterLink
            v-if="currentUser?.is_admin"
            to="/admin"
            class="nav-link admin-btn"
            active-class="active"
          >管理端</RouterLink>
          <!-- 所有登录用户可见：进入账号设置 -->
          <RouterLink
            v-if="currentUser"
            to="/account"
            class="nav-link account-btn"
            active-class="active"
          >账号</RouterLink>
          <!-- 所有登录用户可见：进入词汇记忆 -->
          <RouterLink
            v-if="currentUser"
            to="/vocab"
            class="nav-link vocab-btn"
            active-class="active"
          >词汇记忆</RouterLink>
          <!-- 所有登录用户可见：拼写测试 -->
          <RouterLink
            v-if="currentUser"
            to="/spell"
            class="nav-link spell-btn"
            active-class="active"
          >拼写测试</RouterLink>
          <!-- 返回用户端（在非首页路由显示） -->
          <RouterLink
            v-if="currentUser && route.path !== '/'"
            to="/"
            class="nav-link back-btn"
            active-class="active"
          >← 返回用户端</RouterLink>
          <button class="logout-btn" @click="onLogout">退出</button>
        </div>
      </header>

      <main class="app-body">
        <RouterView />
      </main>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearToken, getMe } from './api'
import { clearCachedUser, getCachedUser, loadUser } from './router'

const route = useRoute()
const router = useRouter()

const currentUser = ref(null)

// 启动时从缓存/接口拿当前用户（守卫已经会调 loadUser，这里复用缓存）
onMounted(async () => {
  const u = await loadUser()
  currentUser.value = u
})

// 路由变化时同步 currentUser（登录成功后 cachedUser 会被 setCachedUser 更新）
watch(() => route.path, () => {
  const cached = getCachedUser()
  if (cached !== currentUser.value) {
    currentUser.value = cached
  }
})

function onLogout() {
  clearToken()
  clearCachedUser()
  currentUser.value = null
  router.push('/login')
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
.nav-link {
  border-radius: 6px;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
  text-decoration: none;
  color: #fff;
}
.nav-link.active {
  outline: 2px solid #1f2937;
  outline-offset: 1px;
}
.admin-btn { background: #10b981; }
.admin-btn:hover { background: #059669; }
.account-btn { background: #6366f1; }
.account-btn:hover { background: #4f46e5; }
.vocab-btn { background: #8b5cf6; }
.vocab-btn:hover { background: #7c3aed; }
.spell-btn { background: #f59e0b; }
.spell-btn:hover { background: #d97706; }
.back-btn { background: #6b7280; }
.back-btn:hover { background: #4b5563; }
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
</style>
