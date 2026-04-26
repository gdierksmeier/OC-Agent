import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ---------- Agents ----------
export const agentsApi = {
  list: (params = {}) => api.get('/agents', { params }).then(r => r.data),
  get: (id) => api.get(`/agents/${id}`).then(r => r.data),
  create: (data) => api.post('/agents', data).then(r => r.data),
  update: (id, data) => api.patch(`/agents/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/agents/${id}`),
  clone: (id) => api.post(`/agents/${id}/clone`).then(r => r.data),
  snapshot: (id, changelog) => api.post(`/agents/${id}/snapshot`, null, { params: { changelog } }).then(r => r.data),
  versions: (id) => api.get(`/agents/${id}/versions`).then(r => r.data),
  transition: (id, new_status) => api.post(`/agents/${id}/transition`, null, { params: { new_status } }).then(r => r.data),
}

// ---------- Workflows ----------
export const workflowsApi = {
  list: (params = {}) => api.get('/workflows', { params }).then(r => r.data),
  get: (id) => api.get(`/workflows/${id}`).then(r => r.data),
  create: (data) => api.post('/workflows', data).then(r => r.data),
  update: (id, data) => api.patch(`/workflows/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/workflows/${id}`),
  addTask: (id, task) => api.post(`/workflows/${id}/tasks`, task).then(r => r.data),
  removeTask: (id, taskId) => api.delete(`/workflows/${id}/tasks/${taskId}`),
}

// ---------- Endpoints ----------
export const endpointsApi = {
  list: (params = {}) => api.get('/endpoints', { params }).then(r => r.data),
  get: (id) => api.get(`/endpoints/${id}`).then(r => r.data),
  create: (data) => api.post('/endpoints', data).then(r => r.data),
  update: (id, data) => api.patch(`/endpoints/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/endpoints/${id}`),
  test: (id, data) => api.post(`/endpoints/${id}/test`, data).then(r => r.data),
}

// ---------- Models ----------
export const modelsApi = {
  list: (params = {}) => api.get('/models', { params }).then(r => r.data),
  get: (id) => api.get(`/models/${id}`).then(r => r.data),
  create: (data) => api.post('/models', data).then(r => r.data),
  update: (id, data) => api.patch(`/models/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/models/${id}`),
}

// ---------- Prompts ----------
export const promptsApi = {
  list: (params = {}) => api.get('/prompts', { params }).then(r => r.data),
  get: (id) => api.get(`/prompts/${id}`).then(r => r.data),
  create: (data) => api.post('/prompts', data).then(r => r.data),
  update: (id, data) => api.patch(`/prompts/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/prompts/${id}`),
}

// ---------- Executions ----------
export const executionsApi = {
  list: (params = {}) => api.get('/executions', { params }).then(r => r.data),
  get: (id) => api.get(`/executions/${id}`).then(r => r.data),
  run: (agentId, payload) => api.post(`/executions/run/${agentId}`, payload).then(r => r.data),
}

// ---------- Dashboard ----------
export const dashboardApi = {
  kpis: (days = 30) => api.get('/dashboard/kpis', { params: { days } }).then(r => r.data),
  costSummary: (days = 30) => api.get('/dashboard/cost-summary', { params: { days } }).then(r => r.data),
  budgets: () => api.get('/dashboard/budgets').then(r => r.data),
  createBudget: (data) => api.post('/dashboard/budgets', data).then(r => r.data),
}

// ---------- Environment Settings ----------
export const environmentSettingsApi = {
  list: (params = {}) => api.get('/environment-settings', { params }).then(r => r.data),
  get: (id) => api.get(`/environment-settings/${id}`).then(r => r.data),
  create: (data) => api.post('/environment-settings', data).then(r => r.data),
  update: (id, data) => api.patch(`/environment-settings/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/environment-settings/${id}`),
}

export default api
