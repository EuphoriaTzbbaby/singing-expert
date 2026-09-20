<template>
  <section class="user-home">
    <GroupSidebar ref="sidebarRef" @change="onGroupChange" @loaded="onGroupsLoaded" />
    <div class="app-main">
      <UploadPanel :groups="groups" :current-group="currentGroup" @uploaded="refresh" />
      <PdfList ref="listRef" :group-id="currentGroup" @groups-updated="refreshGroups" />
    </div>
  </section>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import GroupSidebar from './GroupSidebar.vue'
import PdfList from './PdfList.vue'
import UploadPanel from './UploadPanel.vue'

const sidebarRef = ref(null)
const listRef = ref(null)
const currentGroup = ref(undefined)
const groups = ref([])

function onGroupChange(groupId) {
  currentGroup.value = groupId
  listRef.value?.load(groupId)
}

function onGroupsLoaded(gList) {
  groups.value = gList
}

function refresh() {
  listRef.value?.load(currentGroup.value)
  sidebarRef.value?.load()
}

function refreshGroups() {
  sidebarRef.value?.load()
}

// 暴露给父组件（如管理端返回时刷新）
defineExpose({ refresh, refreshGroups })
</script>

<style scoped>
.user-home {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
}
</style>
