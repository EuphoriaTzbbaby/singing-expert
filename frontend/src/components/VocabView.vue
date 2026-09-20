<template>
  <section class="vocab-view">
    <!-- ==================== 背诵模式 ==================== -->
    <div v-if="reviewing" class="card review-card">
      <div class="review-toolbar">
        <span class="review-progress">
          {{ reviewIdx + 1 }} / {{ queue.length }}
          <span class="mode-badge">{{ MODE_LABELS[reviewMode] }}</span>
        </span>
        <span v-if="roundKnown || roundWrong" class="round-score">
          😄 {{ roundKnown }} · 😵 {{ roundWrong }}
        </span>
        <button class="ghost-btn" @click="endReview">结束背诵</button>
      </div>

      <!-- 翻卡模式 -->
      <template v-if="reviewMode === 'flash'">
        <div class="flashcard" :class="{ revealed }" @click="revealed = !revealed">
          <div class="flashcard-label">{{ revealed ? '背面 · 答案' : '正面 · 点卡片显示答案' }}</div>
          <div class="flashcard-cat">{{ queue[reviewIdx]?.category }}</div>
          <div class="flashcard-front">
            {{ queue[reviewIdx]?.front }}
            <button class="speak-btn" title="朗读" @click.stop="speak(queue[reviewIdx]?.front)">🔊</button>
          </div>
          <template v-if="revealed">
            <div class="flashcard-divider"></div>
            <div class="flashcard-back">{{ queue[reviewIdx]?.back }}</div>
            <div v-if="queue[reviewIdx]?.note" class="flashcard-note">{{ queue[reviewIdx].note }}</div>
          </template>
        </div>
      </template>

      <!-- 选择题模式 -->
      <template v-else-if="reviewMode === 'choice'">
        <div class="flashcard choice-card">
          <div class="flashcard-label">选出正确释义</div>
          <div class="flashcard-cat">{{ current?.category }}</div>
          <div class="flashcard-front">
            {{ current?.front }}
            <button class="speak-btn" title="朗读" @click="speak(current?.front)">🔊</button>
          </div>
        </div>
        <div class="choice-options">
          <button
            v-for="(opt, i) in choiceOptions"
            :key="i"
            class="choice-option"
            :class="optionClass(opt)"
            :disabled="choiceLocked"
            @click="pickOption(opt)"
          >
            {{ opt.text }}
          </button>
        </div>
      </template>

      <!-- 拼写模式 -->
      <template v-else>
        <div class="flashcard spell-card">
          <div class="flashcard-label">根据释义拼写</div>
          <div class="flashcard-cat">{{ current?.category }}</div>
          <div class="flashcard-back">{{ current?.back }}</div>
          <div v-if="current?.note" class="flashcard-note">{{ current.note }}</div>
          <div class="spell-slots">{{ spellSlots }}</div>
          <div v-if="spellHintShown" class="spell-hint-show">首字母：{{ firstLetter }}</div>
          <div v-if="spellGraded" class="spell-result" :class="spellCorrect ? 'ok' : 'bad'">
            {{ spellCorrect ? '✓ 拼对了！' : `✗ 正确答案：${current?.front}` }}
          </div>
        </div>
        <div class="spell-input-row">
          <template v-if="!spellGraded">
            <input
              ref="spellInputRef"
              v-model="spellInput"
              class="spell-input"
              placeholder="在这里输入，回车提交"
              @keyup.enter="checkSpell"
            />
            <button class="ghost-btn" @click="spellHintShown = true">提示首字母</button>
            <button class="primary-btn" @click="checkSpell">检查</button>
          </template>
          <template v-else>
            <button class="primary-btn" @click="nextFromSpell">下一张</button>
          </template>
        </div>
      </template>

      <div v-if="reviewMode === 'flash'" class="review-actions">
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
      <p class="review-hint">{{ modeHint }}</p>
    </div>

    <!-- ==================== 列表模式 ==================== -->
    <template v-else>
      <!-- 统计面板 -->
      <div class="card stats-card">
        <div class="stats-numbers">
          <div class="stat-block">
            <div class="stat-num">{{ catCards.length }}</div>
            <div class="stat-label">总卡片</div>
          </div>
          <div class="stat-block">
            <div class="stat-num due">{{ dueInCat }}</div>
            <div class="stat-label">今日到期</div>
          </div>
          <div class="stat-block">
            <div class="stat-num ok">{{ masteredCount }}</div>
            <div class="stat-label">已掌握</div>
          </div>
          <div class="stat-block">
            <div class="stat-num bad">{{ wrongCount }}</div>
            <div class="stat-label">错题</div>
          </div>
        </div>
        <div class="box-dist">
          <div v-for="(n, lvl) in boxDist" :key="lvl" class="box-col">
            <div class="box-count">{{ n || '' }}</div>
            <div class="box-bar" :class="{ zero: !n, top: lvl === 6 }" :style="{ height: barHeight(n) }"></div>
            <div class="box-label">{{ lvl === 0 ? '新卡' : lvl + '盒' }}</div>
          </div>
        </div>
      </div>

      <!-- 工具栏 -->
      <div class="card toolbar-card">
        <h2>📖 词汇记忆</h2>
        <div class="toolbar-actions">
          <input v-model="keyword" class="search-input" placeholder="搜索卡片…" />
          <div class="mode-seg">
            <button
              v-for="m in MODES"
              :key="m.key"
              class="seg-btn"
              :class="{ active: reviewMode === m.key }"
              @click="reviewMode = m.key"
            >
              {{ m.label }}
            </button>
          </div>
          <button v-if="wrongInCat.length" class="wrong-btn" @click="startWrong">
            错题本（{{ wrongInCat.length }}）
          </button>
          <button class="review-btn" @click="startDue" :disabled="!dueFiltered.length">
            复习到期（{{ dueFiltered.length }}）
          </button>
          <button class="ghost-btn" @click="startAll" :disabled="!filtered.length">背全部</button>
          <RouterLink to="/spell" class="ghost-btn spell-link">无限拼写测试 →</RouterLink>
          <label class="auto-speak">
            <input v-model="autoSpeak" type="checkbox" /> 自动发音
          </label>
        </div>
      </div>

      <!-- 分类筛选 chips -->
      <div class="cat-chips">
        <button
          v-for="c in chipCats"
          :key="c.name"
          class="chip"
          :class="{ active: activeCat === c.name }"
          @click="activeCat = c.name"
        >
          {{ c.name }} · {{ c.count }}
        </button>
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
          {{ keyword || activeCat !== '全部' ? '当前筛选下没有卡片' : '还没有卡片，先在上面添加一张吧' }}
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
                  <div class="item-text">
                    {{ card.front }}
                    <button class="speak-btn tiny" title="朗读" @click="speak(card.front)">🔊</button>
                  </div>
                </div>
                <div class="item-back">
                  <div class="item-label">背面</div>
                  <div class="item-text">{{ card.back }}</div>
                </div>
              </div>
              <div v-if="card.note" class="item-note">{{ card.note }}</div>
              <div class="item-meta">
                <span class="cat-badge" :class="catClass(card.category)">{{ card.category }}</span>
                <span v-if="card.is_wrong" class="wrong-badge">错题</span>
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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { createVocab, deleteVocab, listVocab, reviewVocab, updateVocab } from '../api'

