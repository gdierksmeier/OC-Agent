<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { systemApi } from '../api.js'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const FRONTEND_VERSION = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.0.0'
const FRONTEND_BUILD_DATE = typeof __APP_BUILD_DATE__ !== 'undefined' ? __APP_BUILD_DATE__ : ''

const info = ref(null)
const loading = ref(false)
const apiOk = ref(null)
const error = ref(null)

async function loadInfo() {
  loading.value = true
  error.value = null
  try {
    const [i] = await Promise.all([systemApi.info()])
    info.value = i
    apiOk.value = true
  } catch (e) {
    apiOk.value = false
    error.value = e.response?.data?.detail || e.message || 'Backend unreachable'
  } finally {
    loading.value = false
  }
}

watch(() => props.open, (isOpen) => {
  if (isOpen && !info.value && !loading.value) loadInfo()
})

function onKey(e) {
  if (e.key === 'Escape' && props.open) emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

function formatUptime(seconds) {
  if (seconds == null) return '—'
  const s = Math.floor(seconds)
  const days = Math.floor(s / 86400)
  const hrs = Math.floor((s % 86400) / 3600)
  const mins = Math.floor((s % 3600) / 60)
  const secs = s % 60
  const parts = []
  if (days) parts.push(`${days}d`)
  if (hrs) parts.push(`${hrs}h`)
  if (mins) parts.push(`${mins}m`)
  parts.push(`${secs}s`)
  return parts.join(' ')
}

const formattedStarted = computed(() =>
  info.value?.started_at ? new Date(info.value.started_at).toLocaleString() : '—'
)
</script>

<template>
  <Teleport to="body">
    <Transition name="about-fade">
      <div v-if="open" class="about-overlay" @mousedown.self="emit('close')">
        <div class="about-modal" role="dialog" aria-modal="true" aria-labelledby="about-title">
          <button class="about-close" @click="emit('close')" aria-label="Close">×</button>

          <header class="about-header">
            <div class="about-logo">A</div>
            <div>
              <div class="about-title" id="about-title">{{ info?.short_name || 'Agent Factory' }}</div>
              <div class="about-subtitle">{{ info?.name || 'AI Agent Generation & Maintenance System' }}</div>
            </div>
          </header>

          <section class="about-section about-versions">
            <div class="about-version-card">
              <div class="about-version-label">Frontend</div>
              <div class="about-version-num">v{{ FRONTEND_VERSION }}</div>
              <div class="about-version-hint">Vue 3 · Vite</div>
            </div>
            <div class="about-version-card">
              <div class="about-version-label">Backend</div>
              <div class="about-version-num">
                <template v-if="loading">…</template>
                <template v-else-if="info">v{{ info.version }}</template>
                <template v-else>—</template>
              </div>
              <div class="about-version-hint">FastAPI · SQLite</div>
            </div>
            <div class="about-version-card about-status" :class="{ 'is-ok': apiOk === true, 'is-down': apiOk === false }">
              <div class="about-version-label">API</div>
              <div class="about-version-num">
                <span class="about-status-dot" />
                {{ apiOk === true ? 'Online' : apiOk === false ? 'Offline' : '…' }}
              </div>
              <div class="about-version-hint">{{ error || 'localhost:8000' }}</div>
            </div>
          </section>

          <section v-if="info" class="about-section">
            <div class="about-section-title">Release</div>
            <div class="about-grid">
              <div><span class="about-key">Build</span><span class="about-val">{{ info.build_name || '—' }}</span></div>
              <div><span class="about-key">Released</span><span class="about-val">{{ info.release_date || '—' }}</span></div>
              <div><span class="about-key">Phase</span><span class="about-val">{{ info.phase || '—' }}</span></div>
              <div><span class="about-key">FE built</span><span class="about-val">{{ FRONTEND_BUILD_DATE || '—' }}</span></div>
            </div>
          </section>

          <section v-if="info" class="about-section">
            <div class="about-section-title">Runtime</div>
            <div class="about-grid">
              <div><span class="about-key">Started</span><span class="about-val">{{ formattedStarted }}</span></div>
              <div><span class="about-key">Uptime</span><span class="about-val">{{ formatUptime(info.uptime_seconds) }}</span></div>
              <div><span class="about-key">Python</span><span class="about-val">{{ info.stack?.python || '—' }}</span></div>
              <div><span class="about-key">FastAPI</span><span class="about-val">{{ info.stack?.fastapi || '—' }}</span></div>
              <div><span class="about-key">SQLAlchemy</span><span class="about-val">{{ info.stack?.sqlalchemy || '—' }}</span></div>
              <div><span class="about-key">Pydantic</span><span class="about-val">{{ info.stack?.pydantic || '—' }}</span></div>
              <div class="about-grid-wide"><span class="about-key">Platform</span><span class="about-val">{{ info.stack?.platform || '—' }}</span></div>
            </div>
          </section>

          <section v-if="info?.counts" class="about-section">
            <div class="about-section-title">System contents</div>
            <div class="about-counts">
              <div class="about-count" v-for="(v, k) in info.counts" :key="k">
                <div class="about-count-num">{{ v }}</div>
                <div class="about-count-label">{{ k }}</div>
              </div>
            </div>
          </section>

          <footer v-if="info?.links" class="about-footer">
            <a :href="info.links.api_docs" target="_blank" rel="noopener" class="about-link">API docs</a>
            <span class="about-footer-sep">·</span>
            <a :href="info.links.repository" target="_blank" rel="noopener" class="about-link">Repository</a>
            <span class="about-footer-sep">·</span>
            <span class="about-footer-meta">© 2026 OC Agent</span>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.about-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.7);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.about-modal {
  position: relative;
  width: 100%;
  max-width: 620px;
  max-height: 90vh;
  overflow-y: auto;
  background: linear-gradient(160deg, #0b2545 0%, #06132a 70%);
  border: 1px solid #1e3a8a;
  border-radius: 14px;
  color: #e2e8f0;
  padding: 28px 28px 22px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.6), 0 0 60px rgba(34, 211, 238, 0.12) inset;
}

