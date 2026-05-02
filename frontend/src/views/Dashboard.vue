<script setup>
import { computed, onMounted, ref } from 'vue'
import { dashboardApi, executionsApi } from '../api.js'

const kpis = ref(null)
const recent = ref([])
const series = ref(null)
const cost = ref(null)
const loading = ref(true)
const error = ref(null)
const days = ref(30)

const fmtPct = (v) => `${((v ?? 0) * 100).toFixed(1)}%`
const fmtCost = (v) => `$${(v || 0).toFixed(4)}`
const fmtMs = (v) => `${Math.round(v || 0)} ms`
const fmtNum = (v) => (v || 0).toLocaleString()

async function load() {
  loading.value = true
  error.value = null
  try {
    const [k, r, t, c] = await Promise.all([
      dashboardApi.kpis(days.value),
      executionsApi.list({ limit: 8 }),
      dashboardApi.timeseries(days.value),
      dashboardApi.costSummary(days.value),
    ])
    kpis.value = k
    recent.value = r
    series.value = t
    cost.value = c
  } catch (e) {
    error.value = e.message || 'Failed to load dashboard'
  } finally {
    loading.value = false
  }
}

onMounted(load)

// ---------- Chart helpers (pure SVG, no deps) ----------

const STATUS_COLORS = {
  success: '#10b981',
  failed: '#ef4444',
  escalated: '#f59e0b',
  running: '#3b82f6',
  skipped: '#6b7280',
  other: '#94a3b8',
}

// Daily-executions area chart geometry
const trendChart = computed(() => {
  const data = series.value?.daily || []
  if (!data.length) return null
  const W = 720
  const H = 180
  const PAD = { l: 40, r: 16, t: 12, b: 24 }
  const innerW = W - PAD.l - PAD.r
  const innerH = H - PAD.t - PAD.b
  const max = Math.max(1, ...data.map(d => d.total))
  const step = data.length > 1 ? innerW / (data.length - 1) : 0
  const x = (i) => PAD.l + i * step
  const y = (v) => PAD.t + innerH - (v / max) * innerH

  const buildPath = (key) => {
    const pts = data.map((d, i) => `${x(i)},${y(d[key] || 0)}`)
    return pts.length ? `M ${pts.join(' L ')}` : ''
  }
  const buildArea = (key) => {
    const pts = data.map((d, i) => `${x(i)},${y(d[key] || 0)}`)
    if (!pts.length) return ''
    return `M ${PAD.l},${PAD.t + innerH} L ${pts.join(' L ')} L ${x(data.length - 1)},${PAD.t + innerH} Z`
  }
  // Y-axis ticks (4 lines)
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(t => ({
    y: PAD.t + innerH - t * innerH,
    label: Math.round(max * t),
  }))
  // X-axis labels — first, middle, last
  const xLabels = data.length
    ? [
        { i: 0, label: data[0].date.slice(5) },
        { i: Math.floor(data.length / 2), label: data[Math.floor(data.length / 2)].date.slice(5) },
        { i: data.length - 1, label: data[data.length - 1].date.slice(5) },
      ]
    : []
  return { W, H, PAD, innerW, innerH, max, x, y, data, buildPath, buildArea, ticks, xLabels }
})

// Status donut geometry
const donut = computed(() => {
  const items = (series.value?.status_breakdown || []).filter(s => s.count > 0)
  const total = items.reduce((acc, s) => acc + s.count, 0)
  if (!total) return null
  const cx = 75, cy = 75, r = 60, sw = 22
  let angle = -Math.PI / 2
  const arcs = items.map(s => {
    const frac = s.count / total
    const a0 = angle
    const a1 = angle + frac * Math.PI * 2
    angle = a1
    const large = frac > 0.5 ? 1 : 0
    const x0 = cx + r * Math.cos(a0)
    const y0 = cy + r * Math.sin(a0)
    const x1 = cx + r * Math.cos(a1)
    const y1 = cy + r * Math.sin(a1)
    return {
      d: `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`,
      color: STATUS_COLORS[s.status] || STATUS_COLORS.other,
      status: s.status,
      count: s.count,
      pct: frac,
    }
  })
  return { cx, cy, r, sw, arcs, total }
})

