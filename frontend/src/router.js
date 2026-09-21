import { createRouter, createWebHistory } from 'vue-router'

import AccountView from './components/AccountView.vue'
import AdminView from './components/AdminView.vue'
import HomeView from './components/HomeView.vue'
import LoginView from './components/LoginView.vue'
import SpellTestView from './components/SpellTestView.vue'
import StatsView from './components/StatsView.vue'
import VocabView from './components/VocabView.vue'
import { currentUser, loadUser } from './store.js'

const routes = [
  { path: '/login', name: 'login', component: LoginView },
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { requiresAuth: true, title: '资料库' },
  },
  {
    path: '/vocab',
    name: 'vocab',
    component: VocabView,
    meta: { requiresAuth: true, title: '词汇记忆' },
  },
  {
    path: '/spell',
    name: 'spell',
    component: SpellTestView,
    meta: { requiresAuth: true, title: '拼写测试' },
  },
  {
    path: '/stats',
    name: 'stats',
    component: StatsView,
    meta: { requiresAuth: true, title: '学习统计' },
  },
  {
    path: '/account',
    name: 'account',
    component: AccountView,
    meta: { requiresAuth: true, title: '账号设置' },
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminView,
    meta: { requiresAuth: true, requiresAdmin: true, title: '管理端' },
  },
  // 未知地址回到首页
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  // 首次进入先确认登录状态（刷新页面时 token 还在 localStorage 里）
  if (!currentUser.value) {
    await loadUser()
  }

  if (to.meta.requiresAuth && !currentUser.value) {
    // 记住原本想去哪，登录后跳回去
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresAdmin && !currentUser.value?.is_admin) {
    return { name: 'home' }
  }

  // 已登录就别停在登录页了
  if (to.name === 'login' && currentUser.value) {
    return { name: 'home' }
  }
})

export default router
