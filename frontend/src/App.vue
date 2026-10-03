<template>
  <div class="app">
    <!-- 登录页：全屏独立布局，不带 header -->
    <RouterView v-if="route.name === 'login'" />

    <!-- 已登录 → 主界面 -->
    <template v-else>
      <header class="app-header">
        <h1>cdwswb</h1>
        <div class="user-bar">
          <span v-if="currentUser" class="user-name">{{ currentUser.username }}</span>
          <RouterLink
            v-if="currentUser"
            to="/pdf"
            class="nav-link pdf-btn"
            active-class="active"
          >PDF 文件</RouterLink>
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
          <RouterLink
            v-if="currentUser"
            to="/knowledge"
            class="nav-link knowledge-btn"
            active-class="active"
          >备忘录</RouterLink>
          <RouterLink
            v-if="currentUser"
            to="/focus"
            class="nav-link focus-btn"
            active-class="active"
          >时间记录</RouterLink>
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
:root { --ink:#1d1d1f; --muted:#6e6e73; --line:#e5e5e7; --surface:rgba(255,255,255,.82); --blue:#0071e3; }
* { box-sizing:border-box; margin:0; padding:0; }
html { background:#f5f5f7; }
body { min-width:320px; font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Segoe UI",sans-serif; background:radial-gradient(circle at 10% 0,#eef2ff 0,transparent 34%),#f5f5f7; color:var(--ink); -webkit-font-smoothing:antialiased; }
button,input,textarea,select { font:inherit; }
button { transition:transform .18s ease, background .18s ease, box-shadow .18s ease; }
button:not(:disabled):active { transform:scale(.97); }
.app { width:min(1440px,100%); margin:0 auto; padding:18px 28px 48px; }
.app-header { position:sticky; top:12px; z-index:10; display:flex; justify-content:space-between; align-items:center; gap:24px; margin-bottom:30px; padding:12px 14px 12px 20px; background:rgba(255,255,255,.72); backdrop-filter:blur(22px) saturate(160%); border:1px solid rgba(255,255,255,.8); border-radius:18px; box-shadow:0 8px 30px rgba(0,0,0,.06); }
.app-header h1 { font-size:22px; font-weight:700; letter-spacing:-.04em; color:var(--ink); }
.user-bar { display:flex; align-items:center; gap:7px; flex-wrap:wrap; justify-content:flex-end; }
.user-name { color:var(--muted); font-size:13px; padding:0 8px; }
.nav-link,.logout-btn { border:0; border-radius:999px; padding:8px 13px; cursor:pointer; font-size:12px; text-decoration:none; color:var(--ink); background:transparent; }
.nav-link:hover { background:#e8e8ed; }
.nav-link.active { background:var(--ink); color:#fff; outline:none; }
.admin-btn,.account-btn,.vocab-btn,.spell-btn,.knowledge-btn,.pdf-btn { background:transparent; }
.knowledge-btn { order:1; }
.spell-btn { order:2; }
.vocab-btn { order:3; }
.account-btn { order:4; }
.admin-btn { order:5; }
.pdf-btn { order:6; }
.logout-btn { order:7; }
.logout-btn { background:#ff3b30; color:#fff; padding-inline:15px; }
.logout-btn:hover { background:#d92d25; }
.app-body { display:flex; gap:24px; align-items:flex-start; }
@media (max-width: 820px) { .app { padding:10px 14px 30px; } .app-header { align-items:flex-start; flex-direction:column; gap:12px; } .user-bar { justify-content:flex-start; } .app-body { display:block; } }
/* Shared surface language for the legacy feature views. */
.card, .pdf-list, .upload-panel, .account-view > .card, .admin-view > .card, .sidebar-card { border:1px solid var(--line) !important; border-radius:20px !important; box-shadow:0 8px 26px rgba(0,0,0,.045) !important; }
.primary-btn, .known-btn, .review-btn { background:var(--ink) !important; border-radius:999px !important; }
.ghost-btn, .secondary-btn { border-radius:999px !important; }
.danger-btn, .btn-delete { border-radius:999px !important; }
input, textarea, select { border-color:#d2d2d7 !important; border-radius:12px !important; }
.group-sidebar, .sidebar { border-radius:20px !important; }
</style>
