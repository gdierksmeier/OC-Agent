<script setup>
import { ref, onMounted } from 'vue'
import { environmentSettingsApi } from '../api.js'

const settings = ref([])
const environmentFilter = ref('all')
const loading = ref(true)
const error = ref(null)
const showCreate = ref(false)
const showEdit = ref(false)
const saving = ref(false)
const savingEdit = ref(false)

const blank = () => ({
  environment: 'dev',
  key: '',
  value: '',
  is_secret: false,
  description: '',
  is_active: true,
})

const draft = ref(blank())
const editDraft = ref(blank())
const editId = ref(null)

function isMaskedValue(s) {
  return s.is_secret && (s.value === '***MASKED***' || !s.value)
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (environmentFilter.value !== 'all') params.environment = environmentFilter.value
    settings.value = await environmentSettingsApi.list(params)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

async function createSetting() {
  saving.value = true
  try {
    await environmentSettingsApi.create(draft.value)
    draft.value = blank()
    showCreate.value = false
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

function openEdit(s) {
  error.value = null
  editId.value = s.id
  editDraft.value = {
    environment: s.environment,
    key: s.key,
    value: isMaskedValue(s) ? '' : s.value,
    is_secret: s.is_secret,
    description: s.description || '',
    is_active: s.is_active,
  }
  showEdit.value = true
}

function closeEdit() {
  showEdit.value = false
  editId.value = null
}

async function updateSetting() {
  if (editId.value == null) return
  savingEdit.value = true
  try {
    const d = editDraft.value
    const payload = {
      environment: d.environment,
      key: d.key,
      is_secret: d.is_secret,
      description: d.description || null,
      is_active: d.is_active,
    }
    if (d.is_secret) {
      if (d.value) {
        payload.value = d.value
      }
    } else {
      payload.value = d.value
    }
    await environmentSettingsApi.update(editId.value, payload)
    closeEdit()
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    savingEdit.value = false
  }
}

async function removeSetting(id) {
  if (!confirm('Delete this setting?')) return
  await environmentSettingsApi.remove(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <div>
        <h2 class="section-title">Environment Settings</h2>
        <p class="section-subtitle">Manage DEV / QA / PROD runtime settings such as OUC host, port, and tokens. Edit any row to update values, keys, or flags.</p>
      </div>
      <button class="btn btn-primary" @click="showCreate = true">+ Add setting</button>
    </div>

    <div class="card mb-4">
      <div class="form-row" style="max-width: 280px">
        <label class="form-label">Environment</label>
        <select v-model="environmentFilter" class="form-control" @change="load">
          <option value="all">All</option>
          <option value="dev">DEV</option>
          <option value="qa">QA</option>
          <option value="prod">PROD</option>
        </select>
      </div>
    </div>

    <div v-if="error" class="error-banner mb-4">{{ error }}</div>
    <div v-if="loading" class="loading">Loading…</div>

    <div v-else-if="!settings.length" class="card">
      <div class="empty-state">
        <h3>No settings found</h3>
        <p>Add environment-specific settings to configure runtime integrations.</p>
      </div>
    </div>

    <div v-else class="card">
      <table class="table">
        <thead>
          <tr>
            <th>Environment</th>
            <th>Key</th>
            <th>Value</th>
            <th>Secret</th>
            <th>Status</th>
            <th>Description</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in settings" :key="s.id">
            <td><span class="pill">{{ s.environment.toUpperCase() }}</span></td>
            <td class="text-mono text-sm">{{ s.key }}</td>
            <td class="text-mono text-sm">{{ s.value }}</td>
            <td>{{ s.is_secret ? 'Yes' : 'No' }}</td>
            <td>
              <span :class="`pill pill-${s.is_active ? 'active' : 'inactive'}`">
                {{ s.is_active ? 'active' : 'inactive' }}
              </span>
            </td>
            <td>{{ s.description || '-' }}</td>
            <td class="table-actions">
              <button class="btn btn-sm" @click="openEdit(s)">Edit</button>
              <button class="btn btn-sm btn-danger" @click="removeSetting(s.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create -->
    <div v-if="showCreate" class="modal-backdrop" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">Add environment setting</div>
          <button class="modal-close" @click="showCreate = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row two-col">
            <div>
              <label class="form-label">Environment</label>
              <select v-model="draft.environment" class="form-control">
                <option value="dev">DEV</option>
                <option value="qa">QA</option>
                <option value="prod">PROD</option>
              </select>
            </div>
            <div>
              <label class="form-label">Key</label>
              <input v-model="draft.key" class="form-control" placeholder="OUC_API_HOST">
            </div>
          </div>
          <div class="form-row">
            <label class="form-label">Value</label>
            <input v-model="draft.value" class="form-control" placeholder="qa-ouc.example.internal">
          </div>
          <div class="form-row">
            <label class="form-label">Description</label>
            <input v-model="draft.description" class="form-control" placeholder="Optional description">
          </div>
          <div class="form-row two-col">
            <label class="text-sm">
              <input type="checkbox" v-model="draft.is_secret"> Secret (masked in API responses)
            </label>
            <label class="text-sm">
              <input type="checkbox" v-model="draft.is_active"> Active
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showCreate = false">Cancel</button>
          <button class="btn btn-primary" :disabled="saving || !draft.key || !draft.value" @click="createSetting">
            {{ saving ? 'Saving…' : 'Create' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Edit -->
    <div v-if="showEdit" class="modal-backdrop" @click.self="closeEdit">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">Edit environment setting</div>
          <button class="modal-close" @click="closeEdit">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row two-col">
            <div>
              <label class="form-label">Environment</label>
              <select v-model="editDraft.environment" class="form-control">
                <option value="dev">DEV</option>
                <option value="qa">QA</option>
                <option value="prod">PROD</option>
              </select>
            </div>
            <div>
              <label class="form-label">Key</label>
              <input v-model="editDraft.key" class="form-control">
            </div>
          </div>
          <div class="form-row">
            <label class="form-label">Value</label>
            <input
              v-model="editDraft.value"
              class="form-control"
              :type="editDraft.is_secret ? 'password' : 'text'"
              :placeholder="editDraft.is_secret ? 'Leave empty to keep current secret; type to replace' : 'Value'"
              autocomplete="off"
            >
            <div v-if="editDraft.is_secret" class="form-help">Secret values are not shown after save. Enter a new value only when you want to replace it.</div>
          </div>
          <div class="form-row">
            <label class="form-label">Description</label>
            <input v-model="editDraft.description" class="form-control" placeholder="Optional">
          </div>
          <div class="form-row two-col">
            <label class="text-sm">
              <input type="checkbox" v-model="editDraft.is_secret"> Secret
            </label>
            <label class="text-sm">
              <input type="checkbox" v-model="editDraft.is_active"> Active
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="closeEdit">Cancel</button>
          <button
            class="btn btn-primary"
            :disabled="savingEdit || !editDraft.key || (!editDraft.is_secret && editDraft.value === '')"
            @click="updateSetting"
          >
            {{ savingEdit ? 'Saving…' : 'Save changes' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
