<script setup>
import { ref, onMounted } from 'vue'
import { promptsApi } from '../api.js'

const prompts = ref([])
const loading = ref(true)
const error = ref(null)
const showCreate = ref(false)
const editing = ref(null)
const saving = ref(false)
const filterCategory = ref('')

const blank = () => ({
  name: '', description: '', template: '',
  variables: [], category: 'task', status: 'draft',
})
const draft = ref(blank())

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filterCategory.value) params.category = filterCategory.value
    prompts.value = await promptsApi.list(params)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function openEdit(p) {
  editing.value = p.id
  draft.value = { ...p }
  showCreate.value = true
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await promptsApi.update(editing.value, draft.value)
    } else {
      await promptsApi.create(draft.value)
    }
    closeModal()
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

function closeModal() {
  showCreate.value = false
  editing.value = null
  draft.value = blank()
}

async function remove(id) {
  if (!confirm('Delete this prompt?')) return
  await promptsApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <div>
        <h2 class="section-title">Prompt Library</h2>
        <p class="section-subtitle">Reusable prompt templates with variables and version control.</p>
      </div>
      <div class="toolbar-filters">
        <select class="form-control" v-model="filterCategory" @change="load">
          <option value="">All categories</option>
          <option value="system">System</option>
          <option value="task">Task</option>
          <option value="validation">Validation</option>
          <option value="final">Final</option>
        </select>
        <button class="btn btn-primary" @click="showCreate = true">+ New prompt</button>
      </div>
    </div>

    <div v-if="error" class="error-banner mb-4">{{ error }}</div>
    <div v-if="loading" class="loading">Loading…</div>

    <div v-else-if="!prompts.length" class="card">
      <div class="empty-state">
        <h3>No prompts yet</h3>
      </div>
    </div>

    <div v-else class="card">
      <table class="table">
        <thead>
          <tr>
            <th>Name</th><th>Category</th><th>Variables</th><th>Version</th>
            <th>Status</th><th>Updated</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in prompts" :key="p.id">
            <td>
              <strong>{{ p.name }}</strong>
              <div class="text-sm text-muted">{{ p.description || '—' }}</div>
            </td>
            <td><span class="text-mono text-sm">{{ p.category }}</span></td>
            <td>{{ p.variables?.length || 0 }}</td>
            <td>v{{ p.version }}</td>
            <td><span :class="`pill pill-${p.status}`">{{ p.status }}</span></td>
            <td class="text-sm text-muted">{{ new Date(p.updated_at).toLocaleDateString() }}</td>
            <td class="table-actions">
              <button class="btn btn-sm" @click="openEdit(p)">Edit</button>
              <button class="btn btn-sm btn-danger" @click="remove(p.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create / edit modal -->
    <div v-if="showCreate" class="modal-backdrop" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">{{ editing ? 'Edit prompt' : 'New prompt' }}</div>
          <button class="modal-close" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row two-col">
            <div>
              <label class="form-label">Name</label>
              <input v-model="draft.name" class="form-control">
            </div>
            <div>
              <label class="form-label">Category</label>
              <select v-model="draft.category" class="form-control">
                <option>system</option><option>task</option>
                <option>validation</option><option>final</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <label class="form-label">Description</label>
            <input v-model="draft.description" class="form-control">
          </div>
          <div class="form-row">
            <label class="form-label">Template</label>
            <textarea v-model="draft.template" class="form-control" rows="8"></textarea>
            <div class="form-help">Use <code v-pre>{{ variable.path }}</code> for runtime substitution.</div>
          </div>
          <div class="form-row">
            <label class="form-label">Status</label>
            <select v-model="draft.status" class="form-control">
              <option>draft</option><option>review</option>
              <option>published</option><option>archived</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="closeModal">Cancel</button>
          <button class="btn btn-primary" :disabled="saving || !draft.name || !draft.template" @click="save">
            {{ saving ? 'Saving…' : (editing ? 'Save' : 'Create') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
