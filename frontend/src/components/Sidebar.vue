<script setup>
import { ref } from 'vue'
import AboutDialog from './AboutDialog.vue'

const aboutOpen = ref(false)

const sections = [
  {
    title: 'Overview',
    items: [
      { to: '/', label: 'Dashboard', icon: '◈' },
      { to: '/cost', label: 'Cost Validation', icon: '$' },
    ],
  },
  {
    title: 'Build',
    items: [
      { to: '/agents', label: 'Agents', icon: '◉' },
      { to: '/workflows', label: 'Workflows', icon: '⇶' },
      { to: '/prompts', label: 'Prompts', icon: '✎' },
    ],
  },
  {
    title: 'Configure',
    items: [
      { to: '/endpoints', label: 'Endpoints', icon: '⇆' },
      { to: '/models', label: 'AI Models', icon: '⊛' },
      { to: '/environment-settings', label: 'Environment Settings', icon: '⚙' },
    ],
  },
  {
    title: 'Operate',
    items: [
      { to: '/executions', label: 'Executions', icon: '▶' },
    ],
  },
]
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-brand">
      <div class="sidebar-brand-icon">A</div>
      <div class="sidebar-brand-name">Agent Factory</div>
      <button
        class="sidebar-brand-info"
        type="button"
        title="About this system"
        aria-label="About this system"
        @click="aboutOpen = true"
      >i</button>
    </div>
    <div v-for="s in sections" :key="s.title" class="sidebar-section">
      <div class="sidebar-section-title">{{ s.title }}</div>
      <router-link
        v-for="item in s.items"
        :key="item.to"
        :to="item.to"
        class="sidebar-link"
        active-class="is-active"
        :exact-active-class="item.to === '/' ? 'is-active' : ''"
      >
        <span class="sidebar-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </router-link>
    </div>
    <div class="sidebar-footer">
      Phase 1 Foundation Build
    </div>
    <AboutDialog :open="aboutOpen" @close="aboutOpen = false" />
  </aside>
</template>

<style scoped>
.sidebar-brand-name { flex: 1; }
.sidebar-brand-info {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(96, 165, 250, 0.15);
  border: 1px solid rgba(96, 165, 250, 0.4);
  color: #93c5fd;
  font-size: 12px;
  font-weight: 700;
  font-style: italic;
  font-family: Georgia, "Times New Roman", serif;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  padding: 0;
  transition: all 0.15s ease;
  flex-shrink: 0;
}
.sidebar-brand-info:hover {
  background: rgba(96, 165, 250, 0.3);
  border-color: #60a5fa;
  color: #ffffff;
  transform: scale(1.08);
}
.sidebar-brand-info:active { transform: scale(0.95); }
</style>
