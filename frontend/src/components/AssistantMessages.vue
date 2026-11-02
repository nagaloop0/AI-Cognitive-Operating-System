<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { MessageCircle, Check, Coffee, Sunset, Bell, Mail } from '@lucide/vue'
import type { AssistantMessage } from '@/types'

const messages = ref<AssistantMessage[]>([])
let timer: number | null = null

const ICONS: Record<AssistantMessage['kind'], typeof Bell> = {
  welcome_back: Coffee,
  end_of_day: Sunset,
  nudge: Bell,
  unread: Mail,
}

async function loadMessages() {
  try {
    const res = await fetch('/api/assistant/messages?limit=10')
    if (res.ok) messages.value = (await res.json()) as AssistantMessage[]
  } catch (err) {
    console.error('Failed to load assistant messages', err)
  }
}

async function markRead(message: AssistantMessage) {
  const res = await fetch(`/api/assistant/messages/${message.id}/read`, { method: 'POST' })
  if (res.ok) message.is_read = true
}

function timeLabel(iso: string): string {
  const d = new Date(iso)
  const sameDay = d.toDateString() === new Date().toDateString()
  return sameDay
    ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  loadMessages()
  timer = window.setInterval(loadMessages, 15000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <section class="glass-panel messages-card">
    <header class="card-header">
      <MessageCircle :size="18" class="title-icon" />
      <h2>Assistant</h2>
      <span class="count">{{ messages.filter((m) => !m.is_read).length }} new</span>
    </header>

    <p v-if="messages.length === 0" class="empty">
      No messages yet. After a long break you get a "welcome back", and in the evening your day summary.
    </p>

    <ul v-else class="list">
      <li v-for="message in messages" :key="message.id" :class="{ read: message.is_read }">
        <component :is="ICONS[message.kind]" :size="16" class="kind-icon" />
        <div class="body">
          <div class="row">
            <strong>{{ message.title }}</strong>
            <span class="time">{{ timeLabel(message.created_at) }}</span>
          </div>
          <p>{{ message.body }}</p>
        </div>
        <button v-if="!message.is_read" class="read-btn" title="Mark as read" @click="markRead(message)">
          <Check :size="14" />
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.messages-card {
  padding: 18px 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.title-icon {
  color: var(--accent-cyan);
}

h2 {
  font-size: 1.05rem;
}

.count {
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.empty {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 320px;
  overflow-y: auto;
}

li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px;
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
}

li.read {
  opacity: 0.55;
}

.kind-icon {
  color: var(--accent-cyan);
  margin-top: 2px;
  flex-shrink: 0;
}

.body {
  flex: 1;
  min-width: 0;
}

.row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.85rem;
}

.time {
  font-size: 0.72rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.body p {
  font-size: 0.82rem;
  color: var(--text-secondary);
  white-space: pre-line;
  margin-top: 2px;
}

.read-btn {
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 4px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
}

.read-btn:hover {
  color: var(--accent-emerald);
  border-color: var(--accent-emerald);
}
</style>
