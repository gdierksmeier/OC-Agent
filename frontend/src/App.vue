<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import Sidebar from './components/Sidebar.vue'

const route = useRoute()
const pageTitle = computed(() => {
  const titles = {
    dashboard: 'Dashboard',
    agents: 'Agents',
    'agent-detail': 'Agent Details',
    workflows: 'Workflows',
    endpoints: 'Endpoint Registry',
    models: 'Model Registry',
    prompts: 'Prompt Library',
    executions: 'Executions',
    'execution-detail': 'Execution Trace',
    cost: 'Cost Validation',
  }
  return titles[route.name] || 'AI Agent Platform'
})
</script>

<template>
  <div class="app-layout">
    <Sidebar />
    <div class="main">
      <header class="topbar">
        <div class="topbar-title">{{ pageTitle }}</div>
        <div class="topbar-meta">AI Agent Generation &amp; Maintenance System · v0.1</div>
      </header>
      <div class="content">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </div>
    </div>
  </div>
</template>
