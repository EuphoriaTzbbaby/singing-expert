<template>
  <section class="vocab-view">
    <!-- 背诵模式 -->
    <div v-if="reviewing" class="card review-card">
      <div class="review-toolbar">
        <span class="review-progress">{{ reviewIdx + 1 }} / {{ queue.length }}</span>
        <button class="ghost-btn" @click="endReview">结束背诵</button>
      </div>

      <div class="flashcard" :class="{ revealed }" @click="revealed = !revealed">
        <div class="flashcard-label">{{ revealed ? '背面 · 答案' : '正面 · 点卡片显示答案' }}</div>
        <div class="flashcard-cat">{{ queue[reviewIdx]?.category }}</div>
        <div class="flashcard-front">{{ queue[reviewIdx]?.front }}</div>
        <template v-if="revealed">
          <div class="flashcard-divider"></div>
          <div class="flashcard-back">{{ queue[reviewIdx]?.back }}</div>
          <div v-if="queue[reviewIdx]?.note" class="flashcard-note">{{ queue[reviewIdx].note }}</div>
        </template>
      </div>

      <div class="review-actions">
        <template v-if="!revealed">
          <button class="primary-btn" @click="revealed = true">显示答案</button>
        </template>
        <template v-else>
          <button class="unknown-btn" :disabled="grading" @click="grade(false)">
            😵 不认识
          </button>
          <button class="known-btn" :disabled="grading" @click="grade(true)">
            😄 认识
          </button>
        </template>
      </div>
      <p class="review-hint">认识 → 间隔拉长（明天 → 2天 → 4天 → 7天 → 15天 → 30天）；不认识 → 明天再见</p>
    </div>

    <template v-else>
      <!-- 工具栏 -->
      <div class="card toolbar-card">
        <h2>📖 词汇记忆</h2>
        <div class="toolbar-actions">
          <input v-model="keyword" class="search-input" placeholder="搜索卡片…" />
          <button class="review-btn" @click="startDue" :disabled="!dueCards.length">
            复习到期（{{ dueCards.length }}）
          </button>
          <button class="ghost-btn" @click="startAll" :disabled="!cards.length">背全部</button>
        </div>
      </div>

      <!-- 新增卡片 -->
      <div class="card">
        <h2>新增卡片</h2>
        <form @submit.prevent="onAdd">
          <div class="form-row">
            <div class="form-field">
              <label>分类</label>
              <select v-model="newCategory" :disabled="adding">
                <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
            <div class="form-field"></div>
          </div>
          <div class="form-row">
            <div class="form-field">
              <label>正面（要记的内容）</label>
              <textarea
                v-model="newFront"
                rows="2"
                :placeholder="frontPlaceholder"
                :disabled="adding"
              ></textarea>
            </div>
            <div class="form-field">
              <label>背面（答案 / 释义）</label>
              <textarea
                v-model="newBack"
                rows="2"
                placeholder="例如：v. 放弃；抛弃"
                :disabled="adding"
              ></textarea>
            </div>
          </div>
          <div class="form-field">
            <label>备注（可选，如音标 / 例句 / 记忆提示）</label>
            <input
              v-model="newNote"
              placeholder="/əˈbændən/ 例句…"
              :disabled="adding"
            />
          </div>
          <p v-if="formError" class="error">{{ formError }}</p>
          <button type="submit" class="primary-btn" :disabled="adding">
            {{ adding ? '保存中…' : '添加卡片' }}
          </button>
        </form>
      </div>

      <!-- 卡片列表 -->
      <div class="card">
        <h2>我的卡片（{{ filtered.length }}）</h2>
        <p v-if="listError" class="error">{{ listError }}</p>
        <p v-if="!filtered.length" class="empty">
          {{ keyword ? '没有匹配的卡片' : '还没有卡片，先在上面添加一张吧' }}
        </p>
        <div v-for="card in filtered" :key="card.id" class="vocab-item">
          <!-- 编辑态 -->
          <template v-if="editingId === card.id">
            <div class="edit-form">
              <div class="form-row">
                <div class="form-field">
                  <label>分类</label>
                  <select v-model="editForm.category">
                    <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
                  </select>
                </div>
                <div class="form-field"></div>
              </div>
              <div class="form-row">
                <div class="form-field">
                  <label>正面</label>
                  <textarea v-model="editForm.front" rows="2"></textarea>
                </div>
                <div class="form-field">
                  <label>背面</label>
                  <textarea v-model="editForm.back" rows="2"></textarea>
                </div>
              </div>
              <div class="form-field">
                <label>备注</label>
                <input v-model="editForm.note" />
              </div>
              <div class="item-actions">
                <button class="primary-btn small" @click="onSaveEdit" :disabled="saving">保存</button>
                <button class="ghost-btn small" @click="cancelEdit" :disabled="saving">取消</button>
              </div>
            </div>
          </template>

          <!-- 展示态 -->
          <template v-else>
            <div class="item-main">
              <div class="item-row">
                <div class="item-front">
                  <div class="item-label">正面</div>
                  <div class="item-text">{{ card.front }}</div>
                </div>
                <div class="item-back">
                  <div class="item-label">背面</div>
                  <div class="item-text">{{ card.back }}</div>
                </div>
              </div>
              <div v-if="card.note" class="item-note">{{ card.note }}</div>
              <div class="item-meta">
                <span class="cat-badge" :class="catClass(card.category)">{{ card.category }}</span>
                <span class="box-badge" :class="{ due: isDue(card) }">{{ boxLabel(card) }}</span>
                <span class="item-time">{{ formatDate(card.created_at) }}</span>
              </div>
            </div>
            <div class="item-actions">
              <button class="ghost-btn small" @click="startEdit(card)">编辑</button>
              <button class="danger-btn small" @click="onDelete(card)">删除</button>
            </div>
          </template>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { createVocab, deleteVocab, listVocab, reviewVocab, updateVocab } from '../api'

