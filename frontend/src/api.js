import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
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

// ==================== 分组 ====================

// 列出全部分组（带文件数）
export function listGroups() {
  return api.get('/groups')
}

// 创建分组
export function createGroup(name) {
  return api.post('/groups', { name })
}

// 删除分组（文件会移到未分组）
export function deleteGroup(id) {
  return api.delete(`/groups/${id}`).then((r) => r.data)
}

// ==================== PDF 文件 ====================

// 上传 PDF，带进度回调，可选 group_id
export function uploadPdf(file, onUploadProgress, groupId) {
  const form = new FormData()
  form.append('file', file)
  if (groupId) form.append('group_id', groupId)
  return api.post('/files/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
}

// 列出 PDF（可选 group_id 过滤 + keyword 搜索）
export function listPdfs(groupId, keyword) {
  const params = {}
  if (groupId !== undefined) params.group_id = groupId
  if (keyword) params.keyword = keyword
  return api.get('/files', { params })
}

// 更新文件（移动分组 + 重命名）
export function updateFile(id, { group_id, original_name }) {
  const body = {}
  if (group_id !== undefined) body.group_id = group_id ?? null
  if (original_name !== undefined) body.original_name = original_name
  return api.patch(`/files/${id}`, body)
}

// 获取在线查看签名 URL
export function getViewUrl(id) {
  return api.get(`/files/${id}/view-url`).then((r) => r.data.url)
}

// 获取下载签名 URL
export function getDownloadUrl(id) {
  return api.get(`/files/${id}/download-url`).then((r) => r.data.url)
}

// 删除 PDF（后端会同时删 OSS 对象 + MySQL 记录）
export function deletePdf(id) {
  return api.delete(`/files/${id}`).then((r) => r.data)
}

export default api
