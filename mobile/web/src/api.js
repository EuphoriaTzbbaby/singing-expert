import axios from 'axios'
import { Capacitor } from '@capacitor/core'

// ==================== 接口地址 ====================
//
// 原版用相对路径 '/api'，靠 nginx 同源反代。
// 打成 APK 之后，页面来自 App 内部的 https://localhost，和服务器不同源了，
// 所以原生环境必须用绝对地址。
//
// 注意：8000 端口外网是封着的，只能走 nginx 的 8080（它会把 /api 反代到后端）。
// 在电脑浏览器里跑 dev / preview 时仍用 '/api'，交给 vite 代理，方便调试。
const NATIVE_API_BASE = 'http://47.101.42.177:8080/api'

export const API_BASE =
  import.meta.env.VITE_API_BASE ||
  (Capacitor.isNativePlatform() ? NATIVE_API_BASE : '/api')

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60_000,
})

// ==================== Token 管理 ====================

const TOKEN_KEY = 'singing_expert_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

// 请求拦截器：自动带 Bearer token
api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：401 自动清 token（让 App 跳回登录页）
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      clearToken()
    }
    return Promise.reject(err)
  }
)

// ==================== 认证 ====================

export function login(username, password) {
  return api.post('/auth/login', { username, password }).then((r) => {
    setToken(r.data.access_token)
    return r.data
  })
}

export function register(username, password) {
  return api.post('/auth/register', { username, password }).then((r) => {
    setToken(r.data.access_token)
    return r.data
  })
}

export function getMe() {
  return api.get('/auth/me').then((r) => r.data)
}

// 个人资料。返回里还带 file_count / storage_bytes 两个跟 PDF 文件有关的字段，
// 本 App 已去掉 PDF 功能，账号页不再展示这两项（只取注册时间等信息）。
export function getProfile() {
  return api.get('/auth/profile').then((r) => r.data)
}

// 修改自己密码（需验证旧密码）
export function changePassword({ old_password, new_password }) {
  return api.post('/auth/change-password', { old_password, new_password }).then((r) => r.data)
}

// 注销账号（需输入当前密码确认）
export function deleteSelf({ password }) {
  return api.post('/auth/delete-self', { password }).then((r) => r.data)
}

// ==================== 词汇记忆 ====================

// 学习统计仪表盘
export function getVocabStats() {
  return api.get('/vocab/stats').then((r) => r.data)
}

// 分页查询词汇卡片
export function listVocab({ page = 1, pageSize = 10, keyword = '', category = '' } = {}) {
  const params = new URLSearchParams()
  params.append('page', String(page))
  params.append('page_size', String(pageSize))
  if (keyword) params.append('keyword', keyword)
  if (category) params.append('category', category)
  return api.get(`/vocab?${params.toString()}`).then((r) => r.data)
}

// 获取所有到期/新卡片（复习模式用）
export function listVocabDue({ category = '' } = {}) {
  const params = new URLSearchParams()
  if (category) params.append('category', category)
  const qs = params.toString()
  return api.get(`/vocab/due${qs ? `?${qs}` : ''}`).then((r) => r.data)
}

// 新增词汇卡片。force=true 时即使正面重复也强制新增；否则冲突会抛异常
export function createVocab({ front, back, note, category, forceCreate = false }) {
  return api
    .post('/vocab', {
      front,
      back,
      note: note || null,
      category,
      force_create: !!forceCreate,
    })
    .then((r) => r.data)
}

// 更新词汇卡片
export function updateVocab(id, { front, back, note, category }) {
  return api
    .patch(`/vocab/${id}`, { front, back, note: note || null, category })
    .then((r) => r.data)
}

// 背诵评分
// mode: 'flash' 翻卡 / 'type' 看释义拼写 / 'dictation' 听写
export function reviewVocab(id, known, mode = 'flash') {
  return api.post(`/vocab/${id}/review`, { known: !!known, mode }).then((r) => r.data)
}

// AI 生成助记（词根词缀+小故事+记忆技巧）
export function generateAiMnemonic(id) {
  return api.post(`/vocab/${id}/ai-mnemonic`).then((r) => r.data)
}

// 删除词汇卡片
export function deleteVocab(id) {
  return api.delete(`/vocab/${id}`).then((r) => r.data)
}

// ==================== 管理端 ====================
// 只保留「系统统计」和「用户管理」所需接口。
// 原版的文件管理 / 分组管理接口随 PDF 模块一起去掉了。

// 系统统计
export function adminStats() {
  return api.get('/admin/stats').then((r) => r.data)
}

// 列出所有用户（带文件数 + 存储大小）
export function adminListUsers() {
  return api.get('/admin/users').then((r) => r.data)
}

// 修改用户管理员标志
export function adminSetAdmin(userId, { is_admin }) {
  return api.patch(`/admin/users/${userId}/admin`, { is_admin }).then((r) => r.data)
}

// 重置用户密码
export function adminResetPassword(userId, { new_password }) {
  return api.post(`/admin/users/${userId}/reset-password`, { new_password }).then((r) => r.data)
}

// 删除用户
export function adminDeleteUser(userId) {
  return api.delete(`/admin/users/${userId}`).then((r) => r.data)
}

export default api