const CATEGORIES = ['单词', '短语', '句子', '其他']

const PLACEHOLDERS = {
  单词: '例如：abandon',
  短语: '例如：look forward to',
  句子: '例如：The early bird catches the worm.',
  其他: '例如：不规则动词表 / 语法规则…',
}

const cards = ref([])
const listError = ref('')
const keyword = ref('')

const newCategory = ref('单词')
const newFront = ref('')
const newBack = ref('')
const newNote = ref('')
const formError = ref('')
const adding = ref(false)

const editingId = ref(null)
const editForm = ref({ front: '', back: '', note: '', category: '单词' })
const saving = ref(false)

// 背诵模式状态
const reviewing = ref(false)
const queue = ref([])
const reviewIdx = ref(0)
const revealed = ref(false)
const grading = ref(false)

const frontPlaceholder = computed(() => PLACEHOLDERS[newCategory.value] || '要记的内容')

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return cards.value
  return cards.value.filter(
    (c) =>
      c.front.toLowerCase().includes(kw) ||
      c.back.toLowerCase().includes(kw) ||
      (c.note || '').toLowerCase().includes(kw) ||
      c.category.includes(kw)
  )
})

// 到期 = 新卡（从未复习）或 next_review_at <= 现在
const dueCards = computed(() => {
  const now = Date.now()
  return cards.value.filter(
    (c) => !c.next_review_at || new Date(c.next_review_at).getTime() <= now
  )
})

function isDue(card) {
  return !card.next_review_at || new Date(card.next_review_at).getTime() <= Date.now()
}

function boxLabel(card) {
  if (card.box_level === 0) return '新卡'
  if (!card.next_review_at) return `第 ${card.box_level} 盒`
  const d = new Date(card.next_review_at)
  const days = Math.ceil((d.getTime() - Date.now()) / 86400_000)
  if (days <= 0) return `第 ${card.box_level} 盒 · 今天复习`
  return `第 ${card.box_level} 盒 · ${days} 天后`
}

function catClass(cat) {
  return { 单词: 'cat-word', 短语: 'cat-phrase', 句子: 'cat-sentence', 其他: 'cat-other' }[cat] || 'cat-other'
}

async function load() {
  listError.value = ''
  try {
    cards.value = await listVocab()
  } catch (e) {
    listError.value = e?.response?.data?.detail || '加载失败'
  }
}

async function onAdd() {
  formError.value = ''
  if (!newFront.value.trim() || !newBack.value.trim()) {
    formError.value = '正面和背面内容都要填'
    return
  }
  adding.value = true
  try {
    await createVocab({
      front: newFront.value,
      back: newBack.value,
      note: newNote.value,
      category: newCategory.value,
    })
    newFront.value = ''
    newBack.value = ''
    newNote.value = ''
    await load()
  } catch (e) {
    formError.value = e?.response?.data?.detail || '添加失败'
  } finally {
    adding.value = false
  }
}

function startEdit(card) {
  editingId.value = card.id
  editForm.value = {
    front: card.front,
    back: card.back,
    note: card.note || '',
    category: card.category || '单词',
  }
}

function cancelEdit() {
  editingId.value = null
}