const CATEGORIES = ['单词', '短语', '句子', '其他']
// 拼写模式只针对「单词/短语」
const SPELL_CATS = ['单词', '短语']
const MODES = [
  { key: 'flash', label: '翻卡' },
  { key: 'choice', label: '选择题' },
  { key: 'spell', label: '拼写' },
]
const MODE_LABELS = Object.fromEntries(MODES.map((m) => [m.key, m.label]))

const PLACEHOLDERS = {
  单词: '例如：abandon',
  短语: '例如：look forward to',
  句子: '例如：The early bird catches the worm.',
  其他: '例如：不规则动词表 / 语法规则…',
}

const cards = ref([])
const listError = ref('')
const keyword = ref('')

// 分类筛选（'全部' 或具体分类名）
const activeCat = ref('全部')

// 背诵模式：flash 翻卡 / choice 选择题 / spell 拼写
const reviewMode = ref('flash')

// 自动发音开关（localStorage 持久化）
const autoSpeak = ref(localStorage.getItem('vocab_auto_speak') !== '0')
watch(autoSpeak, (v) => localStorage.setItem('vocab_auto_speak', v ? '1' : '0'))

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
const roundKnown = ref(0)
const roundWrong = ref(0)

// 选择题状态
const choiceOptions = ref([])
const choiceLocked = ref(false)
const choicePicked = ref('')

