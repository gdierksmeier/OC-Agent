<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { agentsApi, endpointsApi, executionsApi, modelsApi, promptsApi, workflowsApi } from '../api.js'

const props = defineProps({ id: { type: [String, Number], required: true } })
const route = useRoute()
const router = useRouter()

const TAB_KEYS = ['config', 'workflow', 'run', 'versions']

function applyQueryTab() {
  const t = route.query.tab
  if (typeof t === 'string' && TAB_KEYS.includes(t)) {
    tab.value = t
  }
}

const agent = ref(null)
const versions = ref([])
const models = ref([])
const endpoints = ref([])
const prompts = ref([])
const loading = ref(true)
const error = ref(null)
const tab = ref('config')
const saving = ref(false)
const savingWorkflowId = ref(null)
const workflowDrafts = ref({})

const runInput = ref('{\n  "customer_id": "C-1234",\n  "question": "Where is my order?"\n}')
const runResult = ref(null)
const running = ref(false)

async function load() {
  loading.value = true
  try {
    const [a, v, m] = await Promise.all([
      agentsApi.get(props.id),
      agentsApi.versions(props.id),
      modelsApi.list(),
    ])
    const [eps, prs] = await Promise.all([
      endpointsApi.list(),
      promptsApi.list(),
    ])
    agent.value = a
    versions.value = v
    models.value = m
    endpoints.value = eps
    prompts.value = prs
    workflowDrafts.value = Object.fromEntries(
      (a.workflows || []).map(wf => [
        wf.id,
        {
          name: wf.name,
          description: wf.description || '',
          status: wf.status,
          tasks: (wf.tasks || []).map(t => ({
            name: t.name,
            task_type: t.task_type,
            order_index: t.order_index,
            timeout_seconds: t.timeout_seconds,
            retry_count: t.retry_count,
            error_handling: t.error_handling,
            endpoint_id: t.endpoint_id,
            model_id: t.model_id,
            prompt_id: t.prompt_id,
            config: t.config || {},
            depends_on: Array.isArray(t.depends_on) ? t.depends_on : [],
            preconditions: t.preconditions || '',
            postconditions: t.postconditions || '',
            configJson: JSON.stringify(t.config || {}, null, 2),
            dependsOnJson: JSON.stringify(Array.isArray(t.depends_on) ? t.depends_on : [], null, 2),
          })),
        },
      ])
    )
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
    applyQueryTab()
  }
}

function addWorkflowTask(workflowId) {
  workflowDrafts.value[workflowId].tasks.push({
    name: '',
    task_type: 'call_endpoint',
    order_index: workflowDrafts.value[workflowId].tasks.length + 1,
    timeout_seconds: 30,
    retry_count: 0,
    error_handling: 'fail',
    endpoint_id: null,
    model_id: null,
    prompt_id: null,
    config: {},
    depends_on: [],
    preconditions: '',
    postconditions: '',
    configJson: '{}',
    dependsOnJson: '[]',
  })
}

function removeWorkflowTask(workflowId, index) {
  workflowDrafts.value[workflowId].tasks.splice(index, 1)
}

async function saveWorkflow(workflowId) {
  savingWorkflowId.value = workflowId
  try {
    const draft = workflowDrafts.value[workflowId]
    const parsedTasks = draft.tasks.map((t, idx) => {
      let parsedConfig = {}
      let parsedDependsOn = []
      try {
        parsedConfig = t.configJson?.trim() ? JSON.parse(t.configJson) : {}
      } catch {
        throw new Error(`Task #${idx + 1} has invalid JSON in config`)
      }
      try {
        parsedDependsOn = t.dependsOnJson?.trim() ? JSON.parse(t.dependsOnJson) : []
      } catch {
        throw new Error(`Task #${idx + 1} has invalid JSON in depends_on`)
      }
      if (!Array.isArray(parsedDependsOn)) {
        throw new Error(`Task #${idx + 1} depends_on must be a JSON array`)
      }
      return {
        name: t.name,
        task_type: t.task_type,
        order_index: Number.isFinite(t.order_index) ? t.order_index : idx + 1,
        timeout_seconds: t.timeout_seconds ?? 30,
        retry_count: t.retry_count ?? 0,
        error_handling: t.error_handling || 'fail',
        endpoint_id: t.endpoint_id || null,
        model_id: t.model_id || null,
        prompt_id: t.prompt_id || null,
        config: parsedConfig,
        depends_on: parsedDependsOn,
        preconditions: t.preconditions || null,
        postconditions: t.postconditions || null,
      }
    })
    const payload = {
      name: draft.name,
      description: draft.description,
      status: draft.status,
      tasks: parsedTasks,
    }
    await workflowsApi.update(workflowId, payload)
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    savingWorkflowId.value = null
  }
}

