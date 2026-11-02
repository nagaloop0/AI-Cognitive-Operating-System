<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Info } from '@lucide/vue'
import { loadDemoManifest, type DemoManifest } from '@/api'

const manifest = ref<DemoManifest | null>(null)

onMounted(async () => {
  manifest.value = await loadDemoManifest()
})
</script>

<template>
  <aside class="demo-banner" role="note">
    <Info :size="18" class="icon" />
    <div>
      <strong>Demo with fake data.</strong>
      This page is read-only and has no server or AI model behind it. Every number comes from invented activity
      for a fictional developer<span v-if="manifest"> ({{ manifest.days[0] }} to {{ manifest.latest_day }})</span>.
      The AI texts are stored samples, written by a local model on a Mac from that fake data; like any
      language model output, they can contain mistakes.
      <span v-if="manifest" class="note">{{ manifest.note }}</span>
    </div>
  </aside>
</template>

<style scoped>
.demo-banner {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px 18px;
  border-radius: var(--radius-md);
  border: 1px solid var(--accent-amber);
  background: rgba(245, 158, 11, 0.08);
  font-size: 0.88rem;
  color: var(--text-secondary);
}

.icon {
  color: var(--accent-amber);
  flex-shrink: 0;
  margin-top: 2px;
}

strong {
  color: var(--text-primary);
}

.note {
  display: block;
  margin-top: 4px;
  font-size: 0.8rem;
  color: var(--text-muted);
}
</style>
