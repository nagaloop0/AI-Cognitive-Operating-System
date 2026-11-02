<script setup lang="ts">
import { ref } from 'vue'
import { Search, Loader2, AlertCircle, History } from '@lucide/vue'
import type { AskAnswer } from '@/types'

const EXAMPLES = ['What did I work on yesterday?', 'When did I work on the dashboard?', 'How was my focus on Monday?']

const question = ref('')
const result = ref<AskAnswer | null>(null)
const isLoading = ref(false)
const errorMessage = ref('')

async function ask(text?: string) {
  const q = (text ?? question.value).trim()
  if (q.length < 3 || isLoading.value) return
  question.value = q
  isLoading.value = true
  errorMessage.value = ''
  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q }),
    })
    if (res.status === 503) throw new Error('The local AI is not running. Start it with: brew services start ollama')
    if (!res.ok) throw new Error(`API error ${res.status}`)
    result.value = (await res.json()) as AskAnswer
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Something went wrong.'
  } finally {
    isLoading.value = false
  }
}

function formatSeconds(seconds: number): string {
  if (seconds < 60) return `${seconds} s`
  const minutes = Math.round(seconds / 60)
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h && m) return `${h} h ${m} min`
  return h ? `${h} h` : `${m} min`
}
</script>

<template>
  <section class="glass-panel ask-card">
    <header class="card-header">
      <History :size="18" class="title-icon" />
      <h2>Ask your history</h2>
      <span class="subtitle">Answers come only from your own activity, on this Mac.</span>
    </header>

    <form class="ask-form" @submit.prevent="ask()">
      <input v-model="question" type="text" maxlength="300" placeholder="What did I work on yesterday?"
             aria-label="Question about your history" />
      <button type="submit" :disabled="isLoading || question.trim().length < 3">
        <Loader2 v-if="isLoading" :size="15" class="spin" />
        <Search v-else :size="15" />
        Ask
      </button>
    </form>

    <div v-if="!result && !errorMessage" class="examples">
      <button v-for="example in EXAMPLES" :key="example" @click="ask(example)">{{ example }}</button>
    </div>

    <p v-if="errorMessage" class="error"><AlertCircle :size="15" />{{ errorMessage }}</p>

    <div v-if="result" class="answer" :class="{ dimmed: isLoading }">
      <p>{{ result.answer }}</p>
      <details v-if="result.sources.length">
        <summary>Based on {{ result.sources.length }} window title(s)</summary>
        <ul>
          <li v-for="source in result.sources" :key="`${source.day}-${source.app_name}-${source.window_title}`">
            <span class="day">{{ source.day }}</span>
            <span class="title">{{ source.app_name }} · {{ source.window_title }}</span>
            <span class="time">{{ formatSeconds(source.seconds) }}</span>
          </li>
        </ul>
      </details>
    </div>
  </section>
</template>

<style scoped>
.ask-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.title-icon {
  color: var(--accent-emerald);
}

h2 {
  font-size: 1.05rem;
}

.subtitle {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.ask-form {
  display: flex;
  gap: 8px;
}

input {
  flex: 1;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font: inherit;
  font-size: 0.88rem;
}

input:focus {
  outline: none;
  border-color: var(--accent-emerald);
}

.ask-form button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 14px;
  border: none;
  cursor: pointer;
  border-radius: var(--radius-sm);
  background: var(--accent-emerald);
  color: #fff;
  font: inherit;
  font-size: 0.85rem;
}

.ask-form button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.examples button {
  font: inherit;
  font-size: 0.78rem;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}

.examples button:hover {
  border-color: var(--accent-emerald);
  color: var(--accent-emerald);
}

.error {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 0.85rem;
  color: var(--accent-rose);
}

.answer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.9rem;
  transition: opacity 0.2s;
}

.dimmed {
  opacity: 0.55;
}

details summary {
  cursor: pointer;
  font-size: 0.78rem;
  color: var(--text-muted);
}

details ul {
  list-style: none;
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

details li {
  display: grid;
  grid-template-columns: 90px 1fr 60px;
  gap: 8px;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.time {
  text-align: right;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