async function onSaveEdit() {
  saving.value = true
  try {
    await updateVocab(editingId.value, { ...editForm.value })
    editingId.value = null
    await load()
  } catch (e) {
    window.alert(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function onDelete(card) {
  if (!window.confirm(`确定删除卡片「${truncate(card.front, 20)}」吗？`)) return
  try {
    await deleteVocab(card.id)
    await load()
  } catch (e) {
    window.alert(e?.response?.data?.detail || '删除失败')
  }
}

// ==================== 背诵模式 ====================

function shuffle(list) {
  const arr = [...list]
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

function startReview(list) {
  if (!list.length) return
  queue.value = shuffle(list)
  reviewIdx.value = 0
  revealed.value = false
  reviewing.value = true
}

function startDue() {
  startReview(dueCards.value)
}

function startAll() {
  startReview(filtered.value)
}

function endReview() {
  reviewing.value = false
}

async function grade(known) {
  if (grading.value) return
  grading.value = true
  const card = queue.value[reviewIdx.value]
  try {
    await reviewVocab(card.id, known)
    if (reviewIdx.value < queue.value.length - 1) {
      reviewIdx.value++
      revealed.value = false
    } else {
      // 全部背完
      reviewing.value = false
      window.alert('这轮背完啦，明天继续 💪')
    }
    await load()
  } catch (e) {
    window.alert(e?.response?.data?.detail || '评分失败')
  } finally {
    grading.value = false
  }
}

function truncate(s, n) {
  return s.length > n ? s.slice(0, n) + '…' : s
}

function formatDate(s) {
  if (!s) return ''
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', { hour12: false })
}

onMounted(load)
</script>

<style scoped>
.vocab-view {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  position: relative;
}
.card h2 {
  font-size: 18px;
  color: #1f2937;
  margin-bottom: 16px;
}
.toolbar-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.toolbar-card h2 {
  margin-bottom: 0;
}
.toolbar-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}
.search-input {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 14px;
  outline: none;
  width: 200px;
}
.search-input:focus {
  border-color: #8b5cf6;
}
.review-btn {
  background: #8b5cf6;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  font-size: 14px;
  cursor: pointer;
}
.review-btn:hover {
  background: #7c3aed;
}
.review-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ghost-btn {
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
}
.ghost-btn:hover {
  background: #e5e7eb;
}
.ghost-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.form-row {
  display: flex;
  gap: 16px;
}
.form-field {
  flex: 1;
  margin-bottom: 14px;
}
.form-field label {
  display: block;
  font-size: 13px;
  color: #4b5563;
  margin-bottom: 6px;
}
.form-field input,
.form-field textarea,
.form-field select {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  outline: none;
  font-family: inherit;
  background: #fff;
  resize: vertical;
}
.form-field select {
  max-width: 200px;
  cursor: pointer;
}
.form-field input:focus,
.form-field textarea:focus,
.form-field select:focus {
  border-color: #8b5cf6;
}
.form-field input:disabled,
.form-field textarea:disabled,
.form-field select:disabled {
  background: #f9fafb;
  cursor: not-allowed;
}
.primary-btn {
  background: #8b5cf6;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
}
.primary-btn:hover {
  background: #7c3aed;
}
.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.danger-btn {
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
}
.small {
  padding: 6px 14px;
  font-size: 13px;
}
.error {
  color: #dc2626;
  font-size: 13px;
  margin-bottom: 8px;
}
.empty {
  color: #9ca3af;
  font-size: 14px;
  padding: 12px 0;
}
.vocab-item {
  border: 1px solid #f3f4f6;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.item-main {
  flex: 1;
  min-width: 0;
}
.edit-form {
  flex: 1;
}
.item-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  align-items: center;
}
.item-row {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}
.item-front,
.item-back {
  flex: 1;
  min-width: 200px;
}
.item-label {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 2px;
}
.item-text {
  font-size: 14px;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-word;
}
.item-front .item-text {
  font-weight: 600;
}
.item-note {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
  white-space: pre-wrap;
  word-break: break-word;
}
.item-meta {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.cat-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.cat-word {
  background: #ede9fe;
  color: #6d28d9;
}
.cat-phrase {
  background: #dbeafe;
  color: #1d4ed8;
}
.cat-sentence {
  background: #dcfce7;
  color: #15803d;
}
.cat-other {
  background: #f3f4f6;
  color: #4b5563;
}
.box-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 12px;
  background: #fff7ed;
  color: #c2410c;
}
.box-badge.due {
  background: #fee2e2;
  color: #991b1b;
}
.item-time {
  font-size: 12px;
  color: #c0c4cc;
}
/* ==================== 背诵模式 ==================== */
.review-card {
  min-height: 440px;
  display: flex;
  flex-direction: column;
}
.review-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.review-progress {
  font-size: 14px;
  color: #6b7280;
}
.flashcard {
  flex: 1;
  background: #f8f7ff;
  border: 2px solid #ddd6fe;
  border-radius: 16px;
  padding: 32px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  cursor: pointer;
  min-height: 240px;
  gap: 12px;
}
.flashcard:hover {
  border-color: #a78bfa;
}
.flashcard-label {
  font-size: 12px;
  color: #a78bfa;
  letter-spacing: 1px;
}
.flashcard-cat {
  font-size: 12px;
  color: #7c3aed;
  background: #ede9fe;
  padding: 1px 10px;
  border-radius: 10px;
}
.flashcard-front {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-word;
}
.flashcard-divider {
  width: 48px;
  height: 2px;
  background: #ddd6fe;
  border-radius: 1px;
}
.flashcard-back {
  font-size: 20px;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
}
.flashcard-note {
  font-size: 14px;
  color: #8b5cf6;
  white-space: pre-wrap;
  word-break: break-word;
}
.review-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}
.known-btn {
  background: #10b981;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 28px;
  font-size: 15px;
  cursor: pointer;
}
.known-btn:hover {
  background: #059669;
}
.known-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.unknown-btn {
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 28px;
  font-size: 15px;
  cursor: pointer;
}
.unknown-btn:hover {
  background: #dc2626;
}
.unknown-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.review-hint {
  margin-top: 12px;
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
}
</style>
