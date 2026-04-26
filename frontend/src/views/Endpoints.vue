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
            <td><span class="text-mono">{{ ep.method }}</span></td>
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
    <div v-if="showTestModal && testEndpoint" class="modal-backdrop" @click.self="closeTestModal">
      <div class="modal" :style="{ maxWidth: testResult ? 'min(960px, 96vw)' : '640px' }">
        <div class="modal-header">
          <div class="modal-title">Review — {{ testEndpoint.name }}</div>
          <button class="modal-close" @click="closeTestModal">×</button>
        </div>
        <div class="modal-body">
          <p class="section-subtitle mb-2">
            <strong>Settings environment</strong> loads host/token from Environment Settings (DEV/QA/PROD).
            <strong>Registry environment</strong> is the label stored on this endpoint row.
          </p>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Settings environment (OUC host, token, …)</label>
              <select v-model="testForm.settingsEnvironment" class="form-control">
                <option value="dev">DEV</option>
                <option value="qa">QA</option>
                <option value="prod">PROD</option>
              </select>
            </div>
            <div>
              <label class="form-label">Registry environment (saved on endpoint)</label>
              <select v-model="testForm.registryEnvironment" class="form-control">
                <option value="dev">dev</option>
                <option value="qa">qa</option>
                <option value="prod">prod</option>
                <option value="test">test</option>
                <option value="uat">uat</option>
              </select>
            </div>
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
          <div class="form-row">
            <label class="form-label">Query params override (JSON object, optional)</label>
            <textarea v-model="testForm.queryOverrideJson" class="form-control text-mono" rows="3" placeholder="Leave empty to use the endpoint’s query_params_template"></textarea>
            <div class="form-help">Values may use <code v-pre>{{ input.field }}</code> for substitution.</div>
          </div>
          <div class="form-row">
            <label class="form-label">Input data (JSON)</label>
            <textarea v-model="testForm.inputJson" class="form-control text-mono" rows="5"></textarea>
          </div>
          <div class="form-row">
            <label class="text-sm">
              <input v-model="testForm.realHttp" type="checkbox"> Real HTTP (call the URL; unchecked = simulated)
            </label>
          </div>
          <div v-if="testResult" class="endpoint-test-verbose border-top" style="margin-top: 16px; padding-top: 16px; max-height: 55vh; overflow: auto">
            <div class="flex-between" style="align-items: center; margin-bottom: 8px">
              <strong>Last test</strong>
              <span :class="`pill pill-${testResult.status === 'ok' ? 'success' : 'failed'}`">
                {{ testResult.status_code }} · {{ testResult.latency_ms }} ms · {{ testResult.mode }}
              </span>
            </div>
            <div v-if="testResult.curl_command" class="form-row" style="margin-bottom: 12px">
              <div class="flex-between" style="align-items: center; margin-bottom: 6px">
                <label class="form-label" style="margin: 0">cURL</label>
                <button type="button" class="btn btn-sm" @click="copyText(testResult.curl_command)">Copy cURL</button>
              </div>
              <pre class="endpoint-pre text-sm">{{ testResult.curl_command }}</pre>
            </div>
            <div v-if="testResult.request_headers && Object.keys(testResult.request_headers).length" class="form-row" style="margin-bottom: 12px">
              <label class="form-label">Request headers (masked)</label>
              <pre class="endpoint-pre text-sm">{{ JSON.stringify(testResult.request_headers, null, 2) }}</pre>
            </div>
            <div v-if="testResult.response_headers && testResult.mode === 'http'" class="form-row" style="margin-bottom: 12px">
              <label class="form-label">Response headers</label>
              <pre class="endpoint-pre text-sm">{{ JSON.stringify(testResult.response_headers, null, 2) }}</pre>
            </div>
            <div class="form-row">
              <label class="form-label">Output</label>
              <pre class="endpoint-pre endpoint-pre-out text-sm">{{ displayOutput(testResult) }}</pre>
            </div>
          </div>
        </div>
        <div class="modal-footer" style="flex-wrap: wrap; gap: 8px">
          <button class="btn" @click="closeTestModal">Close</button>
          <button class="btn" :disabled="savingRegistry" @click="saveRegistry">
            {{ savingRegistry ? 'Saving…' : 'Save to registry' }}
          </button>
          <button class="btn btn-primary" :disabled="testing" @click="runTest">
            {{ testing ? 'Running…' : (testForm.realHttp ? 'Run real test' : 'Run simulated test') }}
          </button>
        </div>
      </div>
    </div>

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