// 拼写状态
const spellInput = ref('')
const spellHintShown = ref(false)
const spellGraded = ref(false)
const spellCorrect = ref(false)
const spellInputRef = ref(null)

const frontPlaceholder = computed(() => PLACEHOLDERS[newCategory.value] || '要记的内容')
const current = computed(() => queue.value[reviewIdx.value] || null)

// ==================== 筛选 / 统计 ====================

// 当前分类下的卡片（统计口径）
const catCards = computed(() =>
  activeCat.value === '全部'
    ? cards.value
    : cards.value.filter((c) => c.category === activeCat.value)
)

// 关键字搜索叠加在分类筛选之上
const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return catCards.value
  return catCards.value.filter(
    (c) =>
      c.front.toLowerCase().includes(kw) ||
      c.back.toLowerCase().includes(kw) ||
      (c.note || '').toLowerCase().includes(kw) ||
      c.category.includes(kw)
  )
})

function isDue(card) {
  return !card.next_review_at || new Date(card.next_review_at).getTime() <= Date.now()
}

// 到期 = 新卡（从未复习）或 next_review_at <= 现在；复习队列跟随筛选
const dueFiltered = computed(() => filtered.value.filter(isDue))
const dueInCat = computed(() => catCards.value.filter(isDue).length)

// 错题本（跟随分类筛选）
const wrongInCat = computed(() => catCards.value.filter((c) => c.is_wrong))
const wrongCount = computed(() => catCards.value.filter((c) => c.is_wrong).length)

// 已掌握 = 顶盒（第 6 盒）
const masteredCount = computed(() => catCards.value.filter((c) => c.box_level >= 6).length)

// 各盒分布 [0..6]
const boxDist = computed(() => {
  const dist = Array(7).fill(0)
  catCards.value.forEach((c) => dist[Math.min(c.box_level, 6)]++)
  return dist
})
const boxMax = computed(() => Math.max(1, ...boxDist.value))

function barHeight(n) {
  if (!n) return '3px'
  return `${Math.max(12, Math.round((n / boxMax.value) * 72))}px`
}

const chipCats = computed(() => [
  { name: '全部', count: cards.value.length },
  ...CATEGORIES.map((c) => ({
    name: c,
    count: cards.value.filter((x) => x.category === c).length,
  })),
])

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

// ==================== 语音朗读（Web Speech API） ====================

function speak(text) {
  if (!text || !('speechSynthesis' in window)) return
  const u = new SpeechSynthesisUtterance(text)
  u.lang = /[\u4e00-\u9fff]/.test(text) ? 'zh-CN' : 'en-US'
  u.rate = 0.9
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(u)
}

function autoSpeakCurrent() {
  if (autoSpeak.value && current.value) speak(current.value.front)
}

// ==================== CRUD ====================

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

// 每张卡片展示前的状态复位
function resetCardState() {
  revealed.value = false
  choiceLocked.value = false
  choicePicked.value = ''
  choiceOptions.value = []
  spellInput.value = ''
  spellHintShown.value = false
  spellGraded.value = false
  spellCorrect.value = false
  if (reviewMode.value === 'choice') buildOptions()
  if (reviewMode.value === 'spell') {
    nextTick(() => spellInputRef.value?.focus())
  } else {
    autoSpeakCurrent()
  }
}

function startReview(list) {
  let arr = list
  if (reviewMode.value === 'spell') {
    arr = arr.filter((c) => SPELL_CATS.includes(c.category))
    if (!arr.length) {
      window.alert('拼写模式只支持「单词 / 短语」卡片，当前筛选下没有可背的')
      return
    }
  }
  if (!arr.length) return
  if (reviewMode.value === 'choice' && cards.value.length < 2) {
    window.alert('选择题模式至少需要 2 张卡片才能生成干扰项')
    return
  }
  queue.value = shuffle(arr)
  reviewIdx.value = 0
  roundKnown.value = 0
  roundWrong.value = 0
  reviewing.value = true
  resetCardState()
}

