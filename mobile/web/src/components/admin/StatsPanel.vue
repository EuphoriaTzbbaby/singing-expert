<template>
  <div class="panel">
    <div class="panel-header">
      <h2>系统统计</h2>
      <button @click="load" :disabled="loading">{{ loading ? '加载中…' : '刷新' }}</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="cards" v-if="stats">
      <div class="card">
        <div class="num">{{ stats.user_count }}</div>
        <div class="label">用户数</div>
      </div>
    </div>

    <p class="empty">
      本 App 未包含 PDF 模块。文件数、总存储、分组、上传记录等统计请到网页端查看。
    </p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { adminStats } from '../../api'

const stats = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    stats.value = await adminStats()
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.panel-header h2 {
  font-size: 18px;
  color: #1f2937;
}
.panel-header button {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
}
.panel-header button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.card .num {
  font-size: 24px;
  font-weight: 600;
  color: #2563eb;
}
.card .label {
  font-size: 13px;
  color: #6b7280;
  margin-top: 4px;
}
.section-title {
  font-size: 15px;
  color: #374151;
  margin-bottom: 12px;
}
table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  overflow: hidden;
}
th, td {
  padding: 10px 14px;
  text-align: left;
  font-size: 13px;
  border-bottom: 1px solid #f3f4f6;
}
th {
  background: #f9fafb;
  color: #6b7280;
  font-weight: 600;
}
.error { color: #dc2626; font-size: 13px; }
.empty { color: #9ca3af; font-size: 13px; padding: 16px; text-align: center; }
</style>
