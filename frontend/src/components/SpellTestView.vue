<template>
  <section class="spell-view">
    <!-- 轻量提示条 -->
    <div v-if="toastMsg" class="spell-toast">{{ toastMsg }}</div>

    <!-- ========== ① 设置 ========== -->
    <div v-if="stage === 'setup'" class="card setup-card">
      <h2 class="spell-title">⌨️ 拼写测试</h2>
      <p class="spell-desc">
        看中文释义，拼出英文单词。答完出成绩，错的可以单独再练一遍。
      </p>

      <div class="setup-rows">
        <div class="setup-row">
          <label>分类</label>
          <select v-model="category">
            <option value="">全部分类</option>
            <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>

        <div class="setup-row">
          <label>选题范围</label>
          <div class="radio-group">
            <label><input type="radio" v-model="source" value="due" /> 到期卡片</label>
            <label><input type="radio" v-model="source" value="wrong" /> 我的错题</label>
            <label><input type="radio" v-model="source" value="all" /> 全部卡片</label>
          </div>
        </div>

        <div class="setup-row">
          <label>题量</label>
          <select v-model.number="count">
            <option :value="10">10 题</option>
            <option :value="20">20 题</option>
            <option :value="50">50 题</option>
          </select>
        </div>
      </div>

      <p v-if="poolHint" class="pool-hint">{{ poolHint }}</p>

      <div class="setup-actions">
        <!-- 必须写成 startTest()：直接传函数引用会把 MouseEvent 当成 poolOverride 参数 -->
        <button class="primary-btn" :disabled="loadingPool" @click="startTest()">
          {{ loadingPool ? '出题中…' : '开始测试' }}
        </button>
        <router-link class="ghost-btn link-btn" to="/vocab">返回词汇本</router-link>
      </div>
    </div>

    <!-- ========== ② 答题 ========== -->
    <div v-else-if="stage === 'testing'" class="card quiz-card">
      <div class="quiz-top">
        <div class="progress-wrap">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: ((idx + 1) / questions.length) * 100 + '%' }"></div>
          </div>
          <span class="quiz-progress">
            第 {{ idx + 1 }} / {{ questions.length }} 题 · 已答对 {{ correctCount }}
          </span>
        </div>
        <button class="ghost-btn small" @click="abortTest">退出测试</button>
      </div>

      <!-- 谜面：中文释义 -->
      <div class="puzzle">
        <div class="puzzle-cat">{{ current.category }}</div>
        <div class="puzzle-clue">{{ current.back }}</div>
        <div v-if="current.note" class="puzzle-note">{{ current.note }}</div>
      </div>

      <!-- 谜底：英文单词（输入） -->
      <div class="answer-wrap">
        <button class="speak-btn" type="button" @click="speakAnswer" title="听发音">🔊</button>
        <input
          ref="inputRef"
          v-model="typed"
          class="answer-input"
          :class="{ right: status === 'right', wrong: status === 'wrong' }"
          :placeholder="placeholder"
          :disabled="status !== 'idle'"
          @keydown.enter="onEnter"
          autofocus
        />
        <!-- 答完（对或错）后就变成「下一题」，避免重复提交导致重复记分 -->
        <button v-if="status === 'idle'" class="primary-btn" @click="submitAnswer">提交</button>
        <button v-else class="success-btn" @click="nextQuestion">下一题 →</button>
      </div>

      <!-- 提示区 -->
      <div class="hint-area">
        <button class="ghost-btn small" :disabled="status === 'right'" @click="showHint">
          提示{{ hintLevel > 0 ? `（${hintLevel}）` : '' }}
        </button>
        <button v-if="status !== 'right'" class="ghost-btn small" @click="revealAnswer">
          不会 / 看答案
        </button>
        <div v-if="hintText" class="hint-text">{{ hintText }}</div>
      </div>

      <!-- 判分结果 -->
      <div v-if="status === 'right'" class="feedback ok">✅ 拼对了！</div>
      <div v-else-if="status === 'wrong'" class="feedback bad">
        ❌ 正确答案：<b>{{ current.front }}</b>
        <span v-if="usedHint" class="feedback-note">（用了提示，这题不算完全掌握）</span>
      </div>
    </div>

    <!-- ========== ③ 结算 ========== -->
    <div v-else class="card result-card">
      <h2 class="spell-title">🎉 测试完成</h2>

      <div class="result-stats">
        <div class="result-stat"><b>{{ scoreRate }}%</b><span>正确率</span></div>
        <div class="result-stat"><b>{{ correctCount }}</b><span>答对</span></div>
        <div class="result-stat"><b>{{ questions.length - correctCount }}</b><span>答错</span></div>
        <div class="result-stat"><b>{{ elapsedText }}</b><span>用时</span></div>
      </div>

      <p v-if="wrongList.length === 0" class="result-perfect">全部拼对，厉害！👏</p>

      <div v-else class="result-wrong">
        <div class="result-wrong-title">再看一遍这些（{{ wrongList.length }}）：</div>
        <div class="wrong-table">
          <div v-for="w in wrongList" :key="w.id" class="wrong-row">
            <span class="wrong-front">{{ w.front }}</span>
            <span class="wrong-back">{{ w.back }}</span>
            <button class="speak-btn tiny" type="button" @click="speak(w.front)" title="发音">🔊</button>
          </div>
        </div>
      </div>

      <div class="result-actions">
        <button v-if="wrongList.length" class="warn-btn" @click="retryWrong">只练错的（{{ wrongList.length }}）</button>
        <button class="primary-btn" @click="restart">再来一组</button>
        <router-link class="ghost-btn link-btn" to="/vocab">返回词汇本</router-link>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { listVocabAll, listVocabDue, listWrongVocab, reviewVocab } from '../api.js'
