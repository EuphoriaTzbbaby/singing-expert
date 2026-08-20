<template>
  <section class="admin-view">
    <nav class="tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        :class="['tab', { active: active === t.key }]"
        @click="active = t.key"
      >{{ t.label }}</button>
    </nav>
    <component :is="currentComponent" />
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import FileManager from './admin/FileManager.vue'
import GroupManager from './admin/GroupManager.vue'
import StatsPanel from './admin/StatsPanel.vue'
import UserManager from './admin/UserManager.vue'

const tabs = [
  { key: 'stats', label: '系统统计', comp: StatsPanel },
  { key: 'users', label: '用户管理', comp: UserManager },
  { key: 'files', label: '文件管理', comp: FileManager },
  { key: 'groups', label: '分组管理', comp: GroupManager },
]
const active = ref('stats')
const currentComponent = computed(() => tabs.find((t) => t.key === active.value).comp)
</script>

<style scoped>
.admin-view {
  flex: 1;
  min-width: 0;
}
.tabs {
  display: flex;
  gap: 8px;
  border-bottom: 2px solid #e5e7eb;
  margin-bottom: 20px;
}
.tab {
  background: transparent;
  border: none;
  padding: 10px 20px;
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}
.tab:hover {
  color: #2563eb;
}
.tab.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
  font-weight: 600;
}
</style>
