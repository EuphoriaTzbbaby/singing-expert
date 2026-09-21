import { ref } from 'vue'
import { clearToken, getMe, getToken } from './api.js'

// 全局登录态：路由守卫和顶栏都要用，所以单独抽出来
export const currentUser = ref(null) // { id, username, is_admin }
export const authReady = ref(false) // 是否已确认过登录状态（避免守卫误判）

/** 启动时确认一次登录状态；没 token 直接跳过请求 */
export async function loadUser() {
  if (!getToken()) {
    currentUser.value = null
    authReady.value = true
    return null
  }
  try {
    currentUser.value = await getMe()
  } catch {
    clearToken()
    currentUser.value = null
  }
  authReady.value = true
  return currentUser.value
}

export function setUser(user) {
  currentUser.value = user
  authReady.value = true
}

export function logout() {
  clearToken()
  currentUser.value = null
}
