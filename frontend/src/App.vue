<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import type { DashboardData, OverallSummary, AppSummary, TimelineItem, HabitPatternItem, PredictionItem } from '@/types'
import HeaderNav from '@/components/HeaderNav.vue'
import SummaryCards from '@/components/SummaryCards.vue'
import AppChart from '@/components/AppChart.vue'
import TimelineFeed from '@/components/TimelineFeed.vue'
import PrivacyControls from '@/components/PrivacyControls.vue'
import PatternWidget from '@/components/PatternWidget.vue'

// Proxied via Vite config to http://127.0.0.1:8000
const API_BASE = '/api'

const isConnected = ref(false)
const lastUpdated = ref('')
const isPaused = ref(false)
const isBusy = ref(false)

const summary = ref<OverallSummary | null>(null)
const apps = ref<AppSummary[]>([])
const timeline = ref<TimelineItem[]>([])
const patterns = ref<HabitPatternItem[]>([])
const recentPredictions = ref<PredictionItem[]>([])

let pollTimer: number | null = null

// Bundled high-performance fetch
async function fetchDashboardData() {
  try {
    const res = await fetch(`${API_BASE}/stats/dashboard?limit=15`)
    if (!res.ok) {
      throw new Error(`API error: ${res.status}`)
    }

    const data: DashboardData = await res.json()
    summary.value = data.summary
    apps.value = data.apps
    timeline.value = data.timeline
    isPaused.value = data.preference.is_tracking_paused
    patterns.value = data.patterns || []
    recentPredictions.value = data.recent_predictions || []

    isConnected.value = true
    lastUpdated.value = new Date().toLocaleTimeString()
  } catch {
    isConnected.value = false
  }
}

async function handleTogglePause() {
  if (isBusy.value) return
  isBusy.value = true
  try {
    const res = await fetch(`${API_BASE}/control/toggle`, { method: 'POST' })
    if (res.ok) {
      const data = await res.json()
      isPaused.value = data.is_tracking_paused
    }
  } catch (err) {
    console.error('Failed to toggle tracking', err)
  } finally {
    isBusy.value = false
  }
}

async function handleClearHistory() {
  if (isBusy.value) return
  isBusy.value = true
  try {
    const res = await fetch(`${API_BASE}/control/clear-history`, { method: 'POST' })
    if (res.ok) {
      await fetchDashboardData()
    }
  } catch (err) {
    console.error('Failed to clear history', err)
  } finally {
    isBusy.value = false
  }
}

// Power-saving visibility listener: Stop polling when laptop is asleep or tab is hidden
function handleVisibilityChange() {
  if (document.hidden) {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  } else {
    // Immediately fetch fresh data when returning to tab, then resume 5s timer
    fetchDashboardData()
    if (!pollTimer) {
      pollTimer = window.setInterval(fetchDashboardData, 5000)
    }
  }
}

onMounted(() => {
  fetchDashboardData()
  pollTimer = window.setInterval(fetchDashboardData, 5000)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div class="app-container">
    <!-- Top Navigation & Connection Status -->
    <HeaderNav 
      :is-connected="isConnected" 
      :last-updated="lastUpdated" 
    />

    <!-- Privacy & Remote Control Action Bar -->
    <PrivacyControls 
      :is-paused="isPaused" 
      :is-busy="isBusy"
      @toggle-pause="handleTogglePause"
      @clear-history="handleClearHistory"
    />

    <!-- Top KPI Summary Cards -->
    <SummaryCards :summary="summary" />

    <!-- Main Visual Split Grid -->
    <main class="dashboard-grid">
      <AppChart :apps="apps" />
      <TimelineFeed :timeline="timeline" />
    </main>

    <!-- Hour 6 Proactive Pattern Intelligence Widget -->
    <PatternWidget 
      :patterns="patterns" 
      :recent-predictions="recentPredictions"
      @retrain="fetchDashboardData"
    />
  </div>
</template>

<style scoped>
/* Scoped overrides if needed */
</style>
