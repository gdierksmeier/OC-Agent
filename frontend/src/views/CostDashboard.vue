<script setup>
import { ref, computed, onMounted } from 'vue'
import { dashboardApi } from '../api.js'

const summary = ref(null)
const budgets = ref([])
const loading = ref(true)
const error = ref(null)
const days = ref(30)
const showCreate = ref(false)
const saving = ref(false)

const blank = () => ({
  name: '', scope: 'global', scope_id: '',
  period: 'monthly', limit_amount: 100, warning_threshold: 0.8, hard_limit: false,
})
const draft = ref(blank())

const fmtCost = (v) => `$${(v || 0).toFixed(4)}`

const maxBy = (arr, key = 'cost') =>
  arr.length ? Math.max(...arr.map(r => r[key])) : 1

const maxModel = computed(() => maxBy(summary.value?.by_model || []))
const maxAgent = computed(() => maxBy(summary.value?.by_agent || []))
const maxEnv   = computed(() => maxBy(summary.value?.by_environment || []))
const maxDay   = computed(() => maxBy(summary.value?.daily_trend || []))

async function load() {
  loading.value = true
  try {
    const [s, b] = await Promise.all([
      dashboardApi.costSummary(days.value),
      dashboardApi.budgets(),
    ])
    summary.value = s
    budgets.value = b
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function createBudget() {
  saving.value = true
  try {
    const payload = { ...draft.value }
    if (!payload.scope_id) payload.scope_id = null
    await dashboardApi.createBudget(payload)
    showCreate.value = false
    draft.value = blank()
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <div>
        <h2 class="section-title">Cost Validation</h2>
        <p class="section-subtitle">Track token usage, endpoint cost, and budget consumption.</p>
      </div>
      <div class="toolbar-filters">
        <select class="form-control" v-model.number="days" @change="load">
          <option :value="7">Last 7 days</option>
          <option :value="30">Last 30 days</option>
          <option :value="90">Last 90 days</option>
        </select>
        <button class="btn btn-primary" @click="showCreate = true">+ Budget</button>
      </div>
    </div>

    <div v-if="error" class="error-banner mb-4">{{ error }}</div>
    <div v-if="loading" class="loading">Loading…</div>

    <template v-else-if="summary">
      <div class="grid grid-2 mb-4">
        <div class="kpi">
          <div class="kpi-label">Total cost ({{ days }}d)</div>
          <div class="kpi-value">{{ fmtCost(summary.total_cost) }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Active budgets</div>
          <div class="kpi-value">{{ budgets.filter(b => b.is_active).length }}</div>
        </div>
      </div>

      <!-- Breakdowns -->
      <div class="grid grid-2 mb-4">
        <div class="card">
          <div class="card-header"><div class="card-title">Cost by model</div></div>
          <div class="card-body">
            <div v-if="!summary.by_model.length" class="text-muted text-sm">No data.</div>
            <div v-for="row in summary.by_model" :key="row.model" class="bar-row">
              <div class="label">{{ row.model }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: (row.cost / maxModel * 100) + '%' }"></div>
              </div>
              <div class="value">{{ fmtCost(row.cost) }}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><div class="card-title">Cost by agent</div></div>
          <div class="card-body">
            <div v-if="!summary.by_agent.length" class="text-muted text-sm">No data.</div>
            <div v-for="row in summary.by_agent" :key="row.agent" class="bar-row">
              <div class="label">{{ row.agent }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: (row.cost / maxAgent * 100) + '%' }"></div>
              </div>
              <div class="value">{{ fmtCost(row.cost) }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-2 mb-4">
        <div class="card">
          <div class="card-header"><div class="card-title">Cost by environment</div></div>
          <div class="card-body">
            <div v-if="!summary.by_environment.length" class="text-muted text-sm">No data.</div>
            <div v-for="row in summary.by_environment" :key="row.environment" class="bar-row">
              <div class="label">{{ row.environment }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: (row.cost / maxEnv * 100) + '%' }"></div>
              </div>
              <div class="value">{{ fmtCost(row.cost) }}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><div class="card-title">Daily trend</div></div>
          <div class="card-body">
            <div v-if="!summary.daily_trend.length" class="text-muted text-sm">No data.</div>
            <div v-for="row in summary.daily_trend" :key="row.date" class="bar-row">
              <div class="label">{{ row.date }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: (row.cost / maxDay * 100) + '%' }"></div>
              </div>
              <div class="value">{{ fmtCost(row.cost) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Budgets -->
      <div class="card">
        <div class="card-header"><div class="card-title">Budgets</div></div>
        <div v-if="!budgets.length" class="empty-state">
          <h3>No budgets configured</h3>
          <p>Set spending limits per agent, department, user, or globally.</p>
        </div>
        <table v-else class="table">
          <thead>
            <tr>
              <th>Name</th><th>Scope</th><th>Period</th><th>Limit</th>
              <th>Consumed</th><th>Hard limit</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in budgets" :key="b.id">
              <td><strong>{{ b.name }}</strong></td>
              <td><span class="text-mono text-sm">{{ b.scope }}{{ b.scope_id ? `:${b.scope_id}` : '' }}</span></td>
              <td>{{ b.period }}</td>
              <td>{{ fmtCost(b.limit_amount) }}</td>
              <td>{{ fmtCost(b.current_consumption) }}</td>
              <td>{{ b.hard_limit ? 'Yes' : 'Warning only' }}</td>
              <td>
                <span :class="b.is_active ? 'pill pill-active' : 'pill pill-inactive'">
                  {{ b.is_active ? 'active' : 'inactive' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Create budget modal -->
    <div v-if="showCreate" class="modal-backdrop" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">New budget</div>
          <button class="modal-close" @click="showCreate = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <label class="form-label">Name</label>
            <input v-model="draft.name" class="form-control">
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Scope</label>
              <select v-model="draft.scope" class="form-control">
                <option>global</option><option>agent</option>
                <option>department</option><option>user</option><option>environment</option>
              </select>
            </div>
            <div>
              <label class="form-label">Scope ID (optional)</label>
              <input v-model="draft.scope_id" class="form-control" placeholder="e.g. agent id, dept name">
            </div>
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Period</label>
              <select v-model="draft.period" class="form-control">
                <option>daily</option><option>weekly</option><option>monthly</option>
              </select>
            </div>
            <div>
              <label class="form-label">Limit ($)</label>
              <input v-model.number="draft.limit_amount" type="number" step="0.01" class="form-control">
            </div>
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Warning threshold (0-1)</label>
              <input v-model.number="draft.warning_threshold" type="number" step="0.05" class="form-control">
            </div>
            <div style="display:flex;align-items:center;gap:8px;padding-top:22px">
              <label class="text-sm">
                <input type="checkbox" v-model="draft.hard_limit"> Hard limit (block on exceed)
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showCreate = false">Cancel</button>
          <button class="btn btn-primary" :disabled="saving || !draft.name" @click="createBudget">
            {{ saving ? 'Saving…' : 'Create' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