import { speak } from '../speech.js'

const CATEGORIES = ['单词', '短语', '句子', '其他']

// ---------- 状态 ----------
const stage = ref('setup') // setup | testing | result
const category = ref('')
const source = ref('due') // due | wrong | all
const count = ref(10)
const loadingPool = ref(false)

const questions = ref([])
const idx = ref(0)
const typed = ref('')
const status = ref('idle') // idle | right | wrong
const hintLevel = ref(0)
const hintText = ref('')
const usedHint = ref(false)
const results = ref([]) // { id, front, back, ok }

const startedAt = ref(0)
const elapsedSec = ref(0)
const inputRef = ref(null)
const toastMsg = ref('')

let toastTimer = null
function toast(msg) {
  toastMsg.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toastMsg.value = ''), 2200)
}

const current = computed(() => questions.value[idx.value] || { front: '', back: '', category: '', note: '' })
const correctCount = computed(() => results.value.filter((r) => r.ok).length)
const wrongList = computed(() => results.value.filter((r) => !r.ok))
const scoreRate = computed(() =>
  results.value.length ? Math.round((correctCount.value / results.value.length) * 100) : 0
)
const elapsedText = computed(() => {
  const s = elapsedSec.value
  if (s < 60) return `${s} 秒`
  return `${Math.floor(s / 60)} 分 ${s % 60} 秒`
})
const placeholder = computed(() => `拼出「${current.value.back || ''}」对应的英文`)
const poolHint = computed(() => {
  if (source.value === 'wrong') return '只从最近一次没答对的卡片里出题。'
  if (source.value === 'due') return '只从今天该复习的卡片里出题。'
  return '从所有卡片里随机出题。'
})

// ---------- 出题 ----------
async function fetchPool() {
  if (source.value === 'due') return await listVocabDue({ category: category.value })
  if (source.value === 'wrong') return await listWrongVocab({ limit: 200, category: category.value })
  return await listVocabAll({ category: category.value, maxCount: 200 })
}

async function startTest(poolOverride) {
  loadingPool.value = true
  try {
    let pool = poolOverride
    if (!pool) {
      pool = await fetchPool()
    }
    // 只保留能当谜底的卡（有正面英文 + 背面释义）
    pool = (pool || []).filter((c) => c.front && c.back)
    if (!pool.length) {
      toast('这个范围内没有可用的卡片')
      return
    }
    const shuffled = pool.slice()
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
    }
    questions.value = shuffled.slice(0, count.value)
    idx.value = 0
    results.value = []
    resetQuestionUI()
    startedAt.value = Date.now()
    elapsedSec.value = 0
    stage.value = 'testing'
    nextTick(() => inputRef.value?.focus())
  } catch (e) {
    toast(e?.response?.data?.detail || '出题失败，请重试')
  } finally {
    loadingPool.value = false
  }
}

