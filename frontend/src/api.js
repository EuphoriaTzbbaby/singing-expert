import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60_000,
})

// 上传 PDF，带进度回调
export function uploadPdf(file, onUploadProgress) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/files/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
}

// 列出全部 PDF
export function listPdfs() {
  return api.get('/files')
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
