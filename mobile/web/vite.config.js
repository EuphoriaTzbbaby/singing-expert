import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 手机端副本的构建配置。
// 与 frontend/vite.config.js 的区别：代理目标改成线上站点，
// 这样在电脑浏览器里跑 dev / preview 时，/api 请求会转发到 47.101.42.177:8080，
// 不用在本机起后端、也不会撞 CORS。
const API_TARGET = 'http://47.101.42.177:8080'

const apiProxy = {
  '/api': {
    target: API_TARGET,
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: true,
    proxy: apiProxy,
  },
  preview: {
    port: 4173,
    host: true,
    proxy: apiProxy,
  },
})
