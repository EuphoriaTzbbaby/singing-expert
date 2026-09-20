<template>
  <section class="spell-view">
    <!-- 顶部统计 + 操作 -->
    <div class="top-bar">
      <div class="stats">
        <span class="stat ok">✓ 对 {{ stats.correct }}</span>
        <span class="stat bad">✗ 错 {{ stats.wrong }}</span>
        <span class="stat streak">🔥 连对 {{ stats.streak }}</span>
        <span class="stat total">题库 {{ cards.length }}</span>
      </div>
      <button class="exit-btn" @click="goBack">← 退出测试</button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="state">加载词汇表…</div>

    <!-- 空状态 -->
    <div v-else-if="!cards.length" class="state empty">
      <p>词汇表还是空的，没法测试。</p>
      <RouterLink to="/vocab" class="primary-btn">去添加卡片</RouterLink>
    </div>

    <!-- 题目区域 -->
    <div v-else class="card quiz-card">
      <div class="prompt-label">中文释义（输入对应英文）</div>
      <h2 class="prompt">
        {{ current.prompt }}
        <button class="speak-btn" type="button" @click="speak(current.prompt)" title="朗读中文">🔊</button>
      </h2>

      <form @submit.prevent="onSubmit">
        <input
          ref="inputRef"
          v-model="answer"
          class="answer-input"
          :class="{ correct: judged === 'correct', wrong: judged === 'wrong' }"
          placeholder="输入英文单词或短语…"
          autocomplete="off"
          autocapitalize="off"
          spellcheck="false"
          :disabled="judged !== ''"
        />
        <div class="actions">
          <button v-if="!judged" type="submit" class="primary-btn" :disabled="!answer.trim()">
            提交（Enter）
          </button>
          <button v-else type="button" class="primary-btn" @click="next">
            下一题（Enter）
          </button>
          <button v-if="!judged" type="button" class="ghost-btn" @click="onGiveUp">
            放弃看答案
          </button>
        </div>
      </form>

      <!-- 判定结果 -->
      <div v-if="judged === 'correct'" class="result correct">
        ✓ 答对了
        <button v-if="current.accepted[0]" class="speak-btn-sm" type="button" @click="speak(current.accepted[0])" title="朗读答案">🔊</button>
      </div>
      <div v-else-if="judged === 'wrong'" class="result wrong">
        ✗ 答错了。正确答案：<b>{{ current.accepted.join(' / ') }}</b>
        <button v-if="current.accepted[0]" class="speak-btn-sm" type="button" @click="speak(current.accepted[0])" title="朗读答案">🔊</button>
        <div v-if="current.note" class="note">备注：{{ current.note }}</div>
      </div>
      <div v-else-if="judged === 'gaveup'" class="result gaveup">
        正确答案：<b>{{ current.accepted.join(' / ') }}</b>
        <button v-if="current.accepted[0]" class="speak-btn-sm" type="button" @click="speak(current.accepted[0])" title="朗读答案">🔊</button>
        <div v-if="current.note" class="note">备注：{{ current.note }}</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listVocab } from '../api'

const router = useRouter()

const cards = ref([])          // 全量词汇卡
const loading = ref(true)
const inputRef = ref(null)

// 统计
const stats = ref({ correct: 0, wrong: 0, streak: 0 })

// 当前题
const current = ref({ prompt: '', accepted: [], note: '', cardId: null })
const answer = ref('')
const judged = ref('')  // '' | 'correct' | 'wrong' | 'gaveup'

// 防重：最近 N 个 cardId 不再出
const RECENT_SIZE = 10
const recentIds = ref([])

// 谜面 -> 可接受答案集合（同一中文可能对应多张卡的英文）
const promptMap = computed(() => {
  const m = new Map()
  for (const c of cards.value) {
    const key = (c.back || '').trim()
    if (!key) continue
    if (!m.has(key)) m.set(key, [])
    m.get(key).push(c)
  }
  return m
})

function pickNext() {
  // 防重窗口：最多 10，但不能超过题库-1（保证至少有 1 张可选）
  const validCards = cards.value.filter(c => (c.back || '').trim() && (c.front || '').trim())
  const recentLimit = Math.min(RECENT_SIZE, Math.max(0, validCards.length - 1))

  // 排除最近出过的
  let pool = validCards.filter(c => !recentIds.value.includes(c.id))
  if (!pool.length) {
    // 理论上不会发生（recentLimit < 题库），保险起见退化为只避免连续重复
    const lastId = recentIds.value[recentIds.value.length - 1]
    pool = validCards.filter(c => c.id !== lastId)
    if (!pool.length) pool = validCards
    if (!pool.length) return null
  }
  const card = pool[Math.floor(Math.random() * pool.length)]
  // 防重入队
  recentIds.value.push(card.id)
  while (recentIds.value.length > recentLimit) recentIds.value.shift()

  // 谜面 = back；可接受答案 = 所有同 back 的 front（去重 + 规范化）
  const key = (card.back || '').trim()
  const sameBackCards = promptMap.value.get(key) || []
  const acceptedSet = new Set()
  for (const sc of sameBackCards) {
    const f = (sc.front || '').trim()
    if (f) acceptedSet.add(f)
  }
  return {
    prompt: key,
    accepted: [...acceptedSet],
    note: card.note || '',
    cardId: card.id,
  }
}

