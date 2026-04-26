<script setup>
import { ref, onMounted } from 'vue'
import { workflowsApi, agentsApi } from '../api.js'

const workflows = ref([])
const agentMap = ref({})
const loading = ref(true)
const error = ref(null)

async function load() {
  loading.value = true
  try {
    const [wfs, agents] = await Promise.all([workflowsApi.list(), agentsApi.list()])
    workflows.value = wfs
    agentMap.value = Object.fromEntries(agents.map(a => [a.id, a.name]))
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function remove(id) {
  if (!confirm('Delete this workflow?')) return
  await workflowsApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <div>
        <h2 class="section-title">Workflows</h2>
        <p class="section-subtitle">Each agent runs through an ordered sequence of tasks. Use <strong>Edit</strong> to open the agent’s Workflow tab and change name, status, and tasks.</p>
      </div>
    </div>

    <div v-if="error" class="error-banner mb-4">{{ error }}</div>
    <div v-if="loading" class="loading">Loading…</div>

    <div v-else-if="!workflows.length" class="card">
      <div class="empty-state">
        <h3>No workflows yet</h3>
        <p>Workflows are created when you set up an agent's task sequence.</p>
      </div>
    </div>

    <div v-else class="card">
      <table class="table">
        <thead>
          <tr>
            <th>Workflow</th><th>Agent</th><th>Tasks</th><th>Version</th>
            <th>Status</th><th>Updated</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="wf in workflows" :key="wf.id">
            <td>
              <strong>{{ wf.name }}</strong>
              <div class="text-sm text-muted">{{ wf.description || '—' }}</div>
            </td>
            <td>
              <router-link :to="`/agents/${wf.agent_id}`">
                {{ agentMap[wf.agent_id] || `#${wf.agent_id}` }}
              </router-link>
            </td>
            <td>{{ wf.tasks.length }} task{{ wf.tasks.length === 1 ? '' : 's' }}</td>
            <td>v{{ wf.version }}</td>
            <td><span :class="`pill pill-${wf.status}`">{{ wf.status }}</span></td>
            <td class="text-sm text-muted">{{ new Date(wf.updated_at).toLocaleDateString() }}</td>
            <td class="table-actions">
              <router-link
                class="btn btn-sm"
                :to="{ name: 'agent-detail', params: { id: wf.agent_id }, query: { tab: 'workflow' } }"
              >Edit</router-link>
              <button class="btn btn-sm btn-danger" @click="remove(wf.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