function resetQuestionUI() {
  typed.value = ''
  status.value = 'idle'
  hintLevel.value = 0
  hintText.value = ''
  usedHint.value = false
  nextTick(() => inputRef.value?.focus())
}

// 判分前归一化：大小写、多余空格、首尾标点都不算错
function normalize(s) {
  return (s || '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/^[.,!?;:'"]+|[.,!?;:'"]+$/g, '')
    .trim()
}

// ---------- 答题 ----------
function onEnter() {
  if (status.value === 'right') nextQuestion()
  else submitAnswer()
}

function submitAnswer() {
  if (status.value === 'right') return
  const ans = normalize(typed.value)
  if (!ans) return
  if (ans === normalize(current.value.front)) {
    status.value = 'right'
    speak(current.value.front)
    grade(usedHint.value ? 1 : 2)
  } else {
    status.value = 'wrong'
  }
}

function revealAnswer() {
  if (status.value !== 'idle') return
  usedHint.value = true
  status.value = 'wrong'
  typed.value = current.value.front
  speak(current.value.front)
  grade(0)
}

async function grade(g) {
  const card = current.value
  if (!card?.id) return
  try {
    await reviewVocab(card.id, g, 'spell')
  } catch (e) {
    // 评分失败不能影响做题，记下来继续
    toast('这题的复习进度没记上：' + (e?.response?.data?.detail || e?.message || '请求失败'))
  }
}

// 提示分 3 级：首字母+长度 → 打乱的字母 → 完整答案
function showHint() {
  const answer = current.value.front || ''
  if (!answer) return
  usedHint.value = true
  hintLevel.value += 1
  if (hintLevel.value === 1) {
    hintText.value = `${answer[0]}${' _'.repeat(Math.max(answer.length - 1, 0))}  （${answer.length} 个字母）`
  } else if (hintLevel.value === 2) {
    const letters = answer.replace(/\s+/g, '').split('')
    for (let i = letters.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[letters[i], letters[j]] = [letters[j], letters[i]]
    }
    hintText.value = `字母池：${letters.join(' ')}`
  } else {
    hintText.value = `答案：${answer}`
  }
}

function speakAnswer() {
  speak(current.value.front)
}

function nextQuestion() {
  // 记录这一题的结果
  const card = current.value
  const ok = status.value === 'right'
  const exist = results.value.find((r) => r.id === card.id)
  if (exist) exist.ok = ok
  else results.value.push({ id: card.id, front: card.front, back: card.back, ok })

  if (idx.value + 1 >= questions.value.length) {
    elapsedSec.value = Math.round((Date.now() - startedAt.value) / 1000)
    stage.value = 'result'
    return
  }
  idx.value += 1
  resetQuestionUI()
}

function abortTest() {
  if (!confirm('退出测试？本次已答的题目不会记录成绩。')) return
  stage.value = 'setup'
}

// ---------- 结算后 ----------
function restart() {
  stage.value = 'setup'
}

async function retryWrong() {
  const wrongIds = new Set(wrongList.value.map((w) => w.id))
  const pool = questions.value.filter((c) => wrongIds.has(c.id))
  results.value = []
  questions.value = pool
  idx.value = 0
  resetQuestionUI()
  startedAt.value = Date.now()
  elapsedSec.value = 0
  stage.value = 'testing'
}

onMounted(() => {
  pickVoice() // 预热语音引擎，避免第一次点发音有延迟
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }
})
</script>

<style scoped>
.spell-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 6px 0 30px 0;
}
.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 22px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}
.spell-title {
  font-size: 20px;
  margin-bottom: 6px;
  color: #1f2937;
}
.spell-desc {
  color: #6b7280;
  font-size: 13px;
  margin-bottom: 18px;
}

/* ---------- 设置 ---------- */
.setup-rows {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.setup-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.setup-row > label:first-child {
  width: 64px;
  font-size: 13px;
  color: #4b5563;
  flex-shrink: 0;
}
.setup-row select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  background: #fff;
}
.radio-group {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}
.radio-group label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
}
.pool-hint {
  margin-top: 14px;
  font-size: 12px;
  color: #6b7280;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 8px 12px;
}
.setup-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  flex-wrap: wrap;
}
.link-btn {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  padding: 9px 16px;
  border-radius: 8px;
}

