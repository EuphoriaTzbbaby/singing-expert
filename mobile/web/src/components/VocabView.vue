<template>
  <section class="vocab-view">
    <!-- ========== 背诵模式 ========== -->
    <div v-if="reviewing" class="card review-card">
      <div class="review-toolbar">
        <div class="progress-wrap">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: ((reviewIdx + (reviewDoneCurrent ? 1 : 0)) / Math.max(queue.length, 1)) * 100 + '%' }"></div>
          </div>
          <span class="review-progress">{{ reviewIdx + (reviewDoneCurrent ? 1 : 0) }} / {{ queue.length }}
            · 正确 {{ sessionCorrect }}（{{ totalSession > 0 ? Math.round(sessionCorrect / totalSession * 100) : 0 }}%）
          </span>
        </div>
        <div class="review-actions">
          <div class="mode-switch" v-if="queue[reviewIdx]?.category === '单词'">
            <label><input type="radio" v-model="sessionMode" value="type"> 拼写</label>
            <label><input type="radio" v-model="sessionMode" value="dictation"> 听写</label>
            <label><input type="radio" v-model="sessionMode" value="flash"> 翻卡</label>
          </div>
          <button class="ghost-btn" @click="endReview">结束背诵</button>
        </div>
      </div>

      <!-- 激励提醒 -->
      <div v-if="showCheer" class="cheer-toast">{{ cheerMsg }}</div>

      <!-- 单词类的 3 种模式 -->
      <template v-if="isWordCard(queue[reviewIdx]) && sessionMode === 'type'">
        <div class="flashcard word-mode">
          <div class="flashcard-label">请根据释义写出单词</div>
          <div class="flashcard-cat">{{ queue[reviewIdx]?.category }} · 拼写模式</div>
          <div class="flashcard-back big">{{ queue[reviewIdx]?.back }}</div>
          <div v-if="queue[reviewIdx]?.note" class="flashcard-note">{{ queue[reviewIdx].note }}</div>
          <div class="input-wrap">
            <button class="speak-btn" type="button" :class="{ error: inputError }" @click="speak(correctAnswer)" title="听发音">🔊</button>
            <input v-model="typeInput" :class="{ wrong: inputError === 'wrong', right: inputError === 'right' }"
              placeholder="输入单词，回车提交" :disabled="grading" @keydown.enter="submitTypeAnswer" autofocus />
            <button class="primary-btn" :disabled="grading" @click="submitTypeAnswer">{{ grading ? '判断中…' : '提交' }}</button>
            <button class="ghost-btn small" :disabled="grading" @click="showHint">提示 {{ hintStep > 0 ? `(${hintStep})` : '' }}</button>
            <button class="ghost-btn small" :disabled="grading" @click="revealWord">不会 / 看答案</button>
          </div>
          <div v-if="hintShown" class="hint-line">提示：<span class="hint-text">{{ hintShown }}</span></div>

          <button class="ghost-btn small ai-btn" :disabled="aiLoading" @click="genAiCurrent">
            {{ aiLoading ? '生成中…' : '🤖 AI 助记（词根+小故事）' }}
          </button>
          <div v-if="queue[reviewIdx]?.ai_mnemonic && !aiLoading" class="ai-mnemonic" v-html="md(queue[reviewIdx].ai_mnemonic)"></div>
        </div>
      </template>

      <template v-else-if="isWordCard(queue[reviewIdx]) && sessionMode === 'dictation'">
        <div class="flashcard word-mode dictation-mode">
          <div class="flashcard-label">🎧 听发音，把单词写下来</div>
          <div class="flashcard-cat">{{ queue[reviewIdx]?.category }} · 听写模式</div>
          <div class="dict-speak">
            <button class="speak-btn big-speak" @click="speak(correctAnswer); revealHintAfterSpeak = false" title="再听一次">🔊 再听一次</button>
          </div>
          <div v-if="!dictationRevealed" class="dict-hide-text">（听到后自己先在纸上/脑海里拼写出来，感觉没问题再看答案）</div>
          <div v-else>
            <div class="dict-reveal-ans">
              <span class="ans-word">{{ correctAnswer }}</span>
              <span class="ans-back">：{{ queue[reviewIdx].back }}</span>
            </div>
            <div v-if="queue[reviewIdx]?.note" class="flashcard-note">{{ queue[reviewIdx].note }}</div>
          </div>
          <div class="row-buttons" v-if="dictationRevealed || grading !== false">
            <button class="success-btn" :disabled="grading" @click="gradeDictation(true)">✓ 我写对了（认识）</button>
            <button class="danger-btn" :disabled="grading" @click="gradeDictation(false)">✗ 没记住（不认识）</button>
          </div>
          <div class="row-buttons" v-else>
            <button class="primary-btn" @click="dictationRevealed = true">看答案</button>
            <button class="ghost-btn small" :disabled="grading" @click="showHint">提示首字母</button>
          </div>
          <div v-if="hintShown && !dictationRevealed" class="hint-line">提示：<span class="hint-text">{{ hintShown }}</span></div>

          <button class="ghost-btn small ai-btn" :disabled="aiLoading" @click="genAiCurrent">
            {{ aiLoading ? '生成中…' : '🤖 AI 助记' }}
          </button>
          <div v-if="queue[reviewIdx]?.ai_mnemonic && !aiLoading" class="ai-mnemonic" v-html="md(queue[reviewIdx].ai_mnemonic)"></div>
        </div>
      </template>

      <!-- 翻卡模式（短语 / 句子 / 其他 + 单词选翻卡） -->
      <template v-else>
        <div class="flashcard flash-mode" @click="!flipped && queue.length && (flipped = true)">
          <div :class="['flashcard-inner', { flipped }]">
            <div class="flashcard-face front">
              <div class="flashcard-label">正面（点击翻面 / 空格键）</div>
              <div class="flashcard-cat">{{ queue[reviewIdx]?.category }}</div>
              <div class="flashcard-front big">
                {{ queue[reviewIdx]?.front }}
                <button class="speak-btn inline" type="button" @click.stop="speak(queue[reviewIdx].front)" title="发音">🔊</button>
              </div>
              <div v-if="queue[reviewIdx]?.note" class="flashcard-note">{{ queue[reviewIdx].note }}</div>
            </div>
            <div class="flashcard-face back">
              <div class="flashcard-label">背面</div>
              <div class="flashcard-back big">{{ queue[reviewIdx]?.back }}</div>
              <button class="ghost-btn small ai-btn" :disabled="aiLoading" @click.stop="genAiCurrent">
                {{ aiLoading ? '生成中…' : '🤖 AI 助记' }}
              </button>
              <div v-if="queue[reviewIdx]?.ai_mnemonic && !aiLoading" class="ai-mnemonic" v-html="md(queue[reviewIdx].ai_mnemonic)"></div>
            </div>
          </div>
        </div>
        <div class="row-buttons">
          <button class="ghost-btn small" :disabled="!flipped" @click="prevCard">← 上一张</button>
          <button class="success-btn" :disabled="!flipped || grading" @click="gradeFlash(true)">😄 认识</button>
          <button class="danger-btn" :disabled="!flipped || grading" @click="gradeFlash(false)">😵 不认识</button>
          <button class="ghost-btn small" :disabled="!flipped" @click="nextCard(false, false)">下一张（不评分）→</button>
        </div>
      </template>
    </div>

    <!-- ========== 列表模式（非背诵）：单栏卡片列表 ========== -->
    <template v-else>
      <div class="vocab-list-page">
      <!-- 工具条 -->
      <div class="card toolbar">
        <div class="toolbar-search">
          <input v-model="keyword" placeholder="搜索正面 / 背面 / 备注…" @keydown.enter="page = 1; loadList()" />
          <select v-model="categoryFilter" @change="page = 1; loadList()">
            <option value="">全部分类</option>
            <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
          </select>
          <button class="primary-btn search-btn" @click="loadList">搜索</button>
        </div>
        <div class="toolbar-actions">
          <span class="total-count">共 {{ total }} 张</span>
          <div class="toolbar-btns">
            <button class="warn-btn" @click="startReview(false)">📖 复习到期（{{ dueCount }}）</button>
            <button class="primary-btn" @click="startReview(true)">🎯 背全部</button>
            <button class="primary-btn" @click="openAdd()">＋ 新增卡片</button>
          </div>
        </div>
      </div>

      <!-- 新增卡片 -->
      <div class="card add-form" v-if="showAdd">
        <h3>{{ editId ? '编辑卡片' : '新增卡片' }}</h3>
        <div class="form-row">
          <label>分类</label>
          <select v-model="form.category">
            <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div class="form-row">
          <label>正面（要记的内容）</label>
          <div class="area-wrap">
            <textarea v-model="form.front" rows="2" :placeholder="placeholderForFront" @focus="autosize" @input="autosize"></textarea>
            <button class="speak-btn tiny" type="button" @click="speak(form.front)" title="试听发音">🔊</button>
          </div>
        </div>
        <div class="form-row">
          <label>背面（答案/释义）</label>
          <textarea v-model="form.back" rows="2" placeholder="例如：adj. 放弃的；vt. 抛弃"></textarea>
        </div>
        <div class="form-row">
          <label>备注（可选）</label>
          <textarea v-model="form.note" rows="2" placeholder="音标、例句、同义词…"></textarea>
        </div>

        <!-- 查重确认弹层 -->
        <div v-if="dupDialog.show" class="dup-dialog">
          <div class="dup-title">⚠️ 正面内容已存在相同卡片</div>
          <div class="dup-preview">
            <div><b>已有正面：</b>{{ dupDialog.existing?.front }}</div>
            <div><b>已有背面：</b>{{ dupDialog.existing?.back }}</div>
            <div><b>分类：</b>{{ dupDialog.existing?.category }} · 盒级 {{ dupDialog.existing?.box_level }}</div>
            <div v-if="dupDialog.existing?.note"><b>备注：</b>{{ dupDialog.existing.note }}</div>
          </div>
          <div class="dup-actions">
            <button class="primary-btn" @click="doUpdateExisting">更新已有卡片内容</button>
            <button class="warn-btn" @click="doForceCreate">仍然再建一张</button>
            <button class="ghost-btn" @click="dupDialog.show = false">取消</button>
          </div>
        </div>

        <div class="form-actions">
          <button class="primary-btn" :disabled="saving" @click="submitForm">
            {{ saving ? '保存中…' : (editId ? '保存修改' : '新增') }}
          </button>
          <button class="ghost-btn" @click="closeAdd">取消</button>
        </div>
      </div>

      <!-- 卡片列表 -->
      <div class="card list">
        <div v-if="loading" class="empty">加载中…</div>
        <div v-else-if="!items.length" class="empty">还没有卡片，先点右上角「新增卡片」吧 🎉</div>
        <div v-else class="card-grid">
          <div v-for="c in items" :key="c.id" class="mini-card" :class="'accent-' + c.category">
            <div class="mini-top">
              <span :class="['cat-tag', 'cat-' + c.category]">{{ c.category }}</span>
              <span class="box-tag" :class="{ due: isDue(c) }">{{ boxLabel(c) }}</span>
            </div>
            <div class="mini-front">
              <span class="mini-front-text">{{ c.front }}</span>
              <button class="speak-btn card-speak" type="button" @click="speak(c.front)" title="点击发音">🔊</button>
            </div>
            <div class="mini-back">{{ c.back }}</div>
            <div v-if="c.note" class="mini-note">{{ c.note }}</div>
            <div class="mini-actions">
              <button class="ghost-btn tiny" @click="openEdit(c)">✎ 编辑</button>
              <button class="danger-btn tiny" @click="remove(c)">✕ 删除</button>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="total > 0" class="pager">
          <button class="ghost-btn tiny" :disabled="page <= 1" @click="page = 1; loadList()">首页</button>
          <button class="ghost-btn tiny" :disabled="page <= 1" @click="page--; loadList()">← 上一页</button>
          <span class="pager-info">第 {{ page }} / {{ totalPages }} 页</span>
          <button class="ghost-btn tiny" :disabled="page >= totalPages" @click="page++; loadList()">下一页 →</button>
          <button class="ghost-btn tiny" :disabled="page >= totalPages" @click="page = totalPages; loadList()">末页</button>
        </div>
      </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch, nextTick } from 'vue'
