<template>
  <section class="upload-panel">
    <div
      class="dropzone"
      :class="{ dragging, disabled: uploading }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
      @click="pickFile"
    >
      <input
        ref="fileInput"
        type="file"
        accept="application/pdf,.pdf"
        hidden
        @change="onSelect"
      />
      <div class="dropzone-inner">
        <div class="icon">⬆️</div>
        <p class="hint">点击或把 PDF 文件拖到这里上传</p>
        <p class="limit">单个文件最大 100MB · 仅支持 PDF</p>
      </div>
    </div>

    <div v-if="uploading" class="progress">
      <div class="bar" :style="{ width: percent + '%' }"></div>
      <span>{{ percent }}%</span>
    </div>

    <p v-if="errorMsg" class="error">⚠ {{ errorMsg }}</p>
    <p v-if="successMsg" class="success">✓ {{ successMsg }}</p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { uploadPdf } from '../api'

const emit = defineEmits(['uploaded'])

const fileInput = ref(null)
const dragging = ref(false)
const uploading = ref(false)
const percent = ref(0)
const errorMsg = ref('')
const successMsg = ref('')

function pickFile() {
  if (uploading.value) return
  fileInput.value?.click()
}

function onSelect(e) {
  const file = e.target.files?.[0]
  handleFile(file)
  e.target.value = ''
}

function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files?.[0]
  handleFile(file)
}

async function handleFile(file) {
  errorMsg.value = ''
  successMsg.value = ''
  if (!file) return

  const isPdf =
    file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  if (!isPdf) {
    errorMsg.value = '只能上传 PDF 文件'
    return
  }

  uploading.value = true
  percent.value = 0
  try {
    await uploadPdf(file, (e) => {
      if (e.total) percent.value = Math.round((e.loaded / e.total) * 100)
    })
    successMsg.value = `已上传：${file.name}`
    emit('uploaded')
  } catch (err) {
    const detail = err?.response?.data?.detail
    errorMsg.value = typeof detail === 'string' ? detail : err?.message || '上传失败'
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.upload-panel {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.dropzone {
  border: 2px dashed #cbd5e1;
  border-radius: 10px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}
.dropzone.dragging {
  border-color: #2563eb;
  background: #eff6ff;
}
.dropzone.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.icon {
  font-size: 36px;
}
.hint {
  margin-top: 8px;
  font-size: 15px;
  color: #374151;
}
.limit {
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
}
.progress {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.progress .bar {
  height: 8px;
  background: #2563eb;
  border-radius: 4px;
  transition: width 0.2s;
  flex: 1;
}
.progress span {
  font-size: 13px;
  color: #6b7280;
  min-width: 40px;
  text-align: right;
}
.error,
.success {
  margin-top: 12px;
  font-size: 13px;
}
.error {
  color: #dc2626;
}
.success {
  color: #059669;
}
</style>