/* ---------- 答题 ---------- */
.quiz-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.progress-wrap {
  flex: 1;
  min-width: 180px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.progress-bar {
  flex: 1;
  height: 8px;
  background: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: #4f46e5;
  border-radius: 999px;
  transition: width 0.25s;
}
.quiz-progress {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

/* 谜面 */
.puzzle {
  text-align: center;
  padding: 22px 16px;
  background: linear-gradient(135deg, #eef2ff, #f5f3ff);
  border-radius: 12px;
  margin-bottom: 18px;
}
.puzzle-cat {
  display: inline-block;
  font-size: 12px;
  color: #4f46e5;
  background: #fff;
  border-radius: 999px;
  padding: 2px 10px;
  margin-bottom: 10px;
}
.puzzle-clue {
  font-size: 26px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.35;
  word-break: break-word;
}
.puzzle-note {
  margin-top: 8px;
  font-size: 13px;
  color: #64748b;
}

/* 输入 */
.answer-wrap {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.answer-input {
  flex: 1;
  min-width: 180px;
  padding: 12px 14px;
  font-size: 17px;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  outline: none;
  font-family: inherit;
}
.answer-input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12);
}
.answer-input.right {
  border-color: #10b981;
  background: #ecfdf5;
}
.answer-input.wrong {
  border-color: #ef4444;
  background: #fef2f2;
}

.hint-area {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.hint-text {
  font-size: 13px;
  color: #b45309;
  background: #fffbeb;
  border-radius: 8px;
  padding: 6px 12px;
  word-break: break-word;
}

.feedback {
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
}
.feedback.ok {
  background: #ecfdf5;
  color: #047857;
}
.feedback.bad {
  background: #fef2f2;
  color: #b91c1c;
}
.feedback-note {
  font-size: 12px;
  color: #9ca3af;
  margin-left: 6px;
}

/* ---------- 结算 ---------- */
.result-stats {
  display: flex;
  gap: 26px;
  justify-content: center;
  margin: 18px 0;
  flex-wrap: wrap;
}
.result-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.result-stat b {
  font-size: 26px;
  color: #4f46e5;
}
.result-stat span {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}
.result-perfect {
  text-align: center;
  color: #047857;
  margin-bottom: 12px;
}
.result-wrong-title {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 8px;
}
.wrong-table {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 260px;
  overflow-y: auto;
}
.wrong-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fef2f2;
  border-radius: 8px;
  padding: 8px 12px;
}
.wrong-front {
  font-weight: 600;
  color: #b91c1c;
  min-width: 120px;
}
.wrong-back {
  color: #6b7280;
  font-size: 13px;
  flex: 1;
}
.result-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  flex-wrap: wrap;
}

/* ---------- 提示条 ---------- */
.spell-toast {
  position: fixed;
  left: 50%;
  top: 18px;
  transform: translateX(-50%);
  z-index: 50;
  background: rgba(17, 24, 39, 0.92);
  color: #fff;
  font-size: 13px;
  padding: 10px 18px;
  border-radius: 999px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.18);
}

/* ---------- 通用按钮（沿用项目既有配色） ---------- */
.primary-btn {
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-size: 14px;
  cursor: pointer;
}
.primary-btn:hover:not(:disabled) { background: #4338ca; }
.primary-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.success-btn {
  background: #10b981;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-size: 14px;
  cursor: pointer;
}
.warn-btn {
  background: #f59e0b;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-size: 14px;
  cursor: pointer;
}
.ghost-btn {
  background: #fff;
  color: #4b5563;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 9px 16px;
  font-size: 13px;
  cursor: pointer;
}
.ghost-btn:hover { border-color: #9ca3af; }
.ghost-btn.small { padding: 7px 12px; font-size: 12px; }
.speak-btn {
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 9px 12px;
  cursor: pointer;
  font-size: 15px;
}
.speak-btn.tiny { padding: 3px 7px; font-size: 12px; }

@media (max-width: 640px) {
  .puzzle-clue { font-size: 22px; }
  .result-stats { gap: 16px; }
}
</style>
