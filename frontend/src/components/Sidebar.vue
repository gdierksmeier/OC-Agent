<script setup>
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
      <div>Agent Factory</div>
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
  </aside>
</template>