// Cost-by-model horizontal bars
const costBars = computed(() => {
  const items = (cost.value?.by_model || []).slice(0, 6)
  if (!items.length) return null
  const max = Math.max(...items.map(i => i.cost), 0.0001)
  const palette = ['#60a5fa', '#a78bfa', '#22d3ee', '#34d399', '#fbbf24', '#f472b6']
  return items.map((it, i) => ({
    label: it.model,
    cost: it.cost,
    pct: it.cost / max,
    color: palette[i % palette.length],
  }))
})

// Color/icon mapping per KPI tile
const KPI_THEMES = {
  total: { color: '#60a5fa', icon: '◆' },
  success: { color: '#10b981', icon: '✓' },
  latency: { color: '#22d3ee', icon: '◷' },
  escalation: { color: '#f59e0b', icon: '⚠' },
  endpoint: { color: '#fb7185', icon: '⇆' },
  model: { color: '#a78bfa', icon: '⊛' },
  schema: { color: '#34d399', icon: '✶' },
  cost: { color: '#fbbf24', icon: '$' },
}
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
      <!-- Operational KPIs (colored) -->
      <div class="grid grid-4 mb-4">
        <div class="kpi kpi-themed" :style="{ '--kpi-accent': KPI_THEMES.total.color }">
          <div class="kpi-row">
            <span class="kpi-icon">{{ KPI_THEMES.total.icon }}</span>
            <div class="kpi-label">Total Executions</div>
          </div>
          <div class="kpi-value">{{ fmtNum(kpis.total_executions) }}</div>
          <div class="kpi-sub">Last {{ days }} day{{ days === 1 ? '' : 's' }}</div>
        </div>
        <div class="kpi kpi-themed" :style="{ '--kpi-accent': KPI_THEMES.success.color }">
          <div class="kpi-row">
            <span class="kpi-icon">{{ KPI_THEMES.success.icon }}</span>
            <div class="kpi-label">Success Rate</div>
          </div>
          <div class="kpi-value">{{ fmtPct(kpis.success_rate) }}</div>
          <div class="kpi-bar">
            <div class="kpi-bar-fill" :style="{ width: fmtPct(kpis.success_rate) }" />
          </div>
        </div>
        <div class="kpi kpi-themed" :style="{ '--kpi-accent': KPI_THEMES.latency.color }">
          <div class="kpi-row">
            <span class="kpi-icon">{{ KPI_THEMES.latency.icon }}</span>
            <div class="kpi-label">Avg Latency</div>
          </div>
          <div class="kpi-value">{{ fmtMs(kpis.average_latency_ms) }}</div>
          <div class="kpi-sub">End-to-end execution time</div>
        </div>
        <div class="kpi kpi-themed" :style="{ '--kpi-accent': KPI_THEMES.escalation.color }">
          <div class="kpi-row">
            <span class="kpi-icon">{{ KPI_THEMES.escalation.icon }}</span>
            <div class="kpi-label">Escalation Rate</div>
          </div>
          <div class="kpi-value">{{ fmtPct(kpis.human_escalation_rate) }}</div>
          <div class="kpi-bar">
            <div class="kpi-bar-fill" :style="{ width: fmtPct(kpis.human_escalation_rate) }" />
          </div>
        </div>
      </div>

      <!-- Quality KPIs (colored) -->
      <div class="grid grid-4 mb-4">
        <div class="kpi kpi-themed" :style="{ '--kpi-accent': KPI_THEMES.endpoint.color }">
          <div class="kpi-row">
            <span class="kpi-icon">{{ KPI_THEMES.endpoint.icon }}</span>
            <div class="kpi-label">Endpoint Failure</div>
          </div>
          <div class="kpi-value">{{ fmtPct(kpis.endpoint_failure_rate) }}</div>
          <div class="kpi-sub">Integration stability</div>
        </div>
        <div class="kpi kpi-themed" :style="{ '--kpi-accent': KPI_THEMES.model.color }">
          <div class="kpi-row">
            <span class="kpi-icon">{{ KPI_THEMES.model.icon }}</span>
            <div class="kpi-label">Model Failure</div>
          </div>
          <div class="kpi-value">{{ fmtPct(kpis.model_failure_rate) }}</div>
          <div class="kpi-sub">LLM reliability</div>
        </div>
        <div class="kpi kpi-themed" :style="{ '--kpi-accent': KPI_THEMES.schema.color }">
          <div class="kpi-row">
            <span class="kpi-icon">{{ KPI_THEMES.schema.icon }}</span>
            <div class="kpi-label">Schema Compliance</div>
          </div>
          <div class="kpi-value">{{ fmtPct(kpis.schema_compliance_rate) }}</div>
          <div class="kpi-bar">
            <div class="kpi-bar-fill" :style="{ width: fmtPct(kpis.schema_compliance_rate) }" />
          </div>
        </div>
        <div class="kpi kpi-themed" :style="{ '--kpi-accent': KPI_THEMES.cost.color }">
          <div class="kpi-row">
            <span class="kpi-icon">{{ KPI_THEMES.cost.icon }}</span>
            <div class="kpi-label">Total Cost</div>
          </div>
          <div class="kpi-value">{{ fmtCost(kpis.total_cost) }}</div>
          <div class="kpi-sub">{{ fmtNum(kpis.total_tokens) }} tokens</div>
        </div>
      </div>

      <!-- Charts row -->
      <div class="grid grid-2 mb-4">
        <!-- Daily executions trend -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">Daily executions</div>
            <span v-if="trendChart" class="text-sm text-muted">
              peak {{ trendChart.max }} / day
            </span>
          </div>
          <div class="card-body" style="padding: 16px">
            <div v-if="!trendChart || !trendChart.data.some(d => d.total)" class="empty-state" style="padding:32px 0">
              <p>No executions in this window. Run an agent to see trends.</p>
            </div>
            <svg v-else :viewBox="`0 0 ${trendChart.W} ${trendChart.H}`" class="dash-chart">
              <defs>
                <linearGradient id="trendArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.45" />
                  <stop offset="100%" stop-color="#3b82f6" stop-opacity="0" />
                </linearGradient>
                <linearGradient id="trendLine" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stop-color="#60a5fa" />
                  <stop offset="100%" stop-color="#22d3ee" />
                </linearGradient>
              </defs>
              <!-- Gridlines -->
              <g class="grid-lines">
                <line v-for="(t, i) in trendChart.ticks" :key="i"
                  :x1="trendChart.PAD.l" :x2="trendChart.W - trendChart.PAD.r"
                  :y1="t.y" :y2="t.y" stroke="#e5e7eb" stroke-dasharray="2 4" />
                <text v-for="(t, i) in trendChart.ticks" :key="`l${i}`"
                  :x="trendChart.PAD.l - 8" :y="t.y + 4" text-anchor="end"
                  font-size="10" fill="#6b7280">{{ t.label }}</text>
              </g>
              <!-- Area for total -->
              <path :d="trendChart.buildArea('total')" fill="url(#trendArea)" />
              <!-- Total line -->
              <path :d="trendChart.buildPath('total')" fill="none"
                stroke="url(#trendLine)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
              <!-- Failed line -->
              <path :d="trendChart.buildPath('failed')" fill="none"
                stroke="#ef4444" stroke-width="1.5" stroke-dasharray="3 3" />
              <!-- Escalated line -->
              <path :d="trendChart.buildPath('escalated')" fill="none"
                stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="3 3" />
              <!-- Data points -->
              <circle v-for="(d, i) in trendChart.data" :key="`p${i}`"
                :cx="trendChart.x(i)" :cy="trendChart.y(d.total)" r="2.5"
                fill="#60a5fa" />
              <!-- X axis labels -->
              <text v-for="(l, i) in trendChart.xLabels" :key="`xl${i}`"
                :x="trendChart.x(l.i)" :y="trendChart.H - 6"
                text-anchor="middle" font-size="10" fill="#6b7280">{{ l.label }}</text>
            </svg>
            <div class="chart-legend">
              <span><i class="dot" style="background:#60a5fa"/> Total</span>
              <span><i class="dot" style="background:#ef4444"/> Failed</span>
              <span><i class="dot" style="background:#f59e0b"/> Escalated</span>
            </div>
          </div>
        </div>

        <!-- Status donut -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">Status breakdown</div>
            <span v-if="donut" class="text-sm text-muted">{{ fmtNum(donut.total) }} runs</span>
          </div>
          <div class="card-body donut-body">
            <div v-if="!donut" class="empty-state" style="padding:32px 0; flex: 1">
              <p>No executions yet.</p>
            </div>
            <template v-else>
              <svg viewBox="0 0 150 150" class="donut-svg">
                <circle :cx="donut.cx" :cy="donut.cy" :r="donut.r"
                  fill="none" stroke="#f3f4f6" :stroke-width="donut.sw" />
                <path v-for="(a, i) in donut.arcs" :key="i"
                  :d="a.d" fill="none" :stroke="a.color"
                  :stroke-width="donut.sw" stroke-linecap="butt" />
                <text :x="donut.cx" :y="donut.cy - 4" text-anchor="middle"
                  font-size="22" font-weight="700" fill="#111827">{{ donut.total }}</text>
                <text :x="donut.cx" :y="donut.cy + 14" text-anchor="middle"
                  font-size="10" fill="#6b7280" letter-spacing="1.5">RUNS</text>
              </svg>
              <ul class="donut-legend">
                <li v-for="(a, i) in donut.arcs" :key="i">
                  <i class="dot" :style="{ background: a.color }" />
                  <span class="donut-name">{{ a.status }}</span>
                  <span class="donut-count">{{ a.count }}</span>
                  <span class="donut-pct">{{ (a.pct * 100).toFixed(0) }}%</span>
                </li>
              </ul>
            </template>
          </div>
        </div>
      </div>

      <!-- Cost by model + Top agents -->
      <div class="grid grid-2 mb-4">
        <div class="card">
          <div class="card-header">
            <div class="card-title">Cost by model</div>
            <router-link to="/cost" class="text-sm">Details →</router-link>
          </div>
          <div class="card-body">
            <div v-if="!costBars" class="empty-state" style="padding:24px 0">
              <p>No cost recorded yet.</p>
            </div>
            <ul v-else class="bar-list">
              <li v-for="b in costBars" :key="b.label" class="bar-row">
                <div class="bar-label">{{ b.label }}</div>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: `${Math.max(2, b.pct * 100)}%`, background: b.color }" />
                </div>
                <div class="bar-value">{{ fmtCost(b.cost) }}</div>
              </li>
            </ul>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Top agents by activity</div>
          </div>
          <div class="card-body">
            <div v-if="!series?.top_agents?.length" class="empty-state" style="padding:24px 0">
              <p>No agent activity yet.</p>
            </div>
            <ul v-else class="bar-list">
              <li v-for="(a, i) in series.top_agents" :key="a.agent_id || i" class="bar-row">
                <div class="bar-label">
                  <router-link v-if="a.agent_id" :to="`/agents/${a.agent_id}`">{{ a.name }}</router-link>
                  <span v-else>{{ a.name }}</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill"
                    :style="{
                      width: `${Math.max(2, (a.executions / series.top_agents[0].executions) * 100)}%`,
                      background: ['#60a5fa','#a78bfa','#22d3ee','#34d399','#fbbf24'][i % 5]
                    }" />
                </div>
                <div class="bar-value">{{ a.executions }} run{{ a.executions === 1 ? '' : 's' }}</div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Inventory + recent activity -->
      <div class="grid grid-2">
        <div class="card">
          <div class="card-header"><div class="card-title">Platform inventory</div></div>
          <div class="card-body">
            <div class="grid grid-3">
              <div class="inv-tile" style="--inv: #60a5fa">
                <div class="inv-num">{{ kpis.active_agents }}</div>
                <div class="inv-label">Active Agents</div>
              </div>
              <div class="inv-tile" style="--inv: #fb7185">
                <div class="inv-num">{{ kpis.active_endpoints }}</div>
                <div class="inv-label">Endpoints</div>
              </div>
              <div class="inv-tile" style="--inv: #a78bfa">
                <div class="inv-num">{{ kpis.active_models }}</div>
                <div class="inv-label">AI Models</div>
              </div>
            </div>
            <div class="mt-4 text-sm text-muted">
              Cost per successful run:
              <strong style="color:#fbbf24">{{ fmtCost(kpis.cost_per_successful_run) }}</strong>
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