function startDue() {
  startReview(dueFiltered.value)
}

function startAll() {
  startReview(filtered.value)
}

function startWrong() {
  startReview(wrongInCat.value)
}

function endReview() {
  reviewing.value = false
}

// ==================== 选择题 ====================

function buildOptions() {
  const card = current.value
  if (!card) return
  const pool = cards.value.filter((c) => c.id !== card.id && c.back !== card.back)
  const sameCat = shuffle(pool.filter((c) => c.category === card.category))
  const others = shuffle(pool.filter((c) => c.category !== card.category))
  const distractors = []
  for (const c of [...sameCat, ...others]) {
    if (distractors.length >= 3) break
    if (!distractors.includes(c.back)) distractors.push(c.back)
  }
  choiceOptions.value = shuffle([
    { text: card.back, correct: true },
    ...distractors.map((t) => ({ text: t, correct: false })),
  ])
}

function pickOption(opt) {
  if (choiceLocked.value) return
  choiceLocked.value = true
  choicePicked.value = opt.text
  // 短暂停留让用户看到对错颜色，再自动评分进入下一张
  setTimeout(() => grade(opt.correct), 700)
}

function optionClass(opt) {
  if (!choiceLocked.value) return {}
  if (opt.correct) return { correct: true }
  if (opt.text === choicePicked.value) return { wrongPick: true }
  return {}
}

// ==================== 拼写 ====================

const spellSlots = computed(() => {
  const word = current.value?.front || ''
  return word
    .split('')
    .map((ch) => (ch === ' ' ? ' / ' : '_'))
    .join(' ')
})

const firstLetter = computed(() => (current.value?.front || '').trim().charAt(0).toUpperCase())

