<template>
  <section class="stats-view">
    <h2>📊 学习统计</h2>

    <!-- 加载失败 -->
    <div v-if="error" class="card error-box">
      <p>统计加载失败：{{ error }}</p>
      <button class="primary-btn" @click="load">重试</button>
    </div>

    <template v-else-if="stats">
      <!-- 指标卡 -->
      <div class="big-cards">
        <div class="big-card due">
          <div class="num">{{ stats.today_due }}</div>
          <div class="label">今日待复习</div>
        </div>
        <div class="big-card reviewed">
          <div class="num">{{ stats.today_reviewed }}</div>
          <div class="label">今日已复习</div>
        </div>
        <div class="big-card acc">
          <div class="num">{{ (stats.weekly_accuracy * 100).toFixed(0) }}<small>%</small></div>
          <div class="label">近 7 天正确率</div>
        </div>
        <div class="big-card mastered">
          <div class="num">{{ stats.mastered }}<small>/ {{ stats.total_cards }}</small></div>
          <div class="label">已掌握 / 总数</div>
        </div>
        <div class="big-card streak">
          <div class="num">{{ stats.streak_days }}<small> 天</small></div>
          <div class="label">🔥 连续打卡</div>
        </div>
      </div>

      <!-- 7 天柱状图 -->
      <div class="card chart-card">
        <div class="chart-head">
          <h3>📈 近 7 天复习情况</h3>
          <span class="chart-summary">
            共复习 <b>{{ weekTotal.reviewed }}</b> 次 · 正确 <b>{{ weekTotal.correct }}</b> 次
          </span>
        </div>
        <div class="big-chart">
          <div v-for="d in stats.daily" :key="d.date" class="bar-col">
            <span class="bar-num">{{ d.reviewed || '' }}</span>
            <div class="bar-track" :title="`${d.date} 复习 ${d.reviewed} 次，正确 ${d.correct} 次`">
              <div class="bar" :style="{ height: barH(d.reviewed) + '%' }"></div>
            </div>
            <div class="bar-date">{{ shortDate(d.date) }}</div>
            <div class="bar-acc">{{ accText(d) }}</div>
          </div>
        </div>
      </div>
    </template>

    <!-- 加载中 -->
    <div v-else class="card loading-box">加载中…</div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getVocabStats } from '../api'

const stats = ref(null)
const error = ref('')

const weekTotal = computed(() => {
  const daily = stats.value?.daily || []
  return {
    reviewed: daily.reduce((s, d) => s + d.reviewed, 0),
    correct: daily.reduce((s, d) => s + d.correct, 0),
  }
})

async function load() {
  error.value = ''
  try {
    stats.value = await getVocabStats()
  } catch (e) {
    error.value = e?.response?.data?.detail || '网络错误'
  }
}

const barH = (n) => {
  if (!stats.value || !n) return 0
  const mx = Math.max(1, ...stats.value.daily.map((d) => d.reviewed))
  return Math.max(8, (n / mx) * 100)
}
const shortDate = (iso) => {
  const [, m, d] = iso.split('-')
  return `${Number(m)}/${Number(d)}`
}
const accText = (d) => (d.reviewed ? `${Math.round((d.correct / d.reviewed) * 100)}%` : '—')

onMounted(load)
</script>

<style scoped>
.stats-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 10px 0 30px 0;
}
h2 { margin: 0; font-size: 20px; }
h3 { margin: 0; font-size: 17px; }

.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}
.error-box, .loading-box { color: #6b7280; text-align: center; }

/* ====== 指标大卡 ====== */
.big-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}
.big-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 22px 16px;
  text-align: center;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}
.big-card .num {
  font-size: 34px;
  font-weight: 700;
  line-height: 1.2;
}
.big-card .num small { font-size: 15px; color: #9ca3af; font-weight: 500; }
.big-card .label { margin-top: 6px; color: #6b7280; font-size: 14px; }
.big-card.due .num { color: #ef4444; }
.big-card.reviewed .num { color: #3b82f6; }
.big-card.acc .num { color: #10b981; }
.big-card.mastered .num { color: #6366f1; }
.big-card.streak .num { color: #f59e0b; }

/* ====== 图表 ====== */
.chart-card { padding: 20px 24px; }
.chart-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 16px;
}
.chart-summary { color: #6b7280; font-size: 13px; }
.chart-summary b { color: #3b82f6; }

.big-chart {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 14px;
  height: 200px;
}
.bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  height: 100%;
}
.bar-num {
  height: 18px;
  line-height: 18px;
  font-size: 12px;
  color: #374151;
  font-weight: 600;
}
.bar-track {
  flex: 1;
  width: 100%;
  max-width: 42px;
  background: #f3f4f6;
  border-radius: 8px;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}
.bar {
  width: 100%;
  background: linear-gradient(180deg, #60a5fa, #3b82f6);
  border-radius: 6px 6px 0 0;
  transition: height 0.4s ease;
}
.bar-date {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}
.bar-acc {
  margin-top: 2px;
  font-size: 11px;
  color: #9ca3af;
  white-space: nowrap;
}

/* ====== 按钮 ====== */
.primary-btn {
  padding: 8px 18px;
  border: none;
  border-radius: 10px;
  background: #4f46e5;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.primary-btn:hover { background: #4338ca; }

@media (max-width: 900px) {
  .big-cards { grid-template-columns: repeat(2, 1fr); }
}
</style>
