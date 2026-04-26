<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { agentsApi, modelsApi } from '../api.js'

const router = useRouter()
const agents = ref([])
const models = ref([])
const loading = ref(true)
const error = ref(null)
const filterStatus = ref('')
const filterEnv = ref('')
const showCreate = ref(false)
const saving = ref(false)

const draft = ref({
  name: '', description: '', objective: '', business_domain: '',
  environment: 'dev', system_prompt: '', business_instructions: '',
  constraints: '', response_format: 'json', default_model_id: null,
})

const filtered = computed(() => agents.value)

async function load() {
  loading.value = true
  error.value = null
  try {
    const params = {}
    if (filterStatus.value) params.status_filter = filterStatus.value
    if (filterEnv.value) params.environment = filterEnv.value
    const [a, m] = await Promise.all([agentsApi.list(params), modelsApi.list()])
    agents.value = a
    models.value = m
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function createAgent() {
  saving.value = true
  try {
    const created = await agentsApi.create(draft.value)
    showCreate.value = false
    draft.value = {
      name: '', description: '', objective: '', business_domain: '',
      environment: 'dev', system_prompt: '', business_instructions: '',
      constraints: '', response_format: 'json', default_model_id: null,
    }
    router.push(`/agents/${created.id}`)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

async function clone(id) {
  await agentsApi.clone(id)
  await load()
}

async function remove(id) {
  if (!confirm('Delete this agent and all its workflows / versions?')) return
  await agentsApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <div>
        <h2 class="section-title">Agents</h2>
        <p class="section-subtitle">Reusable agent definitions: prompts, schemas, workflows, models.</p>
      </div>
      <div class="toolbar-filters">
        <select class="form-control" v-model="filterStatus" @change="load">
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="test">Test</option>
          <option value="review">Review</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
        <select class="form-control" v-model="filterEnv" @change="load">
          <option value="">All environments</option>
          <option value="dev">Dev</option>
          <option value="test">Test</option>
          <option value="uat">UAT</option>
          <option value="prod">Prod</option>
        </select>
        <button class="btn btn-primary" @click="showCreate = true">+ New Agent</button>
      </div>
    </div>

    <div v-if="error" class="error-banner mb-4">{{ error }}</div>
    <div v-if="loading" class="loading">Loading…</div>

    <div v-else-if="!filtered.length" class="card">
      <div class="empty-state">
        <h3>No agents yet</h3>
        <p>Create your first agent definition to get started.</p>
      </div>
    </div>

    <div v-else class="card">
      <table class="table">
        <thead>
          <tr>
            <th>Name</th><th>Domain</th><th>Env</th><th>Status</th>
            <th>Version</th><th>Updated</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in filtered" :key="a.id">
            <td>
              <router-link :to="`/agents/${a.id}`"><strong>{{ a.name }}</strong></router-link>
              <div class="text-sm text-muted">{{ a.objective || a.description || '—' }}</div>
            </td>
            <td>{{ a.business_domain || '—' }}</td>
            <td><span class="text-mono">{{ a.environment }}</span></td>
            <td><span :class="`pill pill-${a.status}`">{{ a.status }}</span></td>
            <td>v{{ a.current_version }}</td>
            <td class="text-sm text-muted">{{ new Date(a.updated_at).toLocaleDateString() }}</td>
            <td class="table-actions">
              <button class="btn btn-sm" @click="clone(a.id)">Clone</button>
              <button class="btn btn-sm btn-danger" @click="remove(a.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="modal-backdrop" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">New agent definition</div>
          <button class="modal-close" @click="showCreate = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row two-col">
            <div>
              <label class="form-label">Name</label>
              <input v-model="draft.name" class="form-control" placeholder="Customer Support Triage">
            </div>
            <div>
              <label class="form-label">Business domain</label>
              <input v-model="draft.business_domain" class="form-control" placeholder="customer_support">
            </div>
          </div>
          <div class="form-row">
            <label class="form-label">Description</label>
            <input v-model="draft.description" class="form-control">
          </div>
          <div class="form-row">
            <label class="form-label">Objective</label>
            <input v-model="draft.objective" class="form-control" placeholder="Classify request, fetch data, return recommendation">
          </div>
          <div class="form-row two-col">
            <div>
              <label class="form-label">Environment</label>
              <select v-model="draft.environment" class="form-control">
                <option value="dev">Dev</option>
                <option value="test">Test</option>
                <option value="uat">UAT</option>
                <option value="prod">Prod</option>
              </select>
            </div>
            <div>
              <label class="form-label">Default model</label>
              <select v-model="draft.default_model_id" class="form-control">
                <option :value="null">— none —</option>
                <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }}</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <label class="form-label">System prompt</label>
            <textarea v-model="draft.system_prompt" class="form-control"
              placeholder="You are a..." rows="4"></textarea>
          </div>
          <div class="form-row">
            <label class="form-label">Business instructions</label>
            <textarea v-model="draft.business_instructions" class="form-control" rows="3"></textarea>
          </div>
          <div class="form-row">
            <label class="form-label">Constraints</label>
            <textarea v-model="draft.constraints" class="form-control" rows="2"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showCreate = false">Cancel</button>
          <button class="btn btn-primary" :disabled="saving || !draft.name" @click="createAgent">
            {{ saving ? 'Creating…' : 'Create' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
