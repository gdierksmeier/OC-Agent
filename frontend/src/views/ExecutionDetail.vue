<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { executionsApi } from '../api.js'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()

const exec = ref(null)
const loading = ref(true)
const error = ref(null)

const fmtCost = (v) => `$${(v || 0).toFixed(6)}`

async function load() {
  loading.value = true
  try {
    exec.value = await executionsApi.get(props.id)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="loading">Loading trace…</div>
  <div v-else-if="error" class="error-banner">{{ error }}</div>

  <div v-else-if="exec">
    <div class="toolbar">
      <div>
        <h2 class="section-title">Execution #{{ exec.id }}</h2>
        <p class="section-subtitle text-mono text-sm">{{ exec.correlation_id }}</p>
      </div>
      <div class="toolbar-filters">
        <button class="btn" @click="router.push('/executions')">← Back</button>
      </div>
    </div>

    <!-- Summary tiles -->
    <div class="grid grid-4 mb-4">
      <div class="kpi">
        <div class="kpi-label">Status</div>
        <div class="kpi-value" style="font-size:18px">
          <span :class="`pill pill-${exec.status}`">{{ exec.status }}</span>
        </div>
        <div v-if="exec.escalated" class="kpi-sub">Escalated to human review</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Latency</div>
        <div class="kpi-value">{{ exec.total_latency_ms }} ms</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Cost</div>
        <div class="kpi-value">{{ fmtCost(exec.total_cost) }}</div>
        <div class="kpi-sub">est. {{ fmtCost(exec.estimated_cost) }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Tokens (in/out)</div>
        <div class="kpi-value" style="font-size:18px">
          {{ exec.total_tokens_input }} / {{ exec.total_tokens_output }}
        </div>
      </div>
    </div>

    <div v-if="exec.error_message" class="error-banner mb-4">
      <strong>Error:</strong> {{ exec.error_message }}
    </div>

    <!-- Input / output -->
    <div class="grid grid-2 mb-4">
      <div class="card">
        <div class="card-header"><div class="card-title">Input</div></div>
        <div class="card-body">
          <div class="json-view">{{ JSON.stringify(exec.input_data, null, 2) }}</div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Output</div></div>
        <div class="card-body">
          <div class="json-view">{{ JSON.stringify(exec.output_data, null, 2) }}</div>
        </div>
      </div>
    </div>

    <!-- Steps -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">Step-by-step trace ({{ exec.steps?.length || 0 }})</div>
      </div>
      <div v-if="!exec.steps?.length" class="empty-state">No steps recorded.</div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>#</th><th>Step</th><th>Type</th><th>Status</th>
            <th>Latency</th><th>Tokens</th><th>Cost</th><th>Output preview</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(s, i) in exec.steps" :key="s.id">
            <td>{{ i + 1 }}</td>
            <td><strong>{{ s.step_name }}</strong></td>
            <td><span class="text-mono text-sm">{{ s.step_type }}</span></td>
            <td><span :class="`pill pill-${s.status}`">{{ s.status }}</span></td>
            <td>{{ s.latency_ms }} ms</td>
            <td class="text-mono text-sm">{{ s.tokens_input }} / {{ s.tokens_output }}</td>
            <td>{{ fmtCost(s.cost) }}</td>
            <td class="text-mono text-sm" style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              <span v-if="s.error_message" style="color:#dc2626">{{ s.error_message }}</span>
              <span v-else>{{ JSON.stringify(s.output_data).slice(0, 80) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