function normalizeText(s) {
  return (s || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[.,!?;:'"()（）。，！？；：、""'']/g, '')
}

function checkSpell() {
  if (spellGraded.value || !spellInput.value.trim()) return
  spellCorrect.value = normalizeText(spellInput.value) === normalizeText(current.value?.front)
  spellGraded.value = true
}

function nextFromSpell() {
  grade(spellCorrect.value)
}

const modeHint = computed(
  () =>
    ({
      flash: '认识 → 间隔拉长（明天 → 2天 → 4天 → 7天 → 15天 → 30天）；不认识 → 明天再见',
      choice: '点选释义：选对升盒，选错回新卡明天再见',
      spell: '根据释义拼写单词：答对升盒，答错明天再见',
    })[reviewMode.value]
)

async function grade(known) {
  if (grading.value) return
  grading.value = true
  const card = queue.value[reviewIdx.value]
  if (known) roundKnown.value++
  else roundWrong.value++
  try {
    await reviewVocab(card.id, known)
    if (reviewIdx.value < queue.value.length - 1) {
      reviewIdx.value++
      resetCardState()
    } else {
      reviewing.value = false
      window.alert(
        `这轮背完啦：认识 ${roundKnown.value} · 不认识 ${roundWrong.value}，明天继续 💪`
      )
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

/* ==================== 统计面板 ==================== */
.stats-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 32px;
  flex-wrap: wrap;
}
.stats-numbers {
  display: flex;
  gap: 36px;
}
.stat-block {
  text-align: center;
}
.stat-num {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
}
.stat-num.due {
  color: #c2410c;
}
.stat-num.ok {
  color: #059669;
}
.stat-num.bad {
  color: #dc2626;
}
.stat-label {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}
.box-dist {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  height: 110px;
}
.box-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  height: 100%;
  justify-content: flex-end;
}
.box-count {
  font-size: 11px;
  color: #6b7280;
  min-height: 14px;
}
.box-bar {
  width: 22px;
  border-radius: 4px 4px 2px 2px;
  background: #ddd6fe;
  min-height: 3px;
}
.box-bar.zero {
  background: #f3f4f6;
}
.box-bar.top {
  background: #10b981;
}
.box-label {
  font-size: 11px;
  color: #9ca3af;
  white-space: nowrap;
}

/* ==================== 工具栏 ==================== */
.toolbar-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}
.toolbar-card h2 {
  margin-bottom: 0;
}
.toolbar-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.search-input {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 14px;
  outline: none;
  width: 160px;
}
.search-input:focus {
  border-color: #8b5cf6;
}
/* 背诵模式切换 */
.mode-seg {
  display: flex;
  border: 1px solid #ddd6fe;
  border-radius: 8px;
  overflow: hidden;
}
.seg-btn {
  background: #fff;
  color: #7c3aed;
  border: none;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
}
.seg-btn + .seg-btn {
  border-left: 1px solid #ddd6fe;
}
.seg-btn.active {
  background: #8b5cf6;
  color: #fff;
}
.auto-speak {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #4b5563;
  cursor: pointer;
  user-select: none;
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
.wrong-btn {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 8px 18px;
  font-size: 14px;
  cursor: pointer;
}
.wrong-btn:hover {
  background: #fee2e2;
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

/* ==================== 分类 chips ==================== */
.cat-chips {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.chip {
  background: #fff;
  color: #4b5563;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 7px 18px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.chip:hover {
  border-color: #a78bfa;
  color: #7c3aed;
}
.chip.active {
  background: #8b5cf6;
  border-color: #8b5cf6;
  color: #fff;
}

/* ==================== 表单 ==================== */
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

/* ==================== 朗读按钮 ==================== */
.speak-btn {
  background: #ede9fe;
  border: none;
  border-radius: 50%;
  width: 34px;
  height: 34px;
  font-size: 15px;
  cursor: pointer;
  vertical-align: middle;
  margin-left: 8px;
  flex-shrink: 0;
}
.speak-btn:hover {
  background: #ddd6fe;
}
.speak-btn.tiny {
  width: 24px;
  height: 24px;
  font-size: 11px;
  margin-left: 6px;
  padding: 0;
  line-height: 1;
}

/* ==================== 列表 ==================== */
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
.wrong-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 12px;
  background: #fee2e2;
  color: #991b1b;
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
  gap: 12px;
}
.review-progress {
  font-size: 14px;
  color: #6b7280;
  display: flex;
  align-items: center;
  gap: 8px;
}
.mode-badge {
  background: #ede9fe;
  color: #7c3aed;
  font-size: 12px;
  padding: 1px 10px;
  border-radius: 10px;
}
.round-score {
  font-size: 13px;
  color: #6b7280;
  margin-right: auto;
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
.choice-card,
.spell-card {
  cursor: default;
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
  display: flex;
  align-items: center;
  gap: 4px;
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

/* ==================== 选择题 ==================== */
.choice-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 20px;
}
.choice-option {
  background: #fff;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px 18px;
  font-size: 15px;
  color: #1f2937;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s;
  word-break: break-word;
}
.choice-option:hover:not(:disabled) {
  border-color: #a78bfa;
  background: #f8f7ff;
}
.choice-option:disabled {
  cursor: default;
}
.choice-option.correct {
  border-color: #10b981;
  background: #ecfdf5;
  color: #065f46;
}
.choice-option.wrongPick {
  border-color: #ef4444;
  background: #fef2f2;
  color: #991b1b;
}
@media (max-width: 640px) {
  .choice-options {
    grid-template-columns: 1fr;
  }
}

/* ==================== 拼写 ==================== */
.spell-slots {
  font-size: 22px;
  letter-spacing: 4px;
  color: #7c3aed;
  font-weight: 600;
  font-family: 'Courier New', monospace;
}
.spell-hint-show {
  font-size: 14px;
  color: #c2410c;
}
.spell-result {
  font-size: 15px;
  font-weight: 600;
}
.spell-result.ok {
  color: #059669;
}
.spell-result.bad {
  color: #dc2626;
}
.spell-input-row {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}
.spell-input {
  border: 2px solid #ddd6fe;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 16px;
  outline: none;
  width: 260px;
  text-align: center;
}
.spell-input:focus {
  border-color: #8b5cf6;
}
</style>
