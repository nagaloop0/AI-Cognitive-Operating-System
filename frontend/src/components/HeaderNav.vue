<script setup lang="ts">
import { ref } from 'vue'
import { Sun, Moon, Clock } from '@lucide/vue'

defineProps<{
  isConnected: boolean
  lastUpdated: string
}>()

const isDark = ref(true)

function toggleTheme() {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.body.classList.remove('light-theme')
  } else {
    document.body.classList.add('light-theme')
  }
}
</script>

<template>
  <header class="header-nav glass-panel">
    <div class="brand">
      <div class="logo-orb">
        <div class="inner-core"></div>
      </div>
      <div>
        <div class="title-row">
          <h1>AI Cognitive OS</h1>
          <span class="version-tag">Phase 1</span>
        </div>
        <p class="subtitle">Real-time Behavioral Telemetry & Application Intelligence</p>
      </div>
    </div>

    <div class="status-actions">
      <!-- Light / Dark Theme Switcher -->
      <button 
        class="theme-toggle-btn" 
        :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
        @click="toggleTheme"
      >
        <Sun v-if="isDark" class="theme-icon" />
        <Moon v-else class="theme-icon" />
      </button>

      <!-- Connection Status Badge -->
      <div class="connection-badge" :class="{ online: isConnected, offline: !isConnected }">
        <span class="status-dot"></span>
        <span class="status-label">{{ isConnected ? 'API Connected' : 'API Offline' }}</span>
      </div>

      <!-- Sync Clock -->
      <div class="timestamp-badge">
        <Clock class="clock-svg" />
        <span>{{ lastUpdated || 'Syncing...' }}</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header-nav {
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo-orb {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #4f46e5, #06b6d4);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.4);
}

.inner-core {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  background: #ffffff;
  transform: rotate(45deg);
  opacity: 0.9;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

h1 {
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  background: linear-gradient(to right, var(--text-primary), var(--text-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.version-tag {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.35);
  color: var(--accent-indigo);
}

.subtitle {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.status-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.theme-toggle-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 7px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.theme-toggle-btn:hover {
  color: var(--text-primary);
  border-color: var(--border-accent);
}

.theme-icon {
  width: 17px;
  height: 17px;
}

.connection-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.connection-badge.online {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #10b981;
}

.connection-badge.offline {
  background: rgba(244, 63, 94, 0.12);
  border: 1px solid rgba(244, 63, 94, 0.3);
  color: #fb7185;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 8px currentColor;
  animation: pulseGlow 2s infinite ease-in-out;
}

.timestamp-badge {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.03);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  gap: 7px;
}

.clock-svg {
  width: 13px;
  height: 13px;
}
</style>
