<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h3 class="title">📁 分组</h3>
    </div>

    <ul class="group-list">
      <li
        class="group-item"
        :class="{ active: selected === undefined }"
        @click="select(undefined)"
      >
        <span class="icon">📂</span>
        <span class="name">全部文件</span>
        <span class="count">{{ totalCount }}</span>
      </li>
      <li
        class="group-item"
        :class="{ active: selected === 0 }"
        @click="select(0)"
      >
        <span class="icon">📄</span>
        <span class="name">未分组</span>
        <span class="count">{{ ungroupedCount }}</span>
      </li>
      <li v-if="!groups.length && loaded" class="empty-hint">还没有分组，在下面新建一个吧</li>
      <li v-for="g in groups" :key="g.id" class="group-item" :class="{ active: selected === g.id }">
        <span class="icon">📁</span>
        <span class="name" @click="select(g.id)">{{ g.name }}</span>
        <span class="count">{{ g.file_count }}</span>
        <button class="btn-del-group" title="删除分组" @click.stop="onDelete(g)">✕</button>
      </li>
    </ul>

    <div class="add-form">
      <input
        v-model="newName"
        class="add-input"
        placeholder="新分组名"
        @keyup.enter="onAdd"
      />
      <button class="add-btn" :disabled="!newName.trim()" @click="onAdd">+</button>
    </div>
  </aside>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { createGroup, deleteGroup, listGroups, listPdfs } from '../api'

const emit = defineEmits(['change', 'loaded'])
const groups = ref([])
const selected = ref(undefined)
const newName = ref('')
const loaded = ref(false)
const ungroupedCount = ref(0)

const totalCount = computed(() => groups.value.reduce((s, g) => s + g.file_count, 0) + ungroupedCount.value)

function select(groupId) {
  selected.value = groupId
  emit('change', groupId)
}

async function load() {
  try {
    const [{ data: gList }, { data: ungrouped }] = await Promise.all([
      listGroups(),
      listPdfs(0),
    ])
    groups.value = gList
    ungroupedCount.value = ungrouped.length
    emit('loaded', gList)
  } finally {
    loaded.value = true
  }
}

async function onAdd() {
  const name = newName.value.trim()
  if (!name) return
  try {
    await createGroup(name)
    newName.value = ''
    await load()
  } catch (e) {
    const detail = e?.response?.data?.detail
    window.alert(detail || '创建失败')
  }
}

async function onDelete(g) {
  const ok = window.confirm(`确定删除分组「${g.name}」吗？\n分组内的文件不会被删除，会移到「未分组」。`)
  if (!ok) return
  try {
    await deleteGroup(g.id)
    if (selected.value === g.id) select(undefined)
    await load()
  } catch (e) {
    window.alert('删除失败')
  }
}

defineExpose({ load })

onMounted(load)
</script>

<style scoped>
.sidebar {
  background: #fff;
  border-radius: 12px;
  padding: 20px 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  height: fit-content;
}
.sidebar-header {
  padding: 0 20px 16px;
  border-bottom: 1px solid #f3f4f6;
}
.title {
  font-size: 16px;
  color: #374151;
}
.group-list {
  list-style: none;
  padding: 8px 0;
}
.group-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  cursor: pointer;
  font-size: 14px;
  color: #4b5563;
  transition: background 0.15s;
}
.group-item:hover {
  background: #f9fafb;
}
.group-item.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}
.icon {
  flex-shrink: 0;
}
.name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.count {
  flex-shrink: 0;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}
.group-item.active .count {
  background: #dbeafe;
  color: #2563eb;
}
.btn-del-group {
  flex-shrink: 0;
  background: transparent;
  border: none;
  color: #d1d5db;
  cursor: pointer;
  font-size: 13px;
  padding: 0 4px;
}
.btn-del-group:hover {
  color: #dc2626;
}
.empty-hint {
  padding: 8px 20px;
  font-size: 12px;
  color: #9ca3af;
  text-align: center;
}
.add-form {
  display: flex;
  gap: 8px;
  padding: 12px 20px 0;
  border-top: 1px solid #f3f4f6;
  margin-top: 8px;
}
.add-input {
  flex: 1;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  outline: none;
}
.add-input:focus {
  border-color: #2563eb;
}
.add-btn {
  background: #2563eb;
  color: #fff;
  border: none;
  width: 32px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 18px;
}
.add-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
