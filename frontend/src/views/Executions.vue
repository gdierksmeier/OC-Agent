<script setup>
import { ref, onMounted } from 'vue'
import { executionsApi, agentsApi } from '../api.js'

const executions = ref([])
const agentMap = ref({})
const loading = ref(true)
const error = ref(null)
const filterStatus = ref('')

const fmtCost = (v) => `$${(v || 0).toFixed(6)}`

async function load() {
  loading.value = true
  try {
    const params = { limit: 200 }
    if (filterStatus.value) params.status_filter = filterStatus.value
    const [es, agents] = await Promise.all([
      executionsApi.list(params),
      agentsApi.list(),
    ])
    executions.value = es
    agentMap.value = Object.fromEntries(agents.map(a => [a.id, a.name]))
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <div>
        <h2 class="section-title">Executions</h2>
        <p class="section-subtitle">Every agent run, with full traceability and per-step metrics.</p>
      </div>
      <div class="toolbar-filters">
        <select class="form-control" v-model="filterStatus" @change="load">
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="escalated">Escalated</option>
          <option value="running">Running</option>
        </select>
        <button class="btn" @click="load">Refresh</button>
      </div>
    </div>

    <div v-if="error" class="error-banner mb-4">{{ error }}</div>
    <div v-if="loading" class="loading">Loading…</div>

    <div v-else-if="!executions.length" class="card">
      <div class="empty-state">
        <h3>No executions yet</h3>
        <p>Open an agent and click "Run" to see traces here.</p>
      </div>
    </div>

    <div v-else class="card">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th><th>Agent</th><th>Status</th><th>Latency</th>
            <th>Tokens (in/out)</th><th>Cost</th><th>Started</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in executions" :key="e.id">
            <td>
              <router-link :to="`/executions/${e.id}`" class="text-mono">#{{ e.id }}</router-link>
            </td>
            <td>{{ agentMap[e.agent_id] || `#${e.agent_id}` }}</td>
            <td><span :class="`pill pill-${e.status}`">{{ e.status }}</span></td>
            <td>{{ e.total_latency_ms }} ms</td>
            <td class="text-mono text-sm">{{ e.total_tokens_input }} / {{ e.total_tokens_output }}</td>
            <td>{{ fmtCost(e.total_cost) }}</td>
            <td class="text-sm text-muted">{{ new Date(e.started_at).toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
