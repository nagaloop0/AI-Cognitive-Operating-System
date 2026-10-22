<script setup lang="ts">
import { computed } from 'vue'
import { BarChart3, Keyboard, Mouse } from '@lucide/vue'
import type { AppSummary } from '@/types'

const props = defineProps<{
  apps: AppSummary[]
}>()

const maxDuration = computed(() => {
  if (!props.apps || props.apps.length === 0) return 1
  return Math.max(...props.apps.map(a => a.total_duration_seconds), 1)
})

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0s'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60

  if (hours > 0) return `${hours}h ${minutes}m`
  if (minutes > 0) return `${minutes}m ${remainingSeconds}s`
  return `${remainingSeconds}s`
}

function getAppColor(appName: string): string {
  const colors = [
    'linear-gradient(90deg, #6366f1, #3b82f6)',
    'linear-gradient(90deg, #06b6d4, #10b981)',
    'linear-gradient(90deg, #ec4899, #8b5cf6)',
    'linear-gradient(90deg, #f59e0b, #ef4444)',
    'linear-gradient(90deg, #10b981, #06b6d4)',
    'linear-gradient(90deg, #8b5cf6, #ec4899)'
  ]
  let hash = 0
  for (let i = 0; i < appName.length; i++) {
    hash = appName.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}
</script>

<template>
  <div class="app-chart-panel glass-panel">
    <div class="panel-header">
      <div>
        <h2>Application Time Distribution</h2>
        <p class="panel-subtitle">Ranked by total dwell time & input activity</p>
      </div>
      <span class="badge-counter">{{ apps.length }} Apps Recorded</span>
    </div>

    <div v-if="apps.length === 0" class="empty-state">
      <div class="empty-icon-bubble">
        <BarChart3 class="empty-svg" />
      </div>
      <p>No application activity recorded yet.</p>
      <small>Run <code>python -m backend.driver</code> to begin logging.</small>
    </div>

    <div v-else class="app-list">
      <div v-for="app in apps" :key="app.app_name" class="app-row">
        <div class="app-meta">
          <div class="app-identity">
            <span class="app-name">{{ app.app_name }}</span>
            <span class="session-tag">{{ app.session_count }} sessions</span>
          </div>
          <div class="app-stats">
            <span class="duration-text">{{ formatDuration(app.total_duration_seconds) }}</span>
            <span class="keys-text">
              <Keyboard class="micro-svg" />
              {{ app.total_keystrokes }}
            </span>
            <span class="clicks-text">
              <Mouse class="micro-svg" />
              {{ app.total_clicks }}
            </span>
          </div>
        </div>

        <div class="progress-track">
          <div 
            class="progress-fill" 
            :style="{ 
              width: `${(app.total_duration_seconds / maxDuration) * 100}%`,
              background: getAppColor(app.app_name)
            }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-chart-panel {
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

.badge-counter {
  font-size: 0.75rem;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.app-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.app-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.app-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.88rem;
}

.app-identity {
  display: flex;
  align-items: center;
  gap: 10px;
}

.app-name {
  font-weight: 600;
  color: var(--text-primary);
}

.session-tag {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-muted);
}

.app-stats {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 0.8rem;
}

.duration-text {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--text-primary);
}

.keys-text, .clicks-text {
  display: flex;
  align-items: center;
  color: var(--text-muted);
}

.progress-track {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 999px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.03);
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
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
