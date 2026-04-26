<script setup>
import { ref, onMounted } from 'vue'
import { dashboardApi, executionsApi } from '../api.js'

const kpis = ref(null)
const recent = ref([])
const loading = ref(true)
const error = ref(null)
const days = ref(30)

const fmtPct = (v) => `${(v * 100).toFixed(1)}%`
const fmtCost = (v) => `$${(v || 0).toFixed(4)}`
const fmtMs = (v) => `${Math.round(v || 0)} ms`
const fmtNum = (v) => (v || 0).toLocaleString()

async function load() {
  loading.value = true
  error.value = null
  try {
    const [k, r] = await Promise.all([
      dashboardApi.kpis(days.value),
      executionsApi.list({ limit: 8 }),
    ])
    kpis.value = k
    recent.value = r
  } catch (e) {
    error.value = e.message || 'Failed to load dashboard'
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
        <h2 class="section-title">Operational overview</h2>
        <p class="section-subtitle">KPIs, cost, and recent activity across all agents.</p>
      </div>
      <div class="toolbar-filters">
        <select class="form-control" v-model.number="days" @change="load">
          <option :value="1">Last 24h</option>
          <option :value="7">Last 7 days</option>
          <option :value="30">Last 30 days</option>
          <option :value="90">Last 90 days</option>
        </select>
        <button class="btn" @click="load">Refresh</button>
      </div>
    </div>

    <div v-if="error" class="error-banner mb-4">{{ error }}</div>
    <div v-if="loading" class="loading">Loading dashboard…</div>

    <template v-else-if="kpis">
      <!-- Operational KPIs -->
      <div class="grid grid-4 mb-4">
        <div class="kpi">
          <div class="kpi-label">Total Executions</div>
          <div class="kpi-value">{{ fmtNum(kpis.total_executions) }}</div>
          <div class="kpi-sub">Last {{ days }} day{{ days === 1 ? '' : 's' }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Success Rate</div>
          <div class="kpi-value">{{ fmtPct(kpis.success_rate) }}</div>
          <div class="kpi-sub">Reliability indicator</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Avg Latency</div>
          <div class="kpi-value">{{ fmtMs(kpis.average_latency_ms) }}</div>
          <div class="kpi-sub">End-to-end execution time</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Escalation Rate</div>
          <div class="kpi-value">{{ fmtPct(kpis.human_escalation_rate) }}</div>
          <div class="kpi-sub">Manual review needed</div>
        </div>
      </div>

      <!-- Quality KPIs -->
      <div class="grid grid-4 mb-4">
        <div class="kpi">
          <div class="kpi-label">Endpoint Failure Rate</div>
          <div class="kpi-value">{{ fmtPct(kpis.endpoint_failure_rate) }}</div>
          <div class="kpi-sub">Integration stability</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Model Failure Rate</div>
          <div class="kpi-value">{{ fmtPct(kpis.model_failure_rate) }}</div>
          <div class="kpi-sub">LLM reliability</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Schema Compliance</div>
          <div class="kpi-value">{{ fmtPct(kpis.schema_compliance_rate) }}</div>
          <div class="kpi-sub">Structured output validity</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Total Cost</div>
          <div class="kpi-value">{{ fmtCost(kpis.total_cost) }}</div>
          <div class="kpi-sub">{{ fmtNum(kpis.total_tokens) }} tokens</div>
        </div>
      </div>

      <!-- Inventory + recent activity -->
      <div class="grid grid-2">
        <div class="card">
          <div class="card-header"><div class="card-title">Platform inventory</div></div>
          <div class="card-body">
            <div class="grid grid-3">
              <div>
                <div class="kpi-label">Active Agents</div>
                <div class="kpi-value" style="font-size:22px">{{ kpis.active_agents }}</div>
              </div>
              <div>
                <div class="kpi-label">Endpoints</div>
                <div class="kpi-value" style="font-size:22px">{{ kpis.active_endpoints }}</div>
              </div>
              <div>
                <div class="kpi-label">AI Models</div>
                <div class="kpi-value" style="font-size:22px">{{ kpis.active_models }}</div>
              </div>
            </div>
            <div class="mt-4 text-sm text-muted">
              Cost per successful run:
              <strong>{{ fmtCost(kpis.cost_per_successful_run) }}</strong>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Recent executions</div>
            <router-link to="/executions" class="text-sm">View all →</router-link>
          </div>
          <div class="card-body" style="padding:0">
            <table v-if="recent.length" class="table">
              <thead>
                <tr><th>ID</th><th>Status</th><th>Cost</th><th>Latency</th><th>Started</th></tr>
              </thead>
              <tbody>
                <tr v-for="e in recent" :key="e.id">
                  <td>
                    <router-link :to="`/executions/${e.id}`" class="text-mono">
                      #{{ e.id }}
                    </router-link>
                  </td>
                  <td><span :class="`pill pill-${e.status}`">{{ e.status }}</span></td>
                  <td>{{ fmtCost(e.total_cost) }}</td>
                  <td>{{ fmtMs(e.total_latency_ms) }}</td>
                  <td class="text-sm text-muted">
                    {{ new Date(e.started_at).toLocaleString() }}
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="empty-state">
              <h3>No executions yet</h3>
              <p>Run an agent to see traces here.</p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
