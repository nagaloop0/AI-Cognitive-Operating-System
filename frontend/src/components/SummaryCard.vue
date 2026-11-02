<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Sparkles, RefreshCw, Lightbulb, Target, AlertCircle, Moon } from '@lucide/vue'
import type { DailySummary } from '@/types'

const summary = ref<DailySummary | null>(null)
const isLoading = ref(false)
const errorMessage = ref('')

const CATEGORY_COLORS: Record<string, string> = {
  work: 'var(--accent-indigo)',
  learning: 'var(--accent-emerald)',
  fun: 'var(--accent-amber)',
  communication: 'var(--accent-cyan)',
  other: 'var(--text-muted)',
}

// Local calendar date as YYYY-MM-DD (toISOString would use UTC and can be off by one day)
function localIsoDate(offsetDays: number): string {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const today = localIsoDate(0)
const yesterday = localIsoDate(-1)
const selectedDay = ref(yesterday)
const isEmpty = computed(() => summary.value !== null && summary.value.active_minutes === 0)
const maxMinutes = computed(() => Math.max(1, ...(summary.value?.time_split.map((t) => t.minutes) ?? [1])))
const categoryTotal = computed(() =>
  Object.values(summary.value?.category_minutes ?? {}).reduce((sum, m) => sum + m, 0),
)

async function loadSummary(refresh = false) {
  if (isLoading.value) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    const params = new URLSearchParams({ day: selectedDay.value, refresh: String(refresh) })
    const res = await fetch(`/api/summary/daily?${params}`)
    if (!res.ok) throw new Error(`API error ${res.status}`)
    summary.value = (await res.json()) as DailySummary
  } catch (err) {
    errorMessage.value = 'Could not load the summary. Is the API running on port 8000?'
    console.error('Failed to load daily summary', err)
  } finally {
    isLoading.value = false
  }
}

function formatMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h && m) return `${h} h ${m} min`
  return h ? `${h} h` : `${m} min`
}

watch(selectedDay, (day) => {
  if (day) loadSummary()
})
onMounted(() => loadSummary())
</script>