.about-close {
  position: absolute;
  top: 14px;
  right: 16px;
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 24px;
  cursor: pointer;
  line-height: 1;
  padding: 4px 8px;
  border-radius: 6px;
}
.about-close:hover { color: #f1f5f9; background: rgba(148, 163, 184, 0.1); }

.about-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(34, 211, 238, 0.15);
}
.about-logo {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: linear-gradient(135deg, #60a5fa, #a78bfa, #22d3ee);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 700;
  color: white;
  box-shadow: 0 0 24px rgba(34, 211, 238, 0.5);
  flex-shrink: 0;
}
.about-title {
  font-size: 22px;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: 0.01em;
}
.about-subtitle {
  font-size: 12.5px;
  color: #94a3b8;
  margin-top: 2px;
}

.about-section { margin-top: 18px; }
.about-section-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #67e8f9;
  margin-bottom: 10px;
}

.about-versions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.about-version-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid #1e3a8a;
  border-radius: 10px;
  padding: 12px 14px;
}
.about-version-label {
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94a3b8;
  font-weight: 600;
}
.about-version-num {
  font-size: 20px;
  font-weight: 700;
  color: #67e8f9;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  margin: 4px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.about-version-hint {
  font-size: 11px;
  color: #64748b;
}
.about-status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #94a3b8;
}
.about-status.is-ok .about-status-dot {
  background: #4ade80;
  box-shadow: 0 0 10px #4ade80;
}
.about-status.is-ok .about-version-num { color: #4ade80; }
.about-status.is-down .about-status-dot {
  background: #fb7185;
  box-shadow: 0 0 10px #fb7185;
}
.about-status.is-down .about-version-num { color: #fb7185; }

.about-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 18px;
  font-size: 12.5px;
}
.about-grid > div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 0;
  border-bottom: 1px dashed rgba(148, 163, 184, 0.12);
}
.about-grid-wide { grid-column: 1 / -1; }
.about-key { color: #94a3b8; }
.about-val { color: #e2e8f0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; text-align: right; word-break: break-word; }

.about-counts {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
}
.about-count {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid #1e3a8a;
  border-radius: 8px;
  padding: 10px 4px;
  text-align: center;
}
.about-count-num {
  font-size: 18px;
  font-weight: 700;
  color: #67e8f9;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.about-count-label {
  font-size: 10px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 2px;
}

.about-footer {
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid rgba(34, 211, 238, 0.15);
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #94a3b8;
  flex-wrap: wrap;
}
.about-link { color: #67e8f9; text-decoration: none; }
.about-link:hover { text-decoration: underline; }
.about-footer-sep { color: #475569; }
.about-footer-meta { margin-left: auto; }

.about-fade-enter-active, .about-fade-leave-active {
  transition: opacity 0.2s ease;
}
.about-fade-enter-active .about-modal, .about-fade-leave-active .about-modal {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.about-fade-enter-from, .about-fade-leave-to { opacity: 0; }
.about-fade-enter-from .about-modal, .about-fade-leave-to .about-modal {
  transform: translateY(12px) scale(0.97);
  opacity: 0;
}

@media (max-width: 600px) {
  .about-versions { grid-template-columns: 1fr; }
  .about-counts { grid-template-columns: repeat(3, 1fr); }
  .about-grid { grid-template-columns: 1fr; }
  .about-grid-wide { grid-column: 1; }
}
</style>