import {
  createVocab,
  deleteVocab,
  generateAiMnemonic,
  listVocab,
  listVocabDue,
  reviewVocab,
  updateVocab,
} from '../api.js'

const CATEGORIES = ['单词', '短语', '句子', '其他']

// ==================== 状态：列表 / 仪表盘 ====================
const loading = ref(false)
const keyword = ref('')
const categoryFilter = ref('')
const page = ref(1)
const pageSize = 10
const items = ref([])
const total = ref(0)
const dueCount = ref(0)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

async function loadList() {
  loading.value = true
  try {
    const r = await listVocab({
      page: page.value,
      pageSize,
      keyword: keyword.value.trim(),
      category: categoryFilter.value,
    })
    items.value = r.items
    total.value = r.total
  } finally {
    loading.value = false
  }
}

async function loadDueCount() {
  try {
    const all = await listVocabDue()
    dueCount.value = all.length
  } catch (e) {
    // 忽略
  }
}

const placeholderForFront = computed(() => {
  switch ((form.value && form.value.category) || '单词') {
    case '单词':
      return '例如：abandon'
    case '短语':
      return '例如：give up'
    case '句子':
      return '例如：I will never give up.'
    default:
      return '正面（要记忆的内容）'
  }
})

// ==================== 新增 / 编辑 ====================
const showAdd = ref(false)
const editId = ref(null)
const saving = ref(false)
const form = ref({ front: '', back: '', note: '', category: '单词' })
const dupDialog = ref({ show: false, existing: null, submitCopy: null })