async function save() {
  saving.value = true
  try {
    const payload = {
      name: agent.value.name,
      description: agent.value.description,
      objective: agent.value.objective,
      business_domain: agent.value.business_domain,
      environment: agent.value.environment,
      system_prompt: agent.value.system_prompt,
      business_instructions: agent.value.business_instructions,
      constraints: agent.value.constraints,
      response_format: agent.value.response_format,
      fallback_behavior: agent.value.fallback_behavior,
      default_model_id: agent.value.default_model_id,
      input_schema: agent.value.input_schema,
      output_schema: agent.value.output_schema,
    }
    await agentsApi.update(props.id, payload)
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

async function transition(newStatus) {
  await agentsApi.transition(props.id, newStatus)
  await load()
}

async function snapshot() {
  const note = prompt('Changelog note (optional):') || ''
  await agentsApi.snapshot(props.id, note)
  await load()
}

async function runAgent() {
  running.value = true
  runResult.value = null
  try {
    const input = JSON.parse(runInput.value)
    runResult.value = await executionsApi.run(props.id, { input_data: input })
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    running.value = false
  }
}

onMounted(load)

watch(
  () => route.query.tab,
  () => {
    if (!agent.value) return
    applyQueryTab()
  }
)
</script>

<template>
  <div v-if="loading" class="loading">Loading agent…</div>
  <div v-else-if="error" class="error-banner">{{ error }}</div>
  <div v-else-if="agent">
    <!-- Header -->
    <div class="toolbar">
      <div>
        <h2 class="section-title">{{ agent.name }}</h2>
        <p class="section-subtitle">
          <span :class="`pill pill-${agent.status}`">{{ agent.status }}</span>
          <span class="text-mono ml-2" style="margin-left:10px">{{ agent.environment }}</span>
          <span class="ml-2 text-muted" style="margin-left:10px">v{{ agent.current_version }}</span>
          · {{ agent.business_domain || '—' }}
        </p>
      </div>
      <div class="toolbar-filters">
        <button class="btn" @click="router.push('/agents')">← Back</button>
        <button class="btn" @click="snapshot">Snapshot version</button>
        <select class="form-control" :value="agent.status" @change="(e) => transition(e.target.value)">
          <option value="draft">Draft</option>
          <option value="test">Test</option>
          <option value="review">Review</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
      </div>
    </div>

    <!-- Tab nav -->
    <div class="card mb-4">
      <div class="card-header" style="gap:0">
        <div style="display:flex; gap:0">
          <button class="btn btn-sm" :class="{'btn-primary': tab==='config'}" @click="router.replace({ query: { ...route.query, tab: 'config' } }); tab = 'config'">Configuration</button>
          <button class="btn btn-sm" :class="{'btn-primary': tab==='workflow'}" @click="router.replace({ query: { ...route.query, tab: 'workflow' } }); tab = 'workflow'">Workflow</button>
          <button class="btn btn-sm" :class="{'btn-primary': tab==='run'}" @click="router.replace({ query: { ...route.query, tab: 'run' } }); tab = 'run'">Run / Test</button>
          <button class="btn btn-sm" :class="{'btn-primary': tab==='versions'}" @click="router.replace({ query: { ...route.query, tab: 'versions' } }); tab = 'versions'">Versions</button>
        </div>
      </div>

      <!-- Configuration tab -->
      <div v-if="tab==='config'" class="card-body">
        <div class="form-row two-col">
          <div>
            <label class="form-label">Name</label>
            <input v-model="agent.name" class="form-control">
          </div>
          <div>
            <label class="form-label">Business domain</label>
            <input v-model="agent.business_domain" class="form-control">
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">Description</label>
          <input v-model="agent.description" class="form-control">
        </div>
        <div class="form-row">
          <label class="form-label">Objective</label>
          <input v-model="agent.objective" class="form-control">
        </div>
        <div class="form-row two-col">
          <div>
            <label class="form-label">Default model</label>
            <select v-model="agent.default_model_id" class="form-control">
              <option :value="null">— none —</option>
              <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }}</option>
            </select>
          </div>
          <div>
            <label class="form-label">Response format</label>
            <select v-model="agent.response_format" class="form-control">
              <option value="json">JSON</option>
              <option value="text">Text</option>
              <option value="markdown">Markdown</option>
            </select>
          </div>
        </div>
        <div class="form-row two-col">
          <div>
            <label class="form-label">Environment</label>
            <select v-model="agent.environment" class="form-control">
              <option value="dev">DEV</option>
              <option value="qa">QA</option>
              <option value="prod">PROD</option>
            </select>
          </div>
          <div />
        </div>
        <div class="form-row">
          <label class="form-label">System prompt</label>
          <textarea v-model="agent.system_prompt" class="form-control" rows="4"></textarea>
        </div>
        <div class="form-row">
          <label class="form-label">Business instructions</label>
          <textarea v-model="agent.business_instructions" class="form-control" rows="3"></textarea>
        </div>
        <div class="form-row">
          <label class="form-label">Constraints</label>
          <textarea v-model="agent.constraints" class="form-control" rows="2"></textarea>
        </div>
        <div class="form-row">
          <label class="form-label">Fallback behavior</label>
          <textarea v-model="agent.fallback_behavior" class="form-control" rows="2"></textarea>
        </div>
        <div class="text-right mt-3">
          <button class="btn btn-primary" :disabled="saving" @click="save">
            {{ saving ? 'Saving…' : 'Save changes' }}
          </button>
        </div>
      </div>

      <!-- Workflow tab -->
      <div v-if="tab==='workflow'" class="card-body">
        <div v-if="!agent.workflows.length" class="empty-state">
          <h3>No workflow attached</h3>
          <p>Attach a workflow from the <router-link to="/workflows">Workflows</router-link> page.</p>
        </div>
        <div v-for="wf in agent.workflows" :key="wf.id" class="mb-4">
          <div class="flex-between mb-2">
            <strong>{{ wf.name }}</strong>
            <span :class="`pill pill-${wf.status}`">{{ wf.status }}</span>
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Workflow name</label>
              <input v-model="workflowDrafts[wf.id].name" class="form-control">
            </div>
            <div>
              <label class="form-label">Status</label>
              <select v-model="workflowDrafts[wf.id].status" class="form-control">
                <option value="draft">Draft</option>
                <option value="test">Test</option>
                <option value="review">Review</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <label class="form-label">Workflow description</label>
            <input v-model="workflowDrafts[wf.id].description" class="form-control">
          </div>
          <table class="table">
            <thead>
              <tr><th>#</th><th>Task</th><th>Type</th><th>Timeout</th><th>Retry</th><th>Error policy</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="(t, idx) in workflowDrafts[wf.id].tasks" :key="`${wf.id}-${idx}`">
                <td><input v-model.number="t.order_index" type="number" class="form-control" style="width:80px"></td>
                <td><input v-model="t.name" class="form-control"></td>
                <td>
                  <select v-model="t.task_type" class="form-control">
                    <option value="classify">classify</option>
                    <option value="retrieve">retrieve</option>
                    <option value="call_endpoint">call_endpoint</option>
                    <option value="transform">transform</option>
                    <option value="call_model">call_model</option>
                    <option value="generate">generate</option>
                    <option value="validate">validate</option>
                    <option value="escalate">escalate</option>
                    <option value="approval">approval</option>
                  </select>
                </td>
                <td><input v-model.number="t.timeout_seconds" type="number" class="form-control" style="width:90px"></td>
                <td><input v-model.number="t.retry_count" type="number" class="form-control" style="width:90px"></td>
                <td>
                  <select v-model="t.error_handling" class="form-control">
                    <option value="fail">fail</option>
                    <option value="retry">retry</option>
                    <option value="fallback">fallback</option>
                    <option value="escalate">escalate</option>
                    <option value="continue">continue</option>
                  </select>
                </td>
                <td>
                  <button class="btn btn-sm btn-danger" @click="removeWorkflowTask(wf.id, idx)">Remove</button>
                </td>
              </tr>
              <tr v-for="(t, idx) in workflowDrafts[wf.id].tasks" :key="`${wf.id}-${idx}-advanced`">
                <td colspan="7">
                  <div class="grid grid-3 mb-2">
                    <div>
                      <label class="form-label">Endpoint</label>
                      <select v-model="t.endpoint_id" class="form-control">
                        <option :value="null">— none —</option>
                        <option v-for="ep in endpoints" :key="ep.id" :value="ep.id">{{ ep.name }} (#{{ ep.id }})</option>
                      </select>
                    </div>
                    <div>
                      <label class="form-label">Model</label>
                      <select v-model="t.model_id" class="form-control">
                        <option :value="null">— none —</option>
                        <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }} (#{{ m.id }})</option>
                      </select>
                    </div>
                    <div>
                      <label class="form-label">Prompt</label>
                      <select v-model="t.prompt_id" class="form-control">
                        <option :value="null">— none —</option>
                        <option v-for="p in prompts" :key="p.id" :value="p.id">{{ p.name }} (#{{ p.id }})</option>
                      </select>
                    </div>
                  </div>
                  <div class="form-row two-col">
                    <div>
                      <label class="form-label">Preconditions</label>
                      <input v-model="t.preconditions" class="form-control" placeholder="Optional">
                    </div>
                    <div>
                      <label class="form-label">Postconditions</label>
                      <input v-model="t.postconditions" class="form-control" placeholder="Optional">
                    </div>
                  </div>
                  <div class="form-row two-col">
                    <div>
                      <label class="form-label">Config (JSON)</label>
                      <textarea v-model="t.configJson" class="form-control text-mono" rows="4"></textarea>
                    </div>
                    <div>
                      <label class="form-label">Depends On (JSON array)</label>
                      <textarea v-model="t.dependsOnJson" class="form-control text-mono" rows="4"></textarea>
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="toolbar-filters">
            <button class="btn btn-sm" @click="addWorkflowTask(wf.id)">+ Add task</button>
            <button class="btn btn-sm btn-primary" :disabled="savingWorkflowId === wf.id" @click="saveWorkflow(wf.id)">
              {{ savingWorkflowId === wf.id ? 'Saving…' : 'Save workflow' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Run tab -->
      <div v-if="tab==='run'" class="card-body">
        <p class="section-subtitle">Run the agent with test input. Cost &amp; trace are recorded.</p>
        <div class="form-row">
          <label class="form-label">Input data (JSON)</label>
          <textarea v-model="runInput" class="form-control" rows="6"></textarea>
        </div>
        <button class="btn btn-success" :disabled="running" @click="runAgent">
          {{ running ? 'Running…' : '▶ Run agent' }}
        </button>

        <div v-if="runResult" class="mt-4">
          <div class="flex-between mb-2">
            <strong>Result</strong>
            <span :class="`pill pill-${runResult.status}`">{{ runResult.status }}</span>
          </div>
          <div class="grid grid-3 mb-3">
            <div class="kpi">
              <div class="kpi-label">Latency</div>
              <div class="kpi-value" style="font-size:18px">{{ runResult.total_latency_ms }} ms</div>
            </div>
            <div class="kpi">
              <div class="kpi-label">Cost</div>
              <div class="kpi-value" style="font-size:18px">${{ runResult.total_cost.toFixed(6) }}</div>
            </div>
            <div class="kpi">
              <div class="kpi-label">Tokens (in/out)</div>
              <div class="kpi-value" style="font-size:18px">
                {{ runResult.total_tokens_input }} / {{ runResult.total_tokens_output }}
              </div>
            </div>
          </div>
          <div class="json-view">{{ JSON.stringify(runResult.output_data, null, 2) }}</div>
          <router-link :to="`/executions/${runResult.id}`" class="btn mt-3 btn-sm">
            View full trace →
          </router-link>
        </div>
      </div>

      <!-- Versions tab -->
      <div v-if="tab==='versions'" class="card-body" style="padding:0">
        <div v-if="!versions.length" class="empty-state">
          <h3>No versions yet</h3>
          <p>Click "Snapshot version" to capture the current configuration.</p>
        </div>
        <table v-else class="table">
          <thead>
            <tr><th>Version</th><th>Status</th><th>Changelog</th><th>Created</th></tr>
          </thead>
          <tbody>
            <tr v-for="v in versions" :key="v.id">
              <td><strong>v{{ v.version }}</strong></td>
              <td><span :class="`pill pill-${v.status}`">{{ v.status }}</span></td>
              <td class="text-sm">{{ v.changelog || '—' }}</td>
              <td class="text-sm text-muted">{{ new Date(v.created_at).toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
