<script setup lang="ts">
import { Clock, Keyboard, Mouse, AppWindow } from '@lucide/vue'
import type { OverallSummary } from '@/types'

defineProps<{
  summary: OverallSummary | null
}>()

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0s'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m ${remainingSeconds}s`
  }
  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`
  }
  return `${remainingSeconds}s`
}

function formatNumber(num: number): string {
  if (!num) return '0'
  return num.toLocaleString()
}
</script>

<template>
  <section class="summary-cards-grid">
    <!-- Card 1: Total Screen Time -->
    <div class="stat-card glass-panel duration-card">
      <div class="card-header">
        <span class="card-label">Screen Time</span>
        <div class="icon-bubble duration-bubble">
          <Clock class="card-svg" />
        </div>
      </div>
      <div class="card-value font-mono">
        {{ formatDuration(summary?.total_duration_seconds || 0) }}
      </div>
      <div class="card-footer">
        <span class="indicator-tag">Tracked Active Time</span>
      </div>
    </div>

    <!-- Card 2: Total Keystrokes -->
    <div class="stat-card glass-panel keystrokes-card">
      <div class="card-header">
        <span class="card-label">Total Keystrokes</span>
        <div class="icon-bubble keys-bubble">
          <Keyboard class="card-svg" />
        </div>
      </div>
      <div class="card-value font-mono">
        {{ formatNumber(summary?.total_keystrokes || 0) }}
      </div>
      <div class="card-footer">
        <span class="sub-metric">
          {{ summary && summary.total_duration_seconds > 0 
              ? Math.round((summary.total_keystrokes / (summary.total_duration_seconds / 60)) || 0) 
              : 0 }} keys / min
        </span>
      </div>
    </div>

    <!-- Card 3: Mouse Clicks -->
    <div class="stat-card glass-panel clicks-card">
      <div class="card-header">
        <span class="card-label">Mouse Clicks</span>
        <div class="icon-bubble clicks-bubble">
          <Mouse class="card-svg" />
        </div>
      </div>
      <div class="card-value font-mono">
        {{ formatNumber(summary?.total_clicks || 0) }}
      </div>
      <div class="card-footer">
        <span class="sub-metric">Interactive Click Events</span>
      </div>
    </div>

    <!-- Card 4: Sessions Recorded -->
    <div class="stat-card glass-panel sessions-card">
      <div class="card-header">
        <span class="card-label">Window Sessions</span>
        <div class="icon-bubble sessions-bubble">
          <AppWindow class="card-svg" />
        </div>
      </div>
      <div class="card-value font-mono">
        {{ formatNumber(summary?.total_sessions || 0) }}
      </div>
      <div class="card-footer">
        <span class="sub-metric">Distinct App Transitions</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.summary-cards-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

@media (max-width: 1080px) {
  .summary-cards-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .summary-cards-grid {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.card-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.icon-bubble {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
}

.card-svg {
  width: 18px;
  height: 18px;
}

.duration-bubble {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
  border-color: rgba(56, 189, 248, 0.2);
}

.keys-bubble {
  color: #a855f7;
  background: rgba(168, 85, 247, 0.1);
  border-color: rgba(168, 85, 247, 0.2);
}

.clicks-bubble {
  color: #34d399;
  background: rgba(52, 211, 153, 0.1);
  border-color: rgba(52, 211, 153, 0.2);
}

.sessions-bubble {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.2);
}

.card-value {
  font-size: 1.85rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin-bottom: 12px;
}

.font-mono {
  font-family: var(--font-mono);
}

.card-footer {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.indicator-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(56, 189, 248, 0.1);
  color: #38bdf8;
  font-size: 0.72rem;
  font-weight: 500;
}

.sub-metric {
  color: var(--text-muted);
}
</style>
