<script setup lang="ts">
import { AppWindow, Keyboard, Mouse } from '@lucide/vue'
import type { TimelineItem } from '@/types'

defineProps<{
  timeline: TimelineItem[]
}>()

function formatTime(isoString: string): string {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return isoString
  }
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '< 1s'
  if (seconds >= 60) {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}m ${s}s`
  }
  return `${seconds}s`
}
</script>

<template>
  <div class="timeline-panel glass-panel">
    <div class="panel-header">
      <div>
        <h2>Active Window Stream</h2>
        <p class="panel-subtitle">Live chronological transitions and window titles</p>
      </div>
      <span class="live-indicator">
        <span class="pulse-dot"></span>
        Live Feed
      </span>
    </div>

    <div v-if="timeline.length === 0" class="empty-state">
      <div class="empty-icon-bubble">
        <AppWindow class="empty-svg" />
      </div>
      <p>No window transitions logged yet.</p>
    </div>

    <div v-else class="feed-scroll">
      <div v-for="item in timeline" :key="item.id" class="feed-item">
        <div class="item-time font-mono">
          {{ formatTime(item.start_time) }}
        </div>
        <div class="item-connector">
          <div class="node-dot"></div>
          <div class="line"></div>
        </div>
        <div class="item-content">
          <div class="content-header">
            <span class="app-badge">{{ item.app_name }}</span>
            <span class="duration-badge font-mono">{{ formatDuration(item.duration_seconds) }}</span>
          </div>
          <div class="window-title" :title="item.window_title || 'Untitled Window'">
            {{ item.window_title || 'Untitled Window' }}
          </div>
          <div class="content-footer">
            <span class="metric-pill">
              <Keyboard class="micro-svg" />
              {{ item.keystroke_count }} keys
            </span>
            <span class="metric-pill">
              <Mouse class="micro-svg" />
              {{ item.mouse_click_count }} clicks
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-panel {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

h2 {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.panel-subtitle {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.live-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #38bdf8;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.25);
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #38bdf8;
  animation: pulseGlow 1.5s infinite ease-in-out;
}

.feed-scroll {
  display: flex;
  flex-direction: column;
  max-height: 480px;
  overflow-y: auto;
  padding-right: 8px;
}

.feed-item {
  display: flex;
  gap: 14px;
  position: relative;
}

.item-time {
  font-size: 0.72rem;
  color: var(--text-muted);
  width: 65px;
  padding-top: 3px;
  text-align: right;
  flex-shrink: 0;
}

.font-mono {
  font-family: var(--font-mono);
}

.item-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 14px;
  flex-shrink: 0;
}

.node-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #6366f1;
  border: 2px solid var(--bg-primary);
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.6);
  z-index: 1;
}

.line {
  flex-grow: 1;
  width: 2px;
  background: rgba(255, 255, 255, 0.08);
  margin: 4px 0;
}

.item-content {
  flex-grow: 1;
  padding-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.app-badge {
  font-size: 0.8rem;
  font-weight: 600;
  color: #c7d2fe;
  background: rgba(99, 102, 241, 0.12);
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.duration-badge {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.window-title {
  font-size: 0.85rem;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 420px;
}

.content-footer {
  display: flex;
  gap: 12px;
}

.metric-pill {
  display: flex;
  align-items: center;
  font-size: 0.72rem;
  color: var(--text-muted);
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

.empty-icon-bubble {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  color: var(--text-muted);
}

.empty-svg {
  width: 24px;
  height: 24px;
}

.micro-svg {
  width: 13px;
  height: 13px;
  margin-right: 4px;
  opacity: 0.75;
}
</style>