<style scoped>
.kpi-themed {
  position: relative;
  border-left: 4px solid var(--kpi-accent);
  overflow: hidden;
}
.kpi-themed::before {
  content: '';
  position: absolute;
  top: -30px;
  right: -30px;
  width: 110px;
  height: 110px;
  border-radius: 50%;
  background: var(--kpi-accent);
  opacity: 0.07;
}
.kpi-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.kpi-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--kpi-accent) 18%, transparent);
  color: var(--kpi-accent);
  font-size: 13px;
  font-weight: 700;
}
.kpi-themed .kpi-value { color: var(--kpi-accent); }
.kpi-bar {
  margin-top: 10px;
  height: 5px;
  background: #f3f4f6;
  border-radius: 999px;
  overflow: hidden;
}
.kpi-bar-fill {
  height: 100%;
  background: var(--kpi-accent);
  border-radius: 999px;
  transition: width 0.4s ease;
}

/* Charts */
.dash-chart {
  width: 100%;
  height: 180px;
  display: block;
}
.chart-legend {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #6b7280;
  margin-top: 8px;
  padding-left: 40px;
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

/* Donut */
.donut-body {
  display: flex;
  align-items: center;
  gap: 20px;
}
.donut-svg {
  width: 150px;
  height: 150px;
  flex-shrink: 0;
}
.donut-legend {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  font-size: 13px;
}
.donut-legend li {
  display: grid;
  grid-template-columns: 14px 1fr auto auto;
  gap: 8px;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px dashed #e5e7eb;
}
.donut-legend li:last-child { border-bottom: none; }
.donut-name { text-transform: capitalize; color: #374151; }
.donut-count { font-variant-numeric: tabular-nums; color: #111827; font-weight: 600; }
.donut-pct { color: #6b7280; font-size: 11px; min-width: 32px; text-align: right; }

/* Bar list */
.bar-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.bar-row {
  display: grid;
  grid-template-columns: 30% 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed #e5e7eb;
  font-size: 13px;
}
.bar-row:last-child { border-bottom: none; }
.bar-label {
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bar-track {
  background: #f3f4f6;
  border-radius: 999px;
  height: 10px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}
.bar-value {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  color: #6b7280;
  min-width: 90px;
  text-align: right;
}

/* Inventory tiles */
.inv-tile {
  background: color-mix(in srgb, var(--inv) 8%, white);
  border: 1px solid color-mix(in srgb, var(--inv) 25%, transparent);
  border-radius: 10px;
  padding: 14px;
  text-align: center;
}
.inv-num {
  font-size: 26px;
  font-weight: 700;
  color: var(--inv);
  font-variant-numeric: tabular-nums;
}
.inv-label {
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 2px;
}
</style>