function openAdd() {
  editId.value = null
  form.value = { front: '', back: '', note: '', category: '单词' }
  dupDialog.value = { show: false, existing: null, submitCopy: null }
  showAdd.value = true
}
function openEdit(c) {
  editId.value = c.id
  form.value = {
    front: c.front,
    back: c.back,
    note: c.note || '',
    category: c.category,
  }
  showAdd.value = true
  nextTick(() => autosize())
}
function closeAdd() {
  showAdd.value = false
  editId.value = null
  dupDialog.value = { show: false, existing: null, submitCopy: null }
}
function autosize(e) {
  const el = e && e.target ? e.target : null
  if (!el) return
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

async function submitForm() {
  if (!form.value.front.trim() || !form.value.back.trim()) {
    alert('正面和背面都不能为空')
    return
  }
  saving.value = true
  try {
    if (editId.value) {
      await updateVocab(editId.value, form.value)
    } else {
      try {
        await createVocab({ ...form.value, forceCreate: false })
      } catch (e) {
        const status = e?.response?.status
        const data = e?.response?.data
        if (status === 409 && data?.detail?.existing) {
          dupDialog.value = {
            show: true,
            existing: data.detail.existing,
            submitCopy: { ...form.value },
          }
          return
        }
        throw e
      }
    }
    closeAdd()
    page.value = 1
    await Promise.all([loadList(), loadDueCount()])
  } finally {
    saving.value = false
  }
}

async function doForceCreate() {
  saving.value = true
  try {
    const copy = dupDialog.value.submitCopy
    await createVocab({ ...copy, forceCreate: true })
    closeAdd()
    page.value = 1
    await Promise.all([loadList(), loadDueCount()])
  } finally {
    saving.value = false
  }
}

async function doUpdateExisting() {
  saving.value = true
  try {
    const copy = dupDialog.value.submitCopy
    const exId = dupDialog.value.existing.id
    await updateVocab(exId, copy)
    closeAdd()
    page.value = 1
    await Promise.all([loadList(), loadDueCount()])
  } finally {
    saving.value = false
  }
}

async function remove(c) {
  if (!confirm(`确定删除「${c.front}」吗？`)) return
  await deleteVocab(c.id)
  if (items.value.length === 1 && page.value > 1) page.value -= 1
  await Promise.all([loadList(), loadDueCount()])
}

// ==================== 复习模式 ====================
const reviewing = ref(false)
const queue = ref([])
const reviewIdx = ref(0)
const sessionMode = ref('type') // 'type' | 'dictation' | 'flash'
const sessionCorrect = ref(0)
const totalSession = ref(0)
const reviewDoneCurrent = ref(false)
// 单词输入模式
const typeInput = ref('')
const inputError = ref(false) // false | 'wrong' | 'right'
const grading = ref(false)
const hintStep = ref(0)
const hintShown = ref('')
// 翻卡
const flipped = ref(false)
// 听写
const dictationRevealed = ref(false)
// 激励
const showCheer = ref(false)
const cheerMsg = ref('')

// AI 助记
const aiLoading = ref(false)

const correctAnswer = computed(() => (queue.value[reviewIdx.value]?.front || '').trim())

function isWordCard(c) {
  return c && c.category === '单词'
}

// 盒子显示
const BOX_LABELS = ['新卡', '明天复习', '2 天后', '4 天后', '7 天后', '15 天后', '30 天后']
function boxLabel(c) {
  if (isDue(c) && c.box_level > 0) return `第 ${c.box_level} 盒 · 到期`
  if (c.box_level === 0) return '新卡'
  return `第 ${c.box_level} 盒 · ${BOX_LABELS[c.box_level]}`
}
function isDue(c) {
  if (!c.next_review_at) return true
  const due = new Date(c.next_review_at).getTime()
  return Date.now() >= due
}

async function startReview(all) {
  let cards
  if (all) {
    const r = await listVocab({ page: 1, pageSize: 10000 })
    cards = r.items.slice()
  } else {
    cards = await listVocabDue()
  }
  if (!cards.length) {
    alert(all ? '还没有卡片，先添加吧～' : '没有到期的卡片，太棒了！')
    return
  }
  // Fisher-Yates 洗牌
  for (let i = cards.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[cards[i], cards[j]] = [cards[j], cards[i]]
  }
  queue.value = cards
  reviewIdx.value = 0
  sessionCorrect.value = 0
  totalSession.value = 0
  reviewDoneCurrent.value = false
  resetCardUI()
  reviewing.value = true
}

function endReview() {
  reviewing.value = false
  queue.value = []
  document.removeEventListener('keydown', onKey)
  Promise.all([loadList(), loadDueCount()])
}

function resetCardUI() {
  typeInput.value = ''
  inputError.value = false
  grading.value = false
  hintStep.value = 0
  hintShown.value = ''
  flipped.value = false
  dictationRevealed.value = false
  // 默认模式：单词=type，非单词=flash
  if (queue.value[reviewIdx.value]?.category === '单词') {
    // 保持用户选择，否则默认 type
    if (!['type', 'dictation', 'flash'].includes(sessionMode.value)) sessionMode.value = 'type'
  } else {
    sessionMode.value = 'flash'
  }
  nextTick(() => {
    // 自动聚焦
    const el = document.querySelector('.review-card input:not([disabled])')
    if (el) el.focus()
  })
  document.addEventListener('keydown', onKey)
}

onBeforeUnmount(() => document.removeEventListener('keydown', onKey))

function onKey(e) {
  if (!reviewing.value) return
  if (e.target && ['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return
  if (e.code === 'Space') {
    e.preventDefault()
    if (sessionMode.value === 'flash') flipped.value = !flipped.value
    else if (sessionMode.value === 'type') submitTypeAnswer()
    else if (sessionMode.value === 'dictation') dictationRevealed.value = true
  } else if (e.code === 'ArrowRight') {
    if (reviewDoneCurrent.value) nextCard()
  } else if (e.code === 'ArrowLeft') {
    prevCard()
  }
}

// --- 拼写模式 ---
function submitTypeAnswer() {
  if (grading.value) return
  const ans = (typeInput.value || '').trim().toLowerCase()
  const correct = correctAnswer.value.toLowerCase()
  if (!ans) return
  if (ans === correct) {
    inputError.value = 'right'
    grading.value = true
    speak(correctAnswer.value)
    gradeType(true)
  } else {
    inputError.value = 'wrong'
    setTimeout(() => {
      inputError.value = false
      typeInput.value = ''
    }, 1200)
  }
}

function revealWord() {
  if (grading.value) return
  inputError.value = 'right'
  typeInput.value = correctAnswer.value
  speak(correctAnswer.value)
  grading.value = true
  setTimeout(() => gradeType(false), 1200)
}

// --- 音节级提示 ---
// 简化实现：把单词按元音/辅音簇做切分（aeiou+连续辅音为一段），提示按段展开 + 首尾字母保底
function splitIntoSyllables(w) {
  if (!w) return []
  const vowels = new Set(['a', 'e', 'i', 'o', 'u'])
  const pieces = []
  let buf = ''
  for (let i = 0; i < w.length; i++) {
    const ch = w[i]
    const isVow = vowels.has(ch.toLowerCase()) || (ch.toLowerCase() === 'y' && i > 0)
    if (buf.length === 0) {
      buf += ch
    } else {
      const lastVow = vowels.has(buf[buf.length - 1].toLowerCase())
      if (isVow === lastVow) {
        buf += ch
      } else {
        pieces.push(buf)
        buf = ch
      }
    }
  }
  if (buf) pieces.push(buf)
  // 太少分段，退回逐字符
  if (pieces.length <= 1) return w.split('')
  return pieces
}

function showHint() {
  const answer = correctAnswer.value
  if (!answer) return
  hintStep.value += 1
  const sylls = splitIntoSyllables(answer)
  const maxStep = sylls.length + 2 // +2 给首尾字符兜底
  const showN = Math.min(hintStep.value, sylls.length)
  // 按段显示前 N 段，其余用 '_' + 空格分隔
  let masked = ''
  for (let i = 0; i < sylls.length; i++) {
    if (i < showN) masked += sylls[i]
    else masked += '_'.repeat(sylls[i].length)
  }
  // 如果 step 超了 sylls 但还没到 max，强制逐字符补充
  if (showN === sylls.length && hintStep.value > sylls.length) {
    // 已经全显示了
    masked = answer
  }
  // 至少首字、末字的兜底（第一步就保证）
  if (hintStep.value <= 1 && answer.length > 2) {
    const arr = masked.split('')
    arr[0] = answer[0]
    arr[arr.length - 1] = answer[answer.length - 1]
    masked = arr.join('')
  }
  // 加空格显示，更易读
  hintShown.value = masked.split('').map((c) => (c === '_' ? '_' : c)).join(' ') + `  (${answer.length} 字母)`
}

// --- 听写模式 ---
async function gradeDictation(known) {
  if (grading.value) return
  grading.value = true
  await sendGrade(known, 'dictation')
}

// --- 翻卡模式 ---
async function gradeFlash(known) {
  if (grading.value) return
  grading.value = true
  await sendGrade(known, 'flash')
}

// --- 拼写模式评分 ---
async function gradeType(known) {
  await sendGrade(known, 'type')
}

// --- 通用评分 ---
async function sendGrade(known, mode) {
  try {
    const c = queue.value[reviewIdx.value]
    const updated = await reviewVocab(c.id, known, mode)
    // 写回队列
    queue.value[reviewIdx.value] = updated
    sessionCorrect.value += known ? 1 : 0
    totalSession.value += 1
    reviewDoneCurrent.value = true
    maybeCheer()
    // 延迟自动下一张
    setTimeout(() => {
      nextCard()
    }, known ? 700 : 1400)
  } finally {
    grading.value = false
  }
}

function maybeCheer() {
  const done = totalSession.value
  if (done > 0 && done % 5 === 0) {
    const msgs = [
      `🎉 已完成 ${done} 张，继续加油！`,
      `💪 ${done} 张了，正确率 ${Math.round(sessionCorrect.value / done * 100)}%，很稳！`,
      `🌟 坚持的样子超帅！又完成了 5 张～`,
      `🔥 ${done} 张打卡！今天的连续打卡日数要 +1 啦～`,
    ]
    cheerMsg.value = msgs[Math.floor(Math.random() * msgs.length)]
    showCheer.value = true
    setTimeout(() => (showCheer.value = false), 1800)
  }
}

function prevCard() {
  if (reviewIdx.value > 0) {
    reviewIdx.value -= 1
    reviewDoneCurrent.value = false
    resetCardUI()
  }
}
function nextCard() {
  if (reviewIdx.value + 1 >= queue.value.length) {
    // 结束
    setTimeout(() => {
      alert(
        `本轮完成 ${totalSession.value} 张，正确 ${sessionCorrect.value} 张，` +
          `正确率 ${totalSession.value ? Math.round(sessionCorrect.value / totalSession.value * 100) : 0}%。`
      )
      endReview()
    }, 300)
    return
  }
  reviewIdx.value += 1
  reviewDoneCurrent.value = false
  resetCardUI()
}

// ==================== AI 助记 ====================
async function genAiCurrent() {
  const c = queue.value[reviewIdx.value]
  if (!c) return
  aiLoading.value = true
  try {
    const updated = await generateAiMnemonic(c.id)
    queue.value[reviewIdx.value] = updated
    // 写 items（如果列表页有同一个）
    const idx = items.value.findIndex((x) => x.id === c.id)
    if (idx >= 0) items.value[idx] = updated
  } catch (e) {
    const errMsg = e?.response?.data?.detail || e?.message || 'AI 生成失败'
    alert(errMsg)
  } finally {
    aiLoading.value = false
  }
}

// ==================== 发音（Web Speech API） ====================
let cachedVoice = null
function pickVoice() {
  if (cachedVoice) return cachedVoice
  const vs = window.speechSynthesis ? window.speechSynthesis.getVoices() : []
  // 优先英语，挑一个比较自然的
  const en = vs.filter((v) => /^en(-|_)?/i.test(v.lang))
  const priority = ['Samantha', 'Daniel', 'Google US English', 'Google UK English Male', 'Google UK English Female', 'Alex', 'Karen']
  for (const name of priority) {
    const v = en.find((x) => x.name.includes(name))
    if (v) {
      cachedVoice = v
      return v
    }
  }
  if (en.length) {
    cachedVoice = en[0]
    return cachedVoice
  }
  cachedVoice = vs[0] || null
  return cachedVoice
}
// 首次 voices 可能为空，加载后刷新
if (typeof window !== 'undefined' && window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => {
    cachedVoice = null
    pickVoice()
  }
}

function hasEnglish(text) {
  return /[a-zA-Z]/.test(text)
}
function hasChinese(text) {
  return /[\u4e00-\u9fa5]/.test(text)
}

function speak(text) {
  if (!text) return
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    alert('当前浏览器不支持发音功能')
    return
  }
  try {
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    if (hasEnglish(text)) {
      u.lang = 'en-US'
      const v = pickVoice()
      if (v) u.voice = v
    } else if (hasChinese(text)) {
      u.lang = 'zh-CN'
    } else {
      u.lang = 'en-US'
    }
    u.rate = 0.95
    u.pitch = 1
    window.speechSynthesis.speak(u)
  } catch (e) {
    // ignore
  }
}

// ==================== Markdown 极简渲染（只处理标题、加粗、列表、换行、序号段） ====================
function md(s) {
  if (!s) return ''
  const escape = (t) =>
    t
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
  let out = escape(s)
  // 粗体 **x**
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  // 标题
  out = out.replace(/^#\s+(.+)$/gm, '<h5>$1</h5>')
  out = out.replace(/^##\s+(.+)$/gm, '<h5>$1</h5>')
  // 无序列表
  out = out.replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>')
  // 有序列表
  out = out.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
  // 换行 -> <br>
  out = out.replace(/\n/g, '<br>')
  return out
}

// ==================== 初始化 ====================
onMounted(async () => {
  pickVoice()
  await Promise.all([loadList(), loadDueCount()])
})

// 分类变化时，重建列表数据（列表搜索的分类筛选已在工具条上，不需要额外监听）
watch(reviewing, (v) => {
  if (!v) {
    // 刚退出复习，刷新统计/列表
    Promise.all([loadList(), loadDueCount()])
  }
})
</script>

<style scoped>
.vocab-view {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 10px 0 30px 0;
}
.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}

/* ====== 单栏列表布局 ====== */
.vocab-list-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
h3 {
  margin: 0 0 12px 0;
  font-size: 18px;
}

/* ====== 工具条 ====== */
.toolbar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px;
}
.toolbar-search {
  display: flex;
  gap: 8px;
}
.toolbar-search input {
  flex: 1;
  min-width: 0;
  padding: 9px 12px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  outline: none;
  font-size: 14px;
  font-family: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.toolbar-search input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12);
}
.toolbar-search select {
  padding: 9px 10px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  font-size: 14px;
  font-family: inherit;
  background: #fff;
  outline: none;
  cursor: pointer;
}
.toolbar-search .search-btn { flex-shrink: 0; }
.toolbar-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.toolbar-btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.total-count { color: #6b7280; font-size: 13px; }

/* ====== 按钮 ====== */
button {
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 14px;
  transition: all 0.15s;
}
button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.primary-btn {
  background: #4f46e5;
  color: #fff;
}
.primary-btn:hover:not(:disabled) { background: #4338ca; }
.success-btn { background: #10b981; color: #fff; }
.success-btn:hover:not(:disabled) { background: #059669; }
.danger-btn { background: #ef4444; color: #fff; }
.danger-btn:hover:not(:disabled) { background: #dc2626; }
.warn-btn { background: #f59e0b; color: #fff; }
.warn-btn:hover:not(:disabled) { background: #d97706; }
.ghost-btn {
  background: #fff;
  color: #374151;
  border: 1px solid #d1d5db;
}
.ghost-btn:hover:not(:disabled) { background: #f3f4f6; }
.ghost-btn.tiny { padding: 4px 10px; font-size: 12px; }
.ghost-btn.small { padding: 6px 12px; font-size: 13px; }

/* ====== 新增/编辑表单 ====== */
.form-row { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.form-row label { font-size: 13px; color: #374151; font-weight: 500; }
.form-row select,
.form-row textarea {
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  font-family: inherit;
  resize: vertical;
}
.form-row textarea:focus, .form-row select:focus { border-color: #4f46e5; }
.area-wrap { position: relative; }
.area-wrap textarea { width: calc(100% - 4px); padding-right: 40px; box-sizing: border-box; }
.speak-btn {
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  color: #4338ca;
  border-radius: 8px;
  cursor: pointer;
}
.speak-btn.tiny { padding: 4px 8px; font-size: 12px; position: absolute; right: 6px; top: 6px; }
.speak-btn.inline { padding: 2px 8px; margin-left: 8px; font-size: 14px; }
.speak-btn.big-speak {
  font-size: 18px;
  padding: 12px 22px;
  background: linear-gradient(180deg, #6366f1, #4f46e5);
  border: 1px solid #4338ca;
  color: #fff;
  margin: 8px 0 14px;
}
.speak-btn.error { background: #fee2e2; border-color: #fca5a5; color: #b91c1c; }

.form-actions { display: flex; gap: 10px; justify-content: flex-end; }

/* 查重弹窗 */
.dup-dialog {
  margin: 12px 0;
  padding: 14px;
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 10px;
}
.dup-title { font-weight: 600; color: #92400e; margin-bottom: 8px; }
.dup-preview { font-size: 13px; color: #78350f; line-height: 1.7; margin-bottom: 10px; }
.dup-actions { display: flex; gap: 10px; flex-wrap: wrap; }

/* ====== 列表 ====== */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}
.mini-card {
  position: relative;
  border: 1.5px solid var(--accent, #9ca3af);
  border-radius: 14px;
  padding: 16px 16px 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.mini-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
}
.accent-单词 { --accent: #3b82f6; }
.accent-短语 { --accent: #22c55e; }
.accent-句子 { --accent: #a855f7; }
.accent-其他 { --accent: #6b7280; }
.mini-top { display: flex; justify-content: space-between; align-items: center; }
.cat-tag {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}
.cat-单词 { background: #dbeafe; color: #1d4ed8; }
.cat-短语 { background: #dcfce7; color: #15803d; }
.cat-句子 { background: #fae8ff; color: #a21caf; }
.cat-其他 { background: #e5e7eb; color: #374151; }
.box-tag {
  padding: 3px 10px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #4b5563;
  font-size: 11px;
}
.box-tag.due { background: #fee2e2; color: #b91c1c; }
.mini-front {
  font-size: 19px;
  font-weight: 700;
  color: #111827;
  word-break: break-word;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 2px;
}
.mini-front-text { flex: 1; min-width: 0; }
.speak-btn.card-speak {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  border-radius: 50%;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  transition: background 0.15s, transform 0.1s;
}
.speak-btn.card-speak:hover { background: #e0e7ff; transform: scale(1.08); }
.mini-back {
  font-size: 14px;
  color: #374151;
  word-break: break-word;
}
.mini-note {
  font-size: 12px;
  color: #6b7280;
  word-break: break-word;
  background: #f9fafb;
  border-radius: 8px;
  padding: 6px 10px;
}
.mini-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid #f3f4f6;
}

.pager {
  margin-top: 14px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}
.pager-info { color: #6b7280; font-size: 13px; }
.empty {
  text-align: center;
  color: #9ca3af;
  padding: 40px 0;
}

/* ====== 复习 ====== */
.review-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}
.progress-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 200px;
}
.progress-bar {
  flex: 1;
  height: 10px;
  background: #eef2ff;
  border-radius: 999px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #4f46e5);
  transition: width 0.3s ease;
}
.review-progress { font-size: 13px; color: #374151; white-space: nowrap; }
.review-actions { display: flex; align-items: center; gap: 10px; }
.mode-switch {
  display: inline-flex;
  gap: 10px;
  padding: 4px 10px;
  background: #f3f4f6;
  border-radius: 999px;
  font-size: 13px;
}
.mode-switch label { display: inline-flex; align-items: center; gap: 4px; cursor: pointer; }

.cheer-toast {
  position: absolute;
  top: 10px;
  right: 16px;
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  color: #92400e;
  padding: 10px 16px;
  border-radius: 999px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
  animation: pop 0.35s ease;
}
@keyframes pop {
  0% { transform: translateY(-10px); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}

/* 翻卡 */
.flashcard {
  margin: 0 auto;
  max-width: 720px;
  padding: 20px;
  border-radius: 14px;
  background: linear-gradient(180deg, #fff, #f9fafb);
  border: 1px solid #e5e7eb;
  box-shadow: 0 6px 18px rgba(17, 24, 39, 0.04);
  position: relative;
  min-height: 280px;
}
.flashcard-label { font-size: 12px; color: #6b7280; margin-bottom: 6px; }
.flashcard-cat { font-size: 12px; color: #6b7280; margin-bottom: 14px; }
.flashcard-front, .flashcard-back {
  word-break: break-word;
  line-height: 1.6;
}
.flashcard-front.big { font-size: 32px; font-weight: 700; color: #111827; margin: 12px 0; }
.flashcard-back.big { font-size: 22px; font-weight: 600; color: #1f2937; margin: 12px 0; }
.flashcard-note {
  margin-top: 14px;
  padding: 8px 10px;
  background: #eef2ff;
  color: #3730a3;
  border-radius: 8px;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
}
.row-buttons {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.flashcard.flash-mode {
  cursor: pointer;
  perspective: 1600px;
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
}
.flashcard-inner {
  position: relative;
  width: 100%;
  min-height: 320px;
  transition: transform 0.6s;
  transform-style: preserve-3d;
}
.flashcard-inner.flipped { transform: rotateY(180deg); }
.flashcard-face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 24px;
  background: linear-gradient(180deg, #fff, #f9fafb);
  box-shadow: 0 6px 18px rgba(17, 24, 39, 0.04);
}
.flashcard-face.back { transform: rotateY(180deg); }

/* 拼写 */
.input-wrap {
  margin-top: 14px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: stretch;
}
.input-wrap input {
  flex: 1;
  min-width: 200px;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 18px;
  outline: none;
  letter-spacing: 2px;
  font-family: inherit;
}
.input-wrap input:focus { border-color: #4f46e5; }
.input-wrap input.wrong {
  border-color: #ef4444;
  background: #fef2f2;
  animation: shake 0.25s;
}
.input-wrap input.right {
  border-color: #10b981;
  background: #ecfdf5;
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-6px); }
  75% { transform: translateX(6px); }
}
.hint-line { margin-top: 10px; font-size: 14px; color: #6b7280; }
.hint-text { font-family: "SF Mono", Menlo, Consolas, monospace; letter-spacing: 4px; font-weight: 600; color: #4f46e5; }

/* 听写 */
.dictation-mode .dict-speak { text-align: center; }
.dict-hide-text { text-align: center; color: #6b7280; font-size: 14px; padding: 40px 0; }
.dict-reveal-ans { text-align: center; padding: 10px 0; }
.ans-word { font-size: 32px; font-weight: 700; color: #111827; letter-spacing: 2px; }
.ans-back { font-size: 18px; color: #374151; }

/* AI 助记 */
.ai-btn { margin-top: 12px; }
.ai-mnemonic {
  margin-top: 10px;
  padding: 12px 14px;
  background: #f5f3ff;
  border: 1px solid #ddd6fe;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.7;
  color: #4c1d95;
  word-break: break-word;
}
.ai-mnemonic :deep(strong) { color: #5b21b6; }
.ai-mnemonic :deep(li) { margin-left: 16px; }
.ai-mnemonic :deep(h5) { margin: 8px 0 4px; font-size: 14px; color: #4c1d95; }

@media (max-width: 768px) {
  .flashcard-front.big { font-size: 24px; }
  .flashcard-back.big { font-size: 18px; }
}
</style>
