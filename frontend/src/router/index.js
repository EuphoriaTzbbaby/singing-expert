import { createRouter, createWebHistory } from 'vue-router'
import { clearToken, getMe, getToken } from '../api'

// ==================== 用户缓存 ====================
// 守卫和 App.vue 都需要当前用户，用模块级缓存避免重复打 /auth/me
let cachedUser = null
let loadingPromise = null

export function getCachedUser() {
  return cachedUser
}

export function clearCachedUser() {
  cachedUser = null
  loadingPromise = null
}

// 登录/注册成功后直接写入缓存，避免再打一次 /auth/me
export function setCachedUser(user) {
  cachedUser = user
  loadingPromise = null
}

// 有 token 就拉一次用户；无 token 直接返回 null；失败清 token 返回 null
export function loadUser() {
  if (cachedUser) return Promise.resolve(cachedUser)
  if (!getToken()) return Promise.resolve(null)
  if (loadingPromise) return loadingPromise
  loadingPromise = getMe()
    .then((u) => {
      cachedUser = u
      return u
    })
    .catch((e) => {
      // 401 拦截器已清 token，这里同步清缓存
      clearToken()
      cachedUser = null
      return null
    })
    .finally(() => {
      loadingPromise = null
    })
  return loadingPromise
}

// ==================== 路由表 ====================
const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../components/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('../components/UserHome.vue'),
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../components/AdminView.vue'),
    meta: { requireAdmin: true },
  },
  {
    path: '/account',
    name: 'account',
    component: () => import('../components/AccountView.vue'),
  },
  {
    path: '/vocab',
    name: 'vocab',
    component: () => import('../components/VocabView.vue'),
  },
  {
    path: '/spell',
    name: 'spell',
    component: () => import('../components/SpellView.vue'),
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ==================== 全局守卫 ====================
router.beforeEach(async (to) => {
  const user = await loadUser()

  // 未登录
  if (!user) {
    if (to.name === 'login') return true
    return { name: 'login' }
  }

  // 已登录访问登录页 → 回首页
  if (to.name === 'login') return { name: 'home' }

  // 管理员路由
  if (to.meta.requireAdmin && !user.is_admin) {
    return { name: 'home' }
  }

  return true
})

export default router
