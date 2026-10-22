<script setup lang="ts">
import { ref } from 'vue'
import { Shield, AlertTriangle } from '@lucide/vue'

defineProps<{
  isPaused: boolean
  isBusy: boolean
}>()

const emit = defineEmits<{
  (e: 'togglePause'): void
  (e: 'clearHistory'): void
}>()

const showClearConfirm = ref(false)

function onClearClick() {
  showClearConfirm.value = true
}

function confirmClear() {
  showClearConfirm.value = false
  emit('clearHistory')
}

function cancelClear() {
  showClearConfirm.value = false
}
</script>

<template>
  <div class="privacy-panel glass-panel">
    <div class="panel-main">
      <div class="privacy-info">
        <div class="privacy-header">
          <div class="shield-bubble">
            <Shield class="shield-svg" />
          </div>
          <div>
            <h3>Privacy & Remote Controls</h3>
            <p>100% Local Storage in PostgreSQL. Zero content or character keystrokes are ever captured.</p>
          </div>
        </div>
      </div>

      <div class="action-buttons">
        <!-- Toggle Pause / Resume Button -->
        <button 
          class="btn-toggle" 
          :class="{ 'btn-paused': isPaused, 'btn-active': !isPaused }"
          :disabled="isBusy"
          @click="emit('togglePause')"
        >
          <span class="btn-dot"></span>
          <span>{{ isPaused ? 'Resume Tracking' : 'Pause Tracking' }}</span>
        </button>

        <!-- Clear History Button -->
        <button 
          class="btn-danger" 
          :disabled="isBusy"
          @click="onClearClick"
        >
          <span>Wipe History</span>
        </button>
      </div>
    </div>

    <!-- Confirmation Modal Overlay -->
    <div v-if="showClearConfirm" class="modal-backdrop">
      <div class="modal-card glass-panel">
        <div class="modal-icon-bubble">
          <AlertTriangle class="alert-svg" />
        </div>
        <h4>Clear Activity History?</h4>
        <p>This will permanently delete all logged application sessions, keystroke counts, and durations from PostgreSQL.</p>
        <div class="modal-actions">
          <button class="btn-ghost" @click="cancelClear">Cancel</button>
          <button class="btn-danger-solid" @click="confirmClear">Confirm Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.privacy-panel {
  padding: 20px 24px;
}

.panel-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.privacy-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.shield-bubble {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #10b981;
}

.shield-svg {
  width: 20px;
  height: 20px;
}

h3 {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 2px;
}

p {
  font-size: 0.8rem;
  color: var(--text-secondary);
  max-width: 580px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

button {
  cursor: pointer;
  font-family: var(--font-sans);
  font-weight: 600;
  border-radius: var(--radius-sm);
  padding: 10px 18px;
  font-size: 0.82rem;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-toggle {
  border: 1px solid transparent;
}

.btn-toggle.btn-active {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.4);
  color: #10b981;
}

.btn-toggle.btn-active:hover {
  background: rgba(16, 185, 129, 0.25);
}

.btn-toggle.btn-paused {
  background: rgba(245, 158, 11, 0.15);
  border-color: rgba(245, 158, 11, 0.4);
  color: #fbbf24;
}

.btn-toggle.btn-paused:hover {
  background: rgba(245, 158, 11, 0.25);
}

.btn-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.btn-danger {
  background: rgba(244, 63, 94, 0.1);
  border: 1px solid rgba(244, 63, 94, 0.3);
  color: #fb7185;
}

.btn-danger:hover {
  background: rgba(244, 63, 94, 0.2);
}

/* Confirmation Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.modal-card {
  width: 90%;
  max-width: 440px;
  padding: 28px;
  text-align: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
}

.modal-icon-bubble {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  color: #f59e0b;
}

.alert-svg {
  width: 26px;
  height: 26px;
}

.modal-card h4 {
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.modal-card p {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-ghost {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.15);
}

.btn-danger-solid {
  background: #e11d48;
  border: 1px solid #e11d48;
  color: #ffffff;
}

.btn-danger-solid:hover {
  background: #be123c;
}
</style>
