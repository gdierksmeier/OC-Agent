<script setup>
import { ref, onMounted } from 'vue'
import { modelsApi } from '../api.js'

const models = ref([])
const loading = ref(true)
const error = ref(null)
const showCreate = ref(false)
const saving = ref(false)

const blank = () => ({
  name: '', provider: 'openai', model_identifier: '', model_type: 'cloud',
  context_window: 8192, max_tokens: 2048,
  temperature_default: 0.7, top_p_default: 1.0,
  cost_per_1k_input_tokens: 0, cost_per_1k_output_tokens: 0,
  supports_tools: false, handles_sensitive_data: false,
  routing_priority: 100, status: 'active',
})
const draft = ref(blank())

async function load() {
  loading.value = true
  try {
    models.value = await modelsApi.list()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function create() {
  saving.value = true
  try {
    await modelsApi.create(draft.value)
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
  if (!confirm('Delete this model?')) return
  await modelsApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <div>
        <h2 class="section-title">AI Models</h2>
        <p class="section-subtitle">Configured providers, parameters, costs, and routing priorities.</p>
      </div>
      <button class="btn btn-primary" @click="showCreate = true">+ Add model</button>
    </div>

    <div v-if="error" class="error-banner mb-4">{{ error }}</div>
    <div v-if="loading" class="loading">Loading…</div>

    <div v-else-if="!models.length" class="card">
      <div class="empty-state">
        <h3>No models configured</h3>
        <p>Add an LLM provider to make it available to agents.</p>
      </div>
    </div>

    <div v-else class="card">
      <table class="table">
        <thead>
          <tr>
            <th>Name</th><th>Provider</th><th>Type</th><th>Context</th>
            <th>Cost (in/out per 1K)</th><th>Priority</th><th>Status</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in models" :key="m.id">
            <td>
              <strong>{{ m.name }}</strong>
              <div class="text-sm text-muted text-mono">{{ m.model_identifier }}</div>
            </td>
            <td>{{ m.provider }}</td>
            <td>
              <span class="text-mono text-sm">{{ m.model_type }}</span>
              <span v-if="m.handles_sensitive_data" class="pill pill-active" style="margin-left:6px">sensitive-ok</span>
            </td>
            <td class="text-mono text-sm">{{ m.context_window.toLocaleString() }}</td>
            <td class="text-mono text-sm">
              ${{ m.cost_per_1k_input_tokens }} / ${{ m.cost_per_1k_output_tokens }}
            </td>
            <td>{{ m.routing_priority }}</td>
            <td><span :class="`pill pill-${m.status === 'active' ? 'active' : 'inactive'}`">{{ m.status }}</span></td>
            <td class="table-actions">
              <button class="btn btn-sm btn-danger" @click="remove(m.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="modal-backdrop" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">Add AI model</div>
          <button class="modal-close" @click="showCreate = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row two-col">
            <div>
              <label class="form-label">Name</label>
              <input v-model="draft.name" class="form-control" placeholder="GPT-4o (cloud)">
            </div>
            <div>
              <label class="form-label">Provider</label>
              <select v-model="draft.provider" class="form-control">
                <option>openai</option><option>anthropic</option><option>google</option>
                <option>local</option><option>private</option><option>custom</option>
              </select>
            </div>
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Model identifier</label>
              <input v-model="draft.model_identifier" class="form-control" placeholder="gpt-4o">
            </div>
            <div>
              <label class="form-label">Type</label>
              <select v-model="draft.model_type" class="form-control">
                <option>cloud</option><option>local</option>
                <option>private</option><option>specialized</option>
              </select>
            </div>
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Context window</label>
              <input v-model.number="draft.context_window" type="number" class="form-control">
            </div>
            <div>
              <label class="form-label">Max output tokens</label>
              <input v-model.number="draft.max_tokens" type="number" class="form-control">
            </div>
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Temperature</label>
              <input v-model.number="draft.temperature_default" type="number" step="0.1" class="form-control">
            </div>
            <div>
              <label class="form-label">Top-p</label>
              <input v-model.number="draft.top_p_default" type="number" step="0.05" class="form-control">
            </div>
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Cost per 1K input tokens ($)</label>
              <input v-model.number="draft.cost_per_1k_input_tokens" type="number" step="0.0001" class="form-control">
            </div>
            <div>
              <label class="form-label">Cost per 1K output tokens ($)</label>
              <input v-model.number="draft.cost_per_1k_output_tokens" type="number" step="0.0001" class="form-control">
            </div>
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Routing priority</label>
              <input v-model.number="draft.routing_priority" type="number" class="form-control">
              <div class="form-help">Lower = preferred</div>
            </div>
            <div>
              <label class="form-label">Status</label>
              <select v-model="draft.status" class="form-control">
                <option>active</option><option>experimental</option><option>deprecated</option>
              </select>
            </div>
          </div>
          <div class="form-row two-col">
            <label class="text-sm">
              <input type="checkbox" v-model="draft.supports_tools"> Supports tool calls
            </label>
            <label class="text-sm">
              <input type="checkbox" v-model="draft.handles_sensitive_data"> Handles sensitive data
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showCreate = false">Cancel</button>
          <button class="btn btn-primary" :disabled="saving || !draft.name || !draft.model_identifier" @click="create">
            {{ saving ? 'Saving…' : 'Add' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
