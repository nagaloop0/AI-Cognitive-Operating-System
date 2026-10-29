<script setup lang="ts">
import { ref } from 'vue'
import { Sparkles, ArrowRight, RefreshCw, CheckCircle2, Clock, Zap, HelpCircle } from '@lucide/vue'
import type { HabitPatternItem, PredictionItem } from '@/types'

const props = defineProps<{
  patterns?: HabitPatternItem[]
  recentPredictions?: PredictionItem[]
}>()

const emit = defineEmits<{
  (e: 'retrain'): void
}>()

const isRetraining = ref(false)

async function handleRetrain() {
  if (isRetraining.value) return
  isRetraining.value = true
  try {
    const res = await fetch('/api/patterns/retrain', { method: 'POST' })
    if (res.ok) {
      emit('retrain')
    }
  } catch (err) {
    console.error('Failed to retrain patterns:', err)
  } finally {
    setTimeout(() => {
      isRetraining.value = false
    }, 600)
  }
}

function getConfidenceClass(confidence: number): string {
  if (confidence >= 0.75) return 'conf-high'
  if (confidence >= 0.5) return 'conf-med'
  return 'conf-low'
}

function formatTime(isoStr: string): string {
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return isoStr
  }
}
</script>

<template>
  <div class="panel pattern-panel">
    <div class="panel-header">
      <div class="title-group">
        <Sparkles class="panel-icon icon-sparkle" :size="20" />
        <div>
          <h2>Workflow Intelligence & Next-App Predictions</h2>
          <p class="panel-subtitle">Discrete Markov Chain transition probabilities and real-time suggestion feedback</p>
        </div>
      </div>
      <button 
        class="retrain-btn" 
        :class="{ 'btn-spinning': isRetraining }"
        :disabled="isRetraining"
        @click="handleRetrain"
        title="Re-analyze telemetry transitions and update Markov probabilities"
      >
        <RefreshCw :size="14" />
        <span>{{ isRetraining ? 'Analyzing...' : 'Retrain Patterns' }}</span>
      </button>
    </div>

    <div class="pattern-content-grid">
      <!-- Section 1: Learned Habit Patterns -->
      <div class="sub-column">
        <div class="sub-column-title">
          <Zap :size="15" />
          <span>Learned Habit Sequences</span>
          <span class="count-badge">{{ props.patterns?.length || 0 }}</span>
        </div>

        <div v-if="!props.patterns || props.patterns.length === 0" class="empty-state">
          <HelpCircle :size="24" class="empty-icon" />
          <p>No repetitive workflows detected yet.</p>
          <span class="empty-hint">Switch between applications as you work — after 2+ switches, transitions will emerge here.</span>
        </div>

        <div v-else class="patterns-list">
          <div 
            v-for="pattern in props.patterns" 
            :key="pattern.id" 
            class="pattern-item"
          >
            <div class="pattern-flow">
              <span class="app-chip src-chip">{{ pattern.trigger_sequence }}</span>
              <ArrowRight :size="14" class="flow-arrow" />
              <span class="app-chip dst-chip">{{ pattern.predicted_action }}</span>
            </div>

            <div class="pattern-meta">
              <div class="confidence-bar-container">
                <div 
                  class="confidence-bar-fill" 
                  :class="getConfidenceClass(pattern.confidence)"
                  :style="{ width: `${Math.round(pattern.confidence * 100)}%` }"
                ></div>
              </div>
              <div class="meta-labels">
                <span class="conf-badge" :class="getConfidenceClass(pattern.confidence)">
                  {{ Math.round(pattern.confidence * 100) }}% confidence
                </span>
                <span class="count-label">{{ pattern.occurrence_count }}x observed</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Section 2: Real-time Predictions & Feedback Loop -->
      <div class="sub-column">
        <div class="sub-column-title">
          <Clock :size="15" />
          <span>Recent Proactive Suggestions</span>
          <span class="count-badge">{{ props.recentPredictions?.length || 0 }}</span>
        </div>

        <div v-if="!props.recentPredictions || props.recentPredictions.length === 0" class="empty-state">
          <Sparkles :size="24" class="empty-icon" />
          <p>No notifications triggered yet.</p>
          <span class="empty-hint">Desktop slide-ins trigger automatically when confidence &ge; 50% on app switch.</span>
        </div>

        <div v-else class="predictions-list">
          <div 
            v-for="pred in props.recentPredictions" 
            :key="pred.id" 
            class="prediction-item"
          >
            <div class="pred-header">
              <div class="pred-text">
                Suggested <span class="highlight">{{ pred.suggested_action }}</span> after {{ pred.trigger_sequence }}
              </div>
              <span 
                class="status-pill"
                :class="`status-${pred.status}`"
              >
                <CheckCircle2 v-if="pred.status === 'accepted'" :size="12" />
                <span>{{ pred.status }}</span>
              </span>
            </div>
            <div class="pred-time">{{ formatTime(pred.timestamp) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pattern-panel {
  margin-top: 1.5rem;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-color);
}

.title-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.icon-sparkle {
  color: #818cf8;
}

.panel-subtitle {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 0.2rem;
}

.retrain-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.8rem;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-main);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.retrain-btn:hover:not(:disabled) {
  border-color: #818cf8;
  color: #818cf8;
}

.btn-spinning svg {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.pattern-content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  align-items: start;
}

@media (max-width: 900px) {
  .pattern-content-grid {
    grid-template-columns: 1fr;
  }
}

.sub-column {
  display: flex;
  flex-direction: column;
}

.sub-column-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.count-badge {
  background: var(--badge-bg);
  color: var(--text-muted);
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  text-align: center;
  background: var(--empty-bg, rgba(255, 255, 255, 0.02));
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  color: var(--text-muted);
}

.empty-icon {
  margin-bottom: 0.5rem;
  opacity: 0.5;
}

.empty-hint {
  font-size: 0.75rem;
  opacity: 0.7;
  margin-top: 0.25rem;
}

.patterns-list, .predictions-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.pattern-item {
  background: var(--row-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.pattern-flow {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.app-chip {
  padding: 0.2rem 0.55rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
}

.src-chip {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.dst-chip {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.flow-arrow {
  color: var(--text-muted);
}

.pattern-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.confidence-bar-container {
  height: 4px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
  overflow: hidden;
}

.confidence-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.meta-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  margin-top: 0.2rem;
}

.conf-high {
  background: #10b981;
  color: #6ee7b7;
}

.conf-med {
  background: #6366f1;
  color: #a5b4fc;
}

.conf-low {
  background: #f59e0b;
  color: #fcd34d;
}

.conf-badge {
  padding: 0.05rem 0.4rem;
  border-radius: 4px;
  background: transparent;
  font-weight: 600;
}

.count-label {
  color: var(--text-muted);
}

.prediction-item {
  background: var(--row-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0.65rem 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.pred-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.pred-text {
  font-size: 0.8rem;
  color: var(--text-main);
}

.highlight {
  font-weight: 600;
  color: #38bdf8;
}

.pred-time {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: capitalize;
}

.status-accepted {
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-suggested {
  background: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
  animation: pulse 2s infinite;
}

.status-ignored {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
</style>
