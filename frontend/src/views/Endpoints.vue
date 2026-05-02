<script setup>
import { ref, onMounted } from 'vue'
import { endpointsApi } from '../api.js'

const endpoints = ref([])
const loading = ref(true)
const error = ref(null)
const showCreate = ref(false)
const saving = ref(false)
const testResult = ref(null)
const testing = ref(false)
const savingRegistry = ref(false)
const showTestModal = ref(false)
const testEndpoint = ref(null)

const testForm = ref({
  base_url: '',
  path: '',
  method: 'GET',
  settingsEnvironment: 'dev',
  registryEnvironment: 'dev',
  inputJson: '{\n  "account_id": "123456789",\n  "reference_date": "2026-04-01"\n}',
  queryOverrideJson: '',
  realHttp: true,
})

const blank = () => ({
  name: '', description: '', base_url: '', path: '', method: 'GET',
  auth_type: 'none', auth_config: {}, headers: {}, query_params_template: {},
  body_template: '', timeout_seconds: 30, environment: 'dev',
  estimated_cost_per_call: 0, response_mapping: {},
})
const draft = ref(blank())

async function load() {
  loading.value = true
  try {
    endpoints.value = await endpointsApi.list()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function create() {
  saving.value = true
  try {
    await endpointsApi.create(draft.value)
    showCreate.value = false
    draft.value = blank()
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

async function remove(id) {
  if (!confirm('Delete this endpoint?')) return
  await endpointsApi.remove(id)
  await load()
}

function openTestModal(ep) {
  error.value = null
  testResult.value = null
  testEndpoint.value = ep
  testForm.value = {
    base_url: ep.base_url,
    path: ep.path,
    method: ep.method || 'GET',
    settingsEnvironment: 'dev',
    registryEnvironment: ep.environment || 'dev',
    inputJson: '{\n  "account_id": "123456789",\n  "reference_date": "2026-04-01"\n}',
    queryOverrideJson: ep.query_params_template
      ? JSON.stringify(ep.query_params_template, null, 2)
      : '',
    realHttp: true,
  }
  showTestModal.value = true
}

function closeTestModal() {
  showTestModal.value = false
  testEndpoint.value = null
}

function buildTestPayload() {
  let parsedInput = {}
  try {
    parsedInput = testForm.value.inputJson?.trim() ? JSON.parse(testForm.value.inputJson) : {}
  } catch {
    throw new Error('Input data must be valid JSON')
  }
  let overrideQuery = undefined
  if (testForm.value.queryOverrideJson?.trim()) {
    try {
      overrideQuery = JSON.parse(testForm.value.queryOverrideJson)
      if (typeof overrideQuery !== 'object' || overrideQuery === null || Array.isArray(overrideQuery)) {
        throw new Error('Query override must be a JSON object')
      }
    } catch (e) {
      if (e.message.startsWith('Query')) throw e
      throw new Error('Query override must be valid JSON object')
    }
  }
  return {
    environment: testForm.value.settingsEnvironment,
    input_data: parsedInput,
    real_http: testForm.value.realHttp,
    override_base_url: testForm.value.base_url || null,
    override_path: testForm.value.path ?? '',
    override_method: testForm.value.method || null,
    override_query_params: overrideQuery,
  }
}

async function runTest() {
  if (!testEndpoint.value) return
  testing.value = true
  testResult.value = null
  error.value = null
  try {
    const payload = buildTestPayload()
    testResult.value = await endpointsApi.test(testEndpoint.value.id, payload)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    testing.value = false
  }
}

async function saveRegistry() {
  if (!testEndpoint.value) return
  savingRegistry.value = true
  error.value = null
  try {
    await endpointsApi.update(testEndpoint.value.id, {
      base_url: testForm.value.base_url,
      path: testForm.value.path,
      method: testForm.value.method,
      environment: testForm.value.registryEnvironment,
    })
    await load()
    const fresh = endpoints.value.find((e) => e.id === testEndpoint.value.id)
    if (fresh) {
      testEndpoint.value = fresh
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    savingRegistry.value = false
  }
}

function displayOutput(r) {
  if (!r) return ''
  if (r.output != null && String(r.output).length) return r.output
  if (r.response_body != null) {
    if (typeof r.response_body === 'string') return r.response_body
    return JSON.stringify(r.response_body, null, 2)
  }
  return r.error || ''
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text || '')
  } catch {
    /* ignore */
  }
}

const METHOD_COLORS = {
  GET:    '#10b981',
  POST:   '#3b82f6',
  PUT:    '#f59e0b',
  PATCH:  '#a78bfa',
  DELETE: '#ef4444',
  SOAP:   '#6b7280',
}
function methodColor(m) { return METHOD_COLORS[(m || '').toUpperCase()] || '#6b7280' }

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <div>
        <h2 class="section-title">Endpoint Registry</h2>
        <p class="section-subtitle">Reusable API endpoints that agents can call as tools. Use <strong>Review</strong> to change URL, method, environments, and run real or simulated calls. After a test, the <strong>cURL</strong> (tokens masked) and <strong>output</strong> are shown below.</p>
      </div>
      <button class="btn btn-primary" @click="showCreate = true">+ Register endpoint</button>
    </div>

    <div v-if="error" class="error-banner mb-4">{{ error }}</div>
    <div v-if="loading" class="loading">Loading…</div>

    <div v-else-if="!endpoints.length" class="card">
      <div class="empty-state">
        <h3>No endpoints registered</h3>
        <p>Add an endpoint so agents can call it via configuration.</p>
      </div>
    </div>

    <div v-else class="card">
      <table class="table">
        <thead>
          <tr>
            <th>Name</th><th>URL</th><th>Method</th><th>Auth</th>
            <th>Env</th><th>Active</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ep in endpoints" :key="ep.id">
            <td>
              <strong>{{ ep.name }}</strong>
              <div class="text-sm text-muted">{{ ep.description || '—' }}</div>
            </td>
            <td class="text-mono text-sm">{{ ep.base_url }}{{ ep.path }}</td>
            <td>
              <span class="method-badge" :style="{ '--m': methodColor(ep.method) }">{{ ep.method }}</span>
            </td>
            <td><span class="text-mono text-sm">{{ ep.auth_type }}</span></td>
            <td>{{ ep.environment }}</td>
            <td>
              <span :class="ep.is_active ? 'pill pill-active' : 'pill pill-inactive'">
                {{ ep.is_active ? 'active' : 'inactive' }}
              </span>
            </td>
            <td class="table-actions">
              <button class="btn btn-sm" :disabled="testing" @click="openTestModal(ep)">Review</button>
              <button class="btn btn-sm btn-danger" @click="remove(ep.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="testResult" class="card mt-4">
      <div class="card-header">
        <div class="card-title">
          Test result · {{ testResult.name }}
          <span v-if="testResult.mode" class="text-mono text-sm text-muted" style="margin-left:8px">({{ testResult.mode }})</span>
        </div>
        <span :class="`pill pill-${testResult.status === 'ok' ? 'success' : 'failed'}`">
          {{ testResult.status_code }} · {{ testResult.latency_ms }} ms
        </span>
      </div>
      <div class="card-body endpoint-test-verbose">
        <div class="form-row two-col" style="margin-bottom: 12px">
          <div>
            <div class="text-sm text-muted">Resolved URL</div>
            <div class="text-mono text-sm word-break">{{ testResult.url }}{{ testResult.resolved_query_params && Object.keys(testResult.resolved_query_params).length ? ' + query params' : '' }}</div>
          </div>
          <div v-if="testResult.request_headers && Object.keys(testResult.request_headers).length">
            <div class="text-sm text-muted">Request headers (masked)</div>
            <pre class="endpoint-pre text-sm">{{ JSON.stringify(testResult.request_headers, null, 2) }}</pre>
          </div>
        </div>
        <div v-if="testResult.curl_command" class="form-row">
          <div class="flex-between" style="align-items: center; margin-bottom: 6px">
            <label class="form-label" style="margin: 0">cURL (same request; Authorization masked — paste your real token to replay)</label>
            <button type="button" class="btn btn-sm" @click="copyText(testResult.curl_command)">Copy</button>
          </div>
          <pre class="endpoint-pre">{{ testResult.curl_command }}</pre>
        </div>
        <div v-if="testResult.response_headers && testResult.mode === 'http'" class="form-row">
          <label class="form-label">Response headers</label>
          <pre class="endpoint-pre text-sm">{{ JSON.stringify(testResult.response_headers, null, 2) }}</pre>
        </div>
        <div class="form-row">
          <label class="form-label">Output (body or error text)</label>
          <pre class="endpoint-pre endpoint-pre-out">{{ displayOutput(testResult) }}</pre>
        </div>
        <details class="mt-2">
          <summary class="text-sm text-muted" style="cursor: pointer">Raw JSON (debug)</summary>
          <pre class="endpoint-pre text-sm mt-1">{{ JSON.stringify(testResult, null, 2) }}</pre>
        </details>
      </div>
    </div>

    <!-- Edit + test modal -->
    <div v-if="showTestModal && testEndpoint" class="modal-backdrop endpoint-review" @click.self="closeTestModal">
      <div class="modal endpoint-review-modal" :style="{ maxWidth: testResult ? 'min(960px, 96vw)' : '680px' }">
        <!-- Hero header with method-colored stripe -->
        <div class="er-hero" :style="{ '--m': methodColor(testForm.method) }">
          <button class="er-close" @click="closeTestModal" aria-label="Close">×</button>
          <div class="er-hero-top">
            <span class="er-eyebrow">Endpoint Review</span>
            <span :class="testEndpoint.is_active ? 'pill pill-active' : 'pill pill-inactive'">
              {{ testEndpoint.is_active ? 'active' : 'inactive' }}
            </span>
          </div>
          <h3 class="er-name">{{ testEndpoint.name }}</h3>
          <div class="er-url">
            <span class="method-badge" :style="{ '--m': methodColor(testForm.method) }">{{ testForm.method }}</span>
            <span class="er-url-text text-mono">{{ testForm.base_url || '—' }}<span class="er-url-path">{{ testForm.path || '/' }}</span></span>
          </div>
        </div>

        <div class="modal-body er-body">
          <!-- Section: Environments -->
          <div class="er-section">
            <div class="er-section-title">
              <span class="er-section-num">1</span> Environments
            </div>
            <p class="er-help">
              <strong>Settings env</strong> resolves host & token from Environment Settings.
              <strong>Registry env</strong> is the label saved on this endpoint row.
            </p>
            <div class="form-row two-col" style="margin-top:8px">
              <div>
                <label class="form-label">Settings environment</label>
                <select v-model="testForm.settingsEnvironment" class="form-control">
                  <option value="dev">DEV</option>
                  <option value="qa">QA</option>
                  <option value="prod">PROD</option>
                </select>
              </div>
              <div>
                <label class="form-label">Registry environment</label>
                <select v-model="testForm.registryEnvironment" class="form-control">
                  <option value="dev">dev</option>
                  <option value="qa">qa</option>
                  <option value="prod">prod</option>
                  <option value="test">test</option>
                  <option value="uat">uat</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Section: Endpoint -->
          <div class="er-section">
            <div class="er-section-title">
              <span class="er-section-num">2</span> Endpoint
            </div>
            <div class="form-row two-col">
              <div>
                <label class="form-label">Base URL</label>
                <input v-model="testForm.base_url" class="form-control text-mono" placeholder="http://host:port or placeholders">
              </div>
              <div>
                <label class="form-label">Method</label>
                <select v-model="testForm.method" class="form-control">
                  <option>GET</option>
                  <option>POST</option>
                  <option>PUT</option>
                  <option>PATCH</option>
                  <option>DELETE</option>
                  <option>SOAP</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <label class="form-label">Path</label>
              <input v-model="testForm.path" class="form-control text-mono" placeholder="/aiservice/1.0.1/...">
            </div>
          </div>

          <!-- Section: Test request -->
          <div class="er-section">
            <div class="er-section-title">
              <span class="er-section-num">3</span> Test request
            </div>
            <div class="form-row">
              <label class="form-label">Query params override (JSON, optional)</label>
              <textarea v-model="testForm.queryOverrideJson" class="form-control text-mono" rows="3" placeholder="Leave empty to use the endpoint’s query_params_template"></textarea>
              <div class="form-help">Values may use <code v-pre>{{ input.field }}</code> for substitution.</div>
            </div>
            <div class="form-row">
              <label class="form-label">Input data (JSON)</label>
              <textarea v-model="testForm.inputJson" class="form-control text-mono" rows="5"></textarea>
            </div>
            <div class="form-row er-mode-toggle">
              <label class="er-toggle" :class="{ 'er-toggle-active': testForm.realHttp }">
                <input v-model="testForm.realHttp" type="checkbox">
                <span class="er-toggle-dot" />
                <span class="er-toggle-label">
                  <strong>{{ testForm.realHttp ? 'Real HTTP' : 'Simulated' }}</strong>
                  <small>{{ testForm.realHttp ? 'Calls the URL — uses real auth.' : 'Mocks the response — no network call.' }}</small>
                </span>
              </label>
            </div>
          </div>

          <!-- Section: Last test result -->
          <div v-if="testResult" class="er-section er-result">
            <div class="er-section-title">
              <span class="er-section-num er-section-num-result">4</span> Last test
              <span class="er-result-status" :class="testResult.status === 'ok' ? 'er-result-ok' : 'er-result-fail'">
                <span class="er-result-dot" />
                {{ testResult.status_code }} · {{ testResult.latency_ms }} ms · {{ testResult.mode }}
              </span>
            </div>

            <div v-if="testResult.curl_command" class="er-terminal">
              <div class="er-terminal-bar">
                <span class="er-dots"><i/><i/><i/></span>
                <span class="er-terminal-title">cURL</span>
                <button type="button" class="btn btn-sm" @click="copyText(testResult.curl_command)">Copy</button>
              </div>
              <pre class="er-terminal-body">{{ testResult.curl_command }}</pre>
            </div>

            <div v-if="testResult.request_headers && Object.keys(testResult.request_headers).length" class="er-terminal">
              <div class="er-terminal-bar">
                <span class="er-dots"><i/><i/><i/></span>
                <span class="er-terminal-title">Request headers (masked)</span>
              </div>
              <pre class="er-terminal-body">{{ JSON.stringify(testResult.request_headers, null, 2) }}</pre>
            </div>

            <div v-if="testResult.response_headers && testResult.mode === 'http'" class="er-terminal">
              <div class="er-terminal-bar">
                <span class="er-dots"><i/><i/><i/></span>
                <span class="er-terminal-title">Response headers</span>
              </div>
              <pre class="er-terminal-body">{{ JSON.stringify(testResult.response_headers, null, 2) }}</pre>
            </div>

            <div class="er-terminal er-terminal-out">
              <div class="er-terminal-bar">
                <span class="er-dots"><i/><i/><i/></span>
                <span class="er-terminal-title">Output</span>
                <button type="button" class="btn btn-sm" @click="copyText(displayOutput(testResult))">Copy</button>
              </div>
              <pre class="er-terminal-body er-terminal-out-body">{{ displayOutput(testResult) }}</pre>
            </div>
          </div>
        </div>

        <div class="modal-footer er-footer">
          <button class="btn" @click="closeTestModal">Close</button>
          <button class="btn" :disabled="savingRegistry" @click="saveRegistry">
            {{ savingRegistry ? 'Saving…' : 'Save to registry' }}
          </button>
          <button class="btn btn-primary er-run-btn" :disabled="testing" @click="runTest">
            <span class="er-run-icon">▶</span>
            {{ testing ? 'Running…' : (testForm.realHttp ? 'Run real test' : 'Run simulated') }}
          </button>
        </div>
      </div>
    </div>

    <!-- (styles below) -->

    <!-- Create modal -->
    <div v-if="showCreate" class="modal-backdrop" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">Register endpoint</div>
          <button class="modal-close" @click="showCreate = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row two-col">
            <div>
              <label class="form-label">Name</label>
              <input v-model="draft.name" class="form-control" placeholder="Customer Lookup">
            </div>
            <div>
              <label class="form-label">Method</label>
              <select v-model="draft.method" class="form-control">
                <option>GET</option><option>POST</option><option>PUT</option>
                <option>PATCH</option><option>DELETE</option><option>SOAP</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <label class="form-label">Description</label>
            <input v-model="draft.description" class="form-control">
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Base URL</label>
              <input v-model="draft.base_url" class="form-control" placeholder="https://api.example.com">
            </div>
            <div>
              <label class="form-label">Path</label>
              <input v-model="draft.path" class="form-control" placeholder="/v1/users/{{ input.id }}">
            </div>
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Auth type</label>
              <select v-model="draft.auth_type" class="form-control">
                <option>none</option><option>api_key</option><option>bearer</option>
                <option>oauth</option><option>basic</option><option>mtls</option>
                <option>internal</option>
              </select>
            </div>
            <div>
              <label class="form-label">Environment</label>
              <select v-model="draft.environment" class="form-control">
                <option>dev</option>
                <option>qa</option>
                <option>prod</option>
                <option>test</option>
                <option>uat</option>
              </select>
            </div>
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Timeout (s)</label>
              <input v-model.number="draft.timeout_seconds" type="number" class="form-control">
            </div>
            <div>
              <label class="form-label">Est. cost per call</label>
              <input v-model.number="draft.estimated_cost_per_call" type="number" step="0.001" class="form-control">
            </div>
          </div>
          <div class="form-row">
            <label class="form-label">Body template (JSON / XML)</label>
            <textarea v-model="draft.body_template" class="form-control" rows="3"></textarea>
            <div class="form-help">Use <code v-pre>{{ input.field }}</code> for runtime substitution.</div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showCreate = false">Cancel</button>
          <button class="btn btn-primary" :disabled="saving || !draft.name || !draft.base_url" @click="create">
            {{ saving ? 'Saving…' : 'Register' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ---------- HTTP method badge ---------- */
.method-badge {
  display: inline-block;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 3px 8px;
  border-radius: 6px;
  color: var(--m, #374151);
  background: color-mix(in srgb, var(--m, #6b7280) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--m, #6b7280) 35%, transparent);
}

/* ---------- Endpoint Review Modal ---------- */
.endpoint-review-modal {
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
}

.er-hero {
  position: relative;
  padding: 22px 24px 20px;
  background: linear-gradient(135deg,
    color-mix(in srgb, var(--m) 18%, #0f172a) 0%,
    #0f172a 65%,
    #0b1a32 100%);
  color: #f1f5f9;
  border-bottom: 3px solid var(--m);
}
.er-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 20% 0%, color-mix(in srgb, var(--m) 30%, transparent), transparent 40%),
    radial-gradient(circle at 80% 100%, color-mix(in srgb, var(--m) 20%, transparent), transparent 50%);
  pointer-events: none;
}
.er-hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  z-index: 1;
}
.er-eyebrow {
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: color-mix(in srgb, var(--m) 60%, #cbd5e1);
  font-weight: 600;
}
.er-name {
  margin: 6px 0 14px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #f8fafc;
  position: relative;
  z-index: 1;
}
.er-url {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 8px 12px;
  border-radius: 8px;
  position: relative;
  z-index: 1;
  min-height: 40px;
}
.er-url .method-badge {
  background: color-mix(in srgb, var(--m) 25%, transparent);
  color: color-mix(in srgb, var(--m) 80%, white);
  border-color: color-mix(in srgb, var(--m) 50%, transparent);
}
.er-url-text {
  flex: 1;
  font-size: 13px;
  color: #94a3b8;
  word-break: break-all;
}
.er-url-path { color: #f1f5f9; font-weight: 600; }

.er-close {
  position: absolute;
  top: 12px;
  right: 14px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  width: 30px;
  height: 30px;
  border-radius: 8px;
  color: #cbd5e1;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  z-index: 2;
  transition: all 0.15s;
}
.er-close:hover {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

/* ---------- Body sections ---------- */
.er-body {
  padding: 20px 24px;
  background: #f8fafc;
}
.er-section {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px 18px;
  margin-bottom: 14px;
}
.er-section:last-child { margin-bottom: 0; }
.er-section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #111827;
  margin-bottom: 12px;
}
.er-section-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: linear-gradient(135deg, #60a5fa, #a78bfa);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.er-section-num-result {
  background: linear-gradient(135deg, #10b981, #22d3ee);
}
.er-help {
  font-size: 12.5px;
  color: #6b7280;
  margin: 0 0 4px;
  line-height: 1.5;
}

/* ---------- Mode toggle (real / simulated) ---------- */
.er-mode-toggle { margin-top: 4px; margin-bottom: 0; }
.er-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  background: #f9fafb;
  transition: all 0.15s;
}
.er-toggle input { display: none; }
.er-toggle-dot {
  width: 36px;
  height: 20px;
  border-radius: 999px;
  background: #cbd5e1;
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}
.er-toggle-dot::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform 0.2s;
}
.er-toggle-active {
  border-color: #fb923c;
  background: color-mix(in srgb, #fb923c 8%, white);
}
.er-toggle-active .er-toggle-dot { background: #fb923c; }
.er-toggle-active .er-toggle-dot::after { transform: translateX(16px); }
.er-toggle-label {
  display: flex;
  flex-direction: column;
  font-size: 13px;
}
.er-toggle-label small { color: #6b7280; font-size: 11.5px; margin-top: 2px; }

/* ---------- Result section ---------- */
.er-result { background: #f1f5f9; border-color: #cbd5e1; }
.er-result-status {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  text-transform: none;
  letter-spacing: 0;
}
.er-result-ok { background: rgba(16, 185, 129, 0.12); color: #047857; }
.er-result-fail { background: rgba(239, 68, 68, 0.12); color: #b91c1c; }
.er-result-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 6px currentColor;
}

/* ---------- Terminal-style code panels ---------- */
.er-terminal {
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #1e293b;
  margin-bottom: 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.er-terminal:last-child { margin-bottom: 0; }
.er-terminal-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px 7px 14px;
  background: #1e293b;
  color: #cbd5e1;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.er-terminal-bar .btn {
  margin-left: auto;
  padding: 3px 10px;
  font-size: 11px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #f1f5f9;
}
.er-terminal-bar .btn:hover { background: rgba(255, 255, 255, 0.2); }
.er-dots {
  display: inline-flex;
  gap: 4px;
}
.er-dots i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #475569;
}
.er-dots i:nth-child(1) { background: #ef4444; }
.er-dots i:nth-child(2) { background: #f59e0b; }
.er-dots i:nth-child(3) { background: #10b981; }
.er-terminal-title {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: #94a3b8;
  font-weight: 500;
}
.er-terminal-body {
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px 14px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  line-height: 1.55;
  max-height: 260px;
  overflow: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.er-terminal-out-body {
  background: #0a1224;
  max-height: 360px;
  color: #d1fae5;
}

/* ---------- Footer ---------- */
.er-footer {
  flex-wrap: wrap;
  gap: 8px;
  background: white;
  padding: 14px 24px;
}
.er-run-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.er-run-icon {
  display: inline-flex;
  font-size: 10px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.25);
  color: white;
}

@media (max-width: 600px) {
  .er-hero { padding: 18px 18px 16px; }
  .er-name { font-size: 18px; }
  .er-body { padding: 14px 14px; }
  .er-section { padding: 12px 14px; }
}
</style>
