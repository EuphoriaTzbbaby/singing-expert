<template>
  <div class="app-body">
    <GroupSidebar ref="sidebarRef" @change="onGroupChange" @loaded="onGroupsLoaded" />
    <div class="app-main">
      <UploadPanel :groups="groups" :current-group="currentGroup" @uploaded="refresh" />
      <PdfList ref="listRef" :group-id="currentGroup" @groups-updated="refreshGroups" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
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
</script>