function next() {
  const n = pickNext()
  if (!n) {
    current.value = { prompt: '(没有可用题目)', accepted: [], note: '', cardId: null }
    return
  }
  current.value = n
  answer.value = ''
  judged.value = ''
  nextTick(() => inputRef.value?.focus())
  // 出题时自动朗读中文谜面
  speak(n.prompt)
}

// 朗读：自动识别中英语言
function speak(text) {
  if (!text || !('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.lang = /[\u4e00-\u9fff]/.test(text) ? 'zh-CN' : 'en-US'
  u.rate = 0.9
  window.speechSynthesis.speak(u)
}

function normalize(s) {
  return (s || '').trim().toLowerCase().replace(/\s+/g, ' ')
}

function onSubmit() {
  if (judged.value) return
  const userAns = normalize(answer.value)
  if (!userAns) return
  const ok = current.value.accepted.some(a => normalize(a) === userAns)
  judged.value = ok ? 'correct' : 'wrong'
  if (ok) {
    stats.value.correct++
    stats.value.streak++
  } else {
    stats.value.wrong++
    stats.value.streak = 0
  }
}

function onGiveUp() {
  if (judged.value) return
  judged.value = 'gaveup'
  stats.value.wrong++
  stats.value.streak = 0
}

function goBack() {
  router.push('/vocab')
}

onMounted(async () => {
  try {
    const list = await listVocab()
    cards.value = list
  } finally {
    loading.value = false
    next()
  }
})
</script>

<style scoped>
.spell-view {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stats {
  display: flex;
  gap: 16px;
  font-size: 14px;
}
.stat {
  padding: 4px 12px;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.stat.ok { color: #059669; }
.stat.bad { color: #dc2626; }
.stat.streak { color: #d97706; }
.stat.total { color: #6b7280; }
.exit-btn {
  background: #6b7280;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 14px;
  cursor: pointer;
  font-size: 13px;
  text-decoration: none;
}
.exit-btn:hover { background: #4b5563; }
.state {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  color: #6b7280;
  font-size: 15px;
}
.state.empty {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}
.quiz-card {
  background: #fff;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.prompt-label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 12px;
}
.prompt {
  font-size: 32px;
  color: #1f2937;
  margin-bottom: 28px;
  line-height: 1.3;
  display: flex;
  align-items: center;
  gap: 12px;
}
.speak-btn {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  opacity: 0.7;
  transition: opacity 0.15s, transform 0.1s;
}
.speak-btn:hover {
  opacity: 1;
  transform: scale(1.15);
}
.speak-btn:active {
  transform: scale(0.9);
}
.speak-btn-sm {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  opacity: 0.7;
  vertical-align: middle;
}
.speak-btn-sm:hover { opacity: 1; }
.answer-input {
  width: 100%;
  border: 2px solid #d1d5db;
  border-radius: 8px;
  padding: 14px 16px;
  font-size: 18px;
  outline: none;
  transition: border-color 0.15s;
}
.answer-input:focus { border-color: #2563eb; }
.answer-input.correct { border-color: #059669; background: #ecfdf5; }
.answer-input.wrong { border-color: #dc2626; background: #fef2f2; }
.answer-input:disabled { cursor: not-allowed; }
.actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}
.primary-btn {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 22px;
  font-size: 14px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}
.primary-btn:hover:not(:disabled) { background: #1d4ed8; }
.primary-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ghost-btn {
  background: transparent;
  color: #6b7280;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px 18px;
  font-size: 14px;
  cursor: pointer;
}
.ghost-btn:hover { background: #f9fafb; }
.result {
  margin-top: 20px;
  padding: 14px 18px;
  border-radius: 8px;
  font-size: 15px;
}
.result.correct {
  background: #ecfdf5;
  color: #065f46;
}
.result.wrong {
  background: #fef2f2;
  color: #991b1b;
}
.result.gaveup {
  background: #f3f4f6;
  color: #374151;
}
.result b { color: #1f2937; }
.note {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
}
</style>