<template>
  <section class="glass-panel summary-card">
    <header class="card-header">
      <div class="title-group">
        <Sparkles :size="20" class="title-icon" />
        <div>
          <h2>Daily Summary</h2>
          <p class="subtitle">Written on this Mac by a local AI model. Nothing leaves your device.</p>
        </div>
      </div>
      <div class="actions">
        <div class="day-toggle" role="group" aria-label="Choose day">
          <button :class="{ active: selectedDay === yesterday }" @click="selectedDay = yesterday">Yesterday</button>
          <button :class="{ active: selectedDay === today }" @click="selectedDay = today">Today</button>
        </div>
        <input v-model="selectedDay" class="day-picker" type="date" :max="today" aria-label="Pick a day" />
        <button class="icon-btn" :class="{ spinning: isLoading }" :disabled="isLoading"
                title="Write a new summary" @click="loadSummary(true)">
          <RefreshCw :size="14" />
        </button>
      </div>
    </header>

    <div v-if="isLoading && !summary" class="state">
      <RefreshCw :size="22" class="spin" />
      <p>The local model is writing your summary. This can take a few seconds.</p>
    </div>

    <div v-else-if="errorMessage" class="state state-error">
      <AlertCircle :size="22" />
      <p>{{ errorMessage }}</p>
    </div>

    <div v-else-if="isEmpty" class="state">
      <Moon :size="22" />
      <p>No activity recorded on {{ selectedDay }}.</p>
      <span class="hint">The tracker only records while it runs: venv/bin/python -m backend.driver</span>
    </div>

    <div v-else-if="summary" class="content" :class="{ dimmed: isLoading }">
      <div class="headline-row">
        <h3 class="headline">{{ summary.headline }}</h3>
        <span class="badge" :class="summary.source === 'llm' ? 'badge-ai' : 'badge-basic'">
          {{ summary.source === 'llm' ? `AI · ${summary.model}` : 'Basic summary' }}
        </span>
        <span v-if="summary.is_partial" class="badge badge-basic">So far today</span>
      </div>
      <p v-if="summary.notice" class="notice">{{ summary.notice }}</p>

      <ul class="focus-list">
        <li v-for="area in summary.focus_areas" :key="area"><Target :size="13" />{{ area }}</li>
      </ul>

      <div class="text-block">
        <p>{{ summary.insight }}</p>
        <p class="suggestion"><Lightbulb :size="14" />{{ summary.suggestion }}</p>
      </div>

      <div v-if="categoryTotal > 0" class="category-bar" aria-label="Time by category">
        <span v-for="(minutes, name) in summary.category_minutes" :key="name" class="category-part"
              :style="{ flexGrow: minutes, background: CATEGORY_COLORS[name] ?? 'var(--text-muted)' }"
              :title="`${name}: ${formatMinutes(minutes)}`" />
      </div>
      <div v-if="categoryTotal > 0" class="category-legend">
        <span v-for="(minutes, name) in summary.category_minutes" :key="name">
          <i :style="{ background: CATEGORY_COLORS[name] ?? 'var(--text-muted)' }" />{{ name }} {{ formatMinutes(minutes) }}
        </span>
      </div>

      <div class="time-split">
        <div v-for="item in summary.time_split" :key="item.app_name" class="split-row">
          <span class="split-app">{{ item.app_name }}</span>
          <div class="split-track">
            <div class="split-fill" :style="{ width: `${(item.minutes / maxMinutes) * 100}%` }" />
          </div>
          <span class="split-minutes">{{ formatMinutes(item.minutes) }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.summary-card {
  padding: 20px 22px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-bottom: 12px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  color: var(--accent-indigo);
}

h2 {
  font-size: 1.05rem;
}

.subtitle {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.day-toggle {
  display: flex;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.day-toggle button, .icon-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.8rem;
  padding: 6px 12px;
  cursor: pointer;
}

.day-toggle button.active {
  background: var(--accent-indigo);
  color: #fff;
}

.day-picker {
  font: inherit;
  font-size: 0.8rem;
  padding: 5px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  color-scheme: dark;
}

.icon-btn {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  display: flex;
  padding: 7px;
}

.icon-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}

.spinning svg, .spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 28px 12px;
  color: var(--text-secondary);
  text-align: center;
}

.state-error {
  color: var(--accent-rose);
}

.hint {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}

.content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: opacity 0.2s;
}

.dimmed {
  opacity: 0.55;
}

.headline-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.headline {
  font-size: 1.15rem;
}

.badge {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border-subtle);
}

.badge-ai {
  color: var(--accent-indigo);
  border-color: var(--border-active);
}

.badge-basic {
  color: var(--text-muted);
}

.notice {
  font-size: 0.78rem;
  color: var(--accent-amber);
}

.focus-list {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.focus-list li {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
}

.text-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.suggestion {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  color: var(--text-primary);
}

.suggestion svg {
  margin-top: 3px;
  color: var(--accent-amber);
  flex-shrink: 0;
}

.category-bar {
  display: flex;
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  gap: 2px;
}

.category-part {
  min-width: 4px;
}

.category-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.category-legend i {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  margin-right: 6px;
}

.time-split {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.split-row {
  display: grid;
  grid-template-columns: 140px 1fr 70px;
  align-items: center;
  gap: 10px;
  font-size: 0.8rem;
}

.split-app {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}

.split-track {
  height: 6px;
  background: var(--bg-secondary);
  border-radius: 999px;
  overflow: hidden;
}

.split-fill {
  height: 100%;
  background: var(--accent-indigo);
  border-radius: 999px;
}

.split-minutes {
  text-align: right;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 0.75rem;
}
</style>
