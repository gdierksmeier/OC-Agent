import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/agents', name: 'agents', component: () => import('./views/AgentsList.vue') },
  { path: '/agents/:id', name: 'agent-detail', component: () => import('./views/AgentDetail.vue'), props: true },
  { path: '/workflows', name: 'workflows', component: () => import('./views/Workflows.vue') },
  { path: '/endpoints', name: 'endpoints', component: () => import('./views/Endpoints.vue') },
  { path: '/models', name: 'models', component: () => import('./views/Models.vue') },
  { path: '/prompts', name: 'prompts', component: () => import('./views/Prompts.vue') },
  { path: '/environment-settings', name: 'environment-settings', component: () => import('./views/EnvironmentSettings.vue') },
  { path: '/executions', name: 'executions', component: () => import('./views/Executions.vue') },
  { path: '/executions/:id', name: 'execution-detail', component: () => import('./views/ExecutionDetail.vue'), props: true },
  { path: '/cost', name: 'cost', component: () => import('./views/CostDashboard.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
