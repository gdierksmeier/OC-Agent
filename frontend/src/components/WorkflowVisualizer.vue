<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  tasks: { type: Array, required: true },
  endpoints: { type: Array, default: () => [] },
  models: { type: Array, default: () => [] },
  prompts: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  editable: { type: Boolean, default: true },
})

const emit = defineEmits(['update:tasks'])

const direction = ref('horizontal') // 'horizontal' | 'vertical'

const CANVAS_HEIGHT = 460
const MIN_SCALE = 0.2
const MAX_SCALE = 2.5

const NODE_W = 196
const NODE_H = 78
const COL_GAP = 80
const ROW_GAP = 28
const PADDING = 48

const TYPE_META = {
  classify:      { label: 'Classify',     accent: '#a78bfa', icon: 'tag' },
  retrieve:      { label: 'Retrieve',     accent: '#34d399', icon: 'search' },
  call_endpoint: { label: 'Endpoint',     accent: '#22d3ee', icon: 'globe' },
  transform:     { label: 'Transform',    accent: '#f472b6', icon: 'shuffle' },
  call_model:    { label: 'AI Model',     accent: '#60a5fa', icon: 'robot' },
  generate:      { label: 'Generate',     accent: '#fbbf24', icon: 'sparkles' },
  validate:      { label: 'Validate',     accent: '#4ade80', icon: 'check' },
  escalate:      { label: 'Escalate',     accent: '#fb7185', icon: 'alert' },
  approval:      { label: 'Approval',     accent: '#c084fc', icon: 'user' },
  loop:          { label: 'Loop',         accent: '#facc15', icon: 'loop' },
  branch:        { label: 'Branch',       accent: '#fb923c', icon: 'branch' },
}

function metaFor(type) {
  return TYPE_META[type] || { label: type || 'Task', accent: '#22d3ee', icon: 'box' }
}

// Resolve a depends_on token (id, name, or order_index) to a task index.
function resolveDep(tasks, token) {
  const stringToken = String(token)
  for (let i = 0; i < tasks.length; i++) {
    const t = tasks[i]
    if (t.id != null && String(t.id) === stringToken) return i
    if (t.name && t.name === stringToken) return i
    if (t.order_index != null && String(t.order_index) === stringToken) return i
  }
  return -1
}

// Compute layered (Sugiyama-light) layout from depends_on edges.
const layout = computed(() => {
  const tasks = (props.tasks || []).map((t, i) => ({ ...t, _idx: i }))
  if (!tasks.length) return { nodes: [], edges: [], width: 600, height: 240 }

  // Build adjacency
  const inEdges = tasks.map(() => [])
  const outEdges = tasks.map(() => [])
  tasks.forEach((t, i) => {
    const deps = Array.isArray(t.depends_on) ? t.depends_on : []
    deps.forEach(d => {
      const j = resolveDep(tasks, d)
      if (j >= 0 && j !== i) {
        inEdges[i].push(j)
        outEdges[j].push(i)
      }
    })
  })

  // Layer = longest path from any source
  const layer = tasks.map(() => -1)
  function compute(i, stack = new Set()) {
    if (layer[i] >= 0) return layer[i]
    if (stack.has(i)) return 0 // cycle guard
    stack.add(i)
    if (!inEdges[i].length) {
      layer[i] = 0
    } else {
      layer[i] = 1 + Math.max(...inEdges[i].map(j => compute(j, stack)))
    }
    stack.delete(i)
    return layer[i]
  }
  tasks.forEach((_, i) => compute(i))

  // Group by layer, ordered by order_index then original index
  const layers = []
  layer.forEach((l, i) => {
    if (!layers[l]) layers[l] = []
    layers[l].push(i)
  })
  layers.forEach(col => col.sort((a, b) => {
    const oa = tasks[a].order_index ?? a
    const ob = tasks[b].order_index ?? b
    return oa - ob
  }))

  // Position — primary axis follows layer index, cross axis fans nodes within a layer.
  const horizontal = direction.value === 'horizontal'
  const layerCount = layers.length
  const maxCross = Math.max(...layers.map(c => c.length))

  const primaryStep = horizontal ? NODE_W + COL_GAP : NODE_H + ROW_GAP
  const crossStep  = horizontal ? NODE_H + ROW_GAP : NODE_W + COL_GAP
  const primaryNode = horizontal ? NODE_W : NODE_H
  const crossNode  = horizontal ? NODE_H : NODE_W

  const primarySize = PADDING * 2 + layerCount * primaryNode + (layerCount - 1) * (primaryStep - primaryNode)
  const crossSize   = PADDING * 2 + maxCross * crossNode + (maxCross - 1) * (crossStep - crossNode)

  const width = horizontal ? primarySize : crossSize
  const height = horizontal ? crossSize : primarySize

  const nodes = []
  layers.forEach((col, li) => {
    const groupCross = col.length * crossNode + (col.length - 1) * (crossStep - crossNode)
    const crossStart = ((horizontal ? height : width) - groupCross) / 2
    col.forEach((idx, ri) => {
      const t = tasks[idx]
      const primaryPos = PADDING + li * primaryStep
      const crossPos   = crossStart + ri * crossStep
      nodes.push({
        idx,
        task: t,
        x: horizontal ? primaryPos : crossPos,
        y: horizontal ? crossPos   : primaryPos,
        layer: li,
      })
    })
  })

  const nodeByIdx = Object.fromEntries(nodes.map(n => [n.idx, n]))

  // Build edges (resolve via inEdges)
  const edges = []
  inEdges.forEach((deps, i) => {
    const tgt = nodeByIdx[i]
    if (!tgt) return
    deps.forEach(j => {
      const src = nodeByIdx[j]
      if (!src) return
      edges.push({
        id: `${j}-${i}`,
        source: src,
        target: tgt,
      })
    })
  })

  // Sequential implicit edges (when there are 0 explicit edges):
  // chain by order_index so the user sees a sensible flow before wiring deps.
  if (!edges.length && nodes.length > 1) {
    const ordered = [...nodes].sort((a, b) => {
      const oa = a.task.order_index ?? a.idx
      const ob = b.task.order_index ?? b.idx
      return oa - ob
    })
    for (let i = 1; i < ordered.length; i++) {
      edges.push({
        id: `seq-${ordered[i - 1].idx}-${ordered[i].idx}`,
        source: ordered[i - 1],
        target: ordered[i],
        implicit: true,
      })
    }
  }

  return { nodes, edges, width, height }
})

function edgePath(src, tgt) {
  if (direction.value === 'horizontal') {
    const x1 = src.x + NODE_W
    const y1 = src.y + NODE_H / 2
    const x2 = tgt.x
    const y2 = tgt.y + NODE_H / 2
    const dx = Math.max(40, (x2 - x1) * 0.5)
    return `M ${x1},${y1} C ${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`
  } else {
    const x1 = src.x + NODE_W / 2
    const y1 = src.y + NODE_H
    const x2 = tgt.x + NODE_W / 2
    const y2 = tgt.y
    const dy = Math.max(30, (y2 - y1) * 0.5)
    return `M ${x1},${y1} C ${x1},${y1 + dy} ${x2},${y2 - dy} ${x2},${y2}`
  }
}

function edgeMidpoint(src, tgt) {
  if (direction.value === 'horizontal') {
    return {
      x: (src.x + NODE_W + tgt.x) / 2,
      y: (src.y + tgt.y + NODE_H) / 2,
    }
  }
  return {
    x: (src.x + tgt.x + NODE_W) / 2,
    y: (src.y + NODE_H + tgt.y) / 2,
  }
}

const hoverIdx = ref(null)
const selectedIdx = ref(null)

function nodeAttachmentLabel(task) {
  if (task.endpoint_id) {
    const ep = props.endpoints.find(e => e.id === task.endpoint_id)
    return ep ? ep.name : `endpoint #${task.endpoint_id}`
  }
  if (task.model_id) {
    const m = props.models.find(x => x.id === task.model_id)
    return m ? m.name : `model #${task.model_id}`
  }
  if (task.prompt_id) {
    const p = props.prompts.find(x => x.id === task.prompt_id)
    return p ? p.name : `prompt #${task.prompt_id}`
  }
  return ''
}

const selectedTask = computed(() => {
  if (selectedIdx.value == null) return null
  return layout.value.nodes.find(n => n.idx === selectedIdx.value)?.task || null
})

// ---------- Graphical editing ----------
const TASK_TYPES = ['classify','retrieve','call_endpoint','transform','call_model','generate','validate','escalate','approval','loop','branch']
const ERROR_POLICIES = ['fail','retry','fallback','escalate','continue']

const connectingFrom = ref(null) // source node idx while drawing a new dependency
const editingName = ref(false)
const nameDraft = ref('')

// Tokens that could refer to a task in another task's depends_on array.
function tokensFor(task) {
  const out = []
  if (task.id != null) out.push(String(task.id))
  if (task.name) out.push(String(task.name))
  if (task.order_index != null) out.push(String(task.order_index))
  return out
}

function buildTaskPatch(task, patch) {
  const merged = { ...task, ...patch }
  if ('depends_on' in patch) {
    merged.dependsOnJson = JSON.stringify(patch.depends_on, null, 2)
  }
  if ('config' in patch) {
    merged.configJson = JSON.stringify(patch.config, null, 2)
  }
  return merged
}

function emitTaskUpdate(idx, patch) {
  const next = props.tasks.map((t, i) => i === idx ? buildTaskPatch(t, patch) : t)
  emit('update:tasks', next)
}

function addTask() {
  const ord = props.tasks.length + 1
  let baseName = `task_${ord}`
  const existingNames = new Set(props.tasks.map(t => t.name))
  let n = ord
  while (existingNames.has(baseName)) {
    n += 1
    baseName = `task_${n}`
  }
  const newTask = {
    name: baseName,
    task_type: 'call_endpoint',
    order_index: ord,
    timeout_seconds: 30,
    retry_count: 0,
    error_handling: 'fail',
    endpoint_id: null,
    model_id: null,
    prompt_id: null,
    config: {},
    depends_on: [],
    condition: '',
    preconditions: '',
    postconditions: '',
    configJson: '{}',
    dependsOnJson: '[]',
  }
  emit('update:tasks', [...props.tasks, newTask])
  nextTick(() => {
    selectedIdx.value = props.tasks.length - 1
  })
}

function deleteTask(idx) {
  const removed = props.tasks[idx]
  if (!removed) return
  const removeTokens = tokensFor(removed)
  const next = props.tasks
    .filter((_, i) => i !== idx)
    .map(t => {
      const filtered = (t.depends_on || []).filter(d => !removeTokens.includes(String(d)))
      if (filtered.length !== (t.depends_on || []).length) {
        return buildTaskPatch(t, { depends_on: filtered })
      }
      return t
    })
  emit('update:tasks', next)
  selectedIdx.value = null
  connectingFrom.value = null
}

function renameTask(idx, newName) {
  const trimmed = (newName || '').trim()
  if (!trimmed) return
  const oldName = props.tasks[idx].name
  if (oldName === trimmed) return
  const next = props.tasks.map((t, i) => {
    if (i === idx) return { ...t, name: trimmed }
    const deps = t.depends_on || []
    if (deps.some(d => String(d) === String(oldName))) {
      const updated = deps.map(d => String(d) === String(oldName) ? trimmed : d)
      return buildTaskPatch(t, { depends_on: updated })
    }
    return t
  })
  emit('update:tasks', next)
}

function changeTaskType(idx, type) {
  emitTaskUpdate(idx, { task_type: type })
}
function changeErrorHandling(idx, policy) {
  emitTaskUpdate(idx, { error_handling: policy })
}
function changeRetry(idx, n) {
  emitTaskUpdate(idx, { retry_count: Number(n) || 0 })
}
function changeCondition(idx, expr) {
  emitTaskUpdate(idx, { condition: expr || '' })
}

function startConnect(sourceIdx) {
  connectingFrom.value = sourceIdx
}
function cancelConnect() {
  connectingFrom.value = null
}

// Detect whether sourceIdx already appears in targetIdx's depends_on.
function hasDependency(targetIdx, sourceIdx) {
  const target = props.tasks[targetIdx]
  const source = props.tasks[sourceIdx]
  if (!target || !source) return false
  const tokens = tokensFor(source)
  return (target.depends_on || []).some(d => tokens.includes(String(d)))
}

function addDependency(targetIdx, sourceIdx) {
  if (targetIdx === sourceIdx) return
  if (hasDependency(targetIdx, sourceIdx)) return
  const source = props.tasks[sourceIdx]
  const target = props.tasks[targetIdx]
  if (!source || !target) return
  const token = source.name || source.id || source.order_index
  emitTaskUpdate(targetIdx, { depends_on: [...(target.depends_on || []), token] })
}

function removeEdge(sourceIdx, targetIdx) {
  const source = props.tasks[sourceIdx]
  const target = props.tasks[targetIdx]
  if (!source || !target) return
  const tokens = tokensFor(source)
  const next = (target.depends_on || []).filter(d => !tokens.includes(String(d)))
  emitTaskUpdate(targetIdx, { depends_on: next })
}

function onNodeClick(idx) {
  if (connectingFrom.value !== null && connectingFrom.value !== idx) {
    addDependency(idx, connectingFrom.value)
    connectingFrom.value = null
    selectedIdx.value = idx
    return
  }
  if (connectingFrom.value === idx) {
    connectingFrom.value = null
    return
  }
  selectedIdx.value = selectedIdx.value === idx ? null : idx
  editingName.value = false
}

function startNameEdit() {
  if (!selectedTask.value) return
  nameDraft.value = selectedTask.value.name || ''
  editingName.value = true
}
function commitNameEdit() {
  if (selectedIdx.value != null) renameTask(selectedIdx.value, nameDraft.value)
  editingName.value = false
}

function toggleDirection() {
  direction.value = direction.value === 'horizontal' ? 'vertical' : 'horizontal'
  nextTick(fitToView)
}

// ---------- Pan & zoom ----------
const canvasRef = ref(null)
const scale = ref(1)
const tx = ref(0)
const ty = ref(0)
const isPanning = ref(false)
let panStart = null

function clampScale(s) {
  return Math.max(MIN_SCALE, Math.min(MAX_SCALE, s))
}

function fitToView() {
  const el = canvasRef.value
  if (!el) return
  const w = layout.value.width
  const h = layout.value.height
  if (!w || !h) return
  const cw = el.clientWidth
  const ch = el.clientHeight || CANVAS_HEIGHT
  const s = clampScale(Math.min(cw / w, ch / h) * 0.95)
  scale.value = s
  tx.value = (cw - w * s) / 2
  ty.value = (ch - h * s) / 2
}

function resetView() {
  scale.value = 1
  tx.value = 0
  ty.value = 0
}

function zoomBy(factor, originX, originY) {
  const el = canvasRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const cx = originX != null ? originX - rect.left : rect.width / 2
  const cy = originY != null ? originY - rect.top : rect.height / 2
  const next = clampScale(scale.value * factor)
  const ratio = next / scale.value
  tx.value = cx - (cx - tx.value) * ratio
  ty.value = cy - (cy - ty.value) * ratio
  scale.value = next
}

function onWheel(e) {
  // Zoom on Ctrl/Cmd+wheel (or trackpad pinch, which sets ctrlKey).
  // Plain wheel falls through so the page can scroll normally.
  if (!e.ctrlKey && !e.metaKey) return
  e.preventDefault()
  const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1
  zoomBy(factor, e.clientX, e.clientY)
}

function onPanStart(e) {
  if (e.button !== 0) return
  if (e.target.closest('.wf-node')) return
  isPanning.value = true
  panStart = { x: e.clientX - tx.value, y: e.clientY - ty.value }
}
function onPanMove(e) {
  if (!isPanning.value || !panStart) return
  tx.value = e.clientX - panStart.x
  ty.value = e.clientY - panStart.y
}
function onPanEnd() {
  isPanning.value = false
  panStart = null
}

const transform = computed(() => `translate(${tx.value} ${ty.value}) scale(${scale.value})`)
const zoomPct = computed(() => Math.round(scale.value * 100))

let resizeObserver = null
onMounted(() => {
  nextTick(fitToView)
  if (typeof ResizeObserver !== 'undefined' && canvasRef.value) {
    resizeObserver = new ResizeObserver(() => {
      // Refit only when at default-ish zoom so we don't fight the user
    })
    resizeObserver.observe(canvasRef.value)
  }
  window.addEventListener('mousemove', onPanMove)
  window.addEventListener('mouseup', onPanEnd)
})
onBeforeUnmount(() => {
  if (resizeObserver) resizeObserver.disconnect()
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanEnd)
})

// Refit when the graph changes shape (task added/removed) or direction flips
watch(() => [layout.value.width, layout.value.height, layout.value.nodes.length, direction.value], () => {
  nextTick(fitToView)
})
</script>

<template>
  <div class="wf-viz">
    <div class="wf-viz-header" v-if="title || layout.nodes.length">
      <div class="wf-viz-title">
        <span class="wf-viz-dot" /> {{ title || 'Workflow graph' }}
      </div>
      <div class="wf-viz-toolbar">
        <button v-if="editable" class="wf-tool-btn wf-tool-text wf-tool-add" @click="addTask" title="Add a new task">+ Task</button>
        <span v-if="editable" class="wf-tool-sep" />
        <button
          class="wf-tool-btn"
          :class="{ 'wf-tool-active': direction === 'horizontal' }"
          @click="direction !== 'horizontal' && toggleDirection()"
          title="Horizontal layout"
        >↔</button>
        <button
          class="wf-tool-btn"
          :class="{ 'wf-tool-active': direction === 'vertical' }"
          @click="direction !== 'vertical' && toggleDirection()"
          title="Vertical layout"
        >↕</button>
        <span class="wf-tool-sep" />
        <button class="wf-tool-btn" @click="zoomBy(1 / 1.2)" title="Zoom out">−</button>
        <span class="wf-tool-zoom" :title="`${zoomPct}%`">{{ zoomPct }}%</span>
        <button class="wf-tool-btn" @click="zoomBy(1.2)" title="Zoom in">+</button>
        <span class="wf-tool-sep" />
        <button class="wf-tool-btn wf-tool-text" @click="fitToView" title="Fit to view">Fit</button>
        <button class="wf-tool-btn wf-tool-text" @click="resetView" title="Reset to 100%">1:1</button>
      </div>
      <div class="wf-viz-meta">
        {{ layout.nodes.length }} task{{ layout.nodes.length === 1 ? '' : 's' }}
        · {{ layout.edges.length }} link{{ layout.edges.length === 1 ? '' : 's' }}
      </div>
    </div>

    <div v-if="!layout.nodes.length" class="wf-viz-empty">
      No tasks yet.
      <button v-if="editable" class="wf-tool-btn wf-tool-text wf-tool-add" style="margin-left:10px" @click="addTask">+ Add first task</button>
    </div>

    <div
      v-else
      ref="canvasRef"
      class="wf-viz-canvas"
      :class="{ 'wf-viz-panning': isPanning }"
      @wheel="onWheel"
      @mousedown="onPanStart"
    >
      <svg
        class="wf-viz-svg"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <radialGradient id="wfBg" cx="50%" cy="50%" r="75%">
            <stop offset="0%"  stop-color="#0b2545" />
            <stop offset="60%" stop-color="#06132a" />
            <stop offset="100%" stop-color="#020616" />
          </radialGradient>

          <pattern id="wfDots" width="22" height="22" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1" fill="#1e3a8a" opacity="0.35" />
          </pattern>

          <linearGradient id="wfEdge" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stop-color="#22d3ee" stop-opacity="0.15" />
            <stop offset="50%"  stop-color="#67e8f9" stop-opacity="0.95" />
            <stop offset="100%" stop-color="#22d3ee" stop-opacity="0.15" />
          </linearGradient>

          <filter id="wfGlow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="wfNodeGlow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <!-- Icon symbols -->
          <symbol id="ic-tag" viewBox="0 0 24 24">
            <path d="M3 12V5a2 2 0 0 1 2-2h7l9 9-9 9-9-9z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
            <circle cx="8" cy="8" r="1.4" fill="currentColor"/>
          </symbol>
          <symbol id="ic-search" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="6" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <path d="M16 16l4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </symbol>
          <symbol id="ic-globe" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <ellipse cx="12" cy="12" rx="4" ry="9" fill="none" stroke="currentColor" stroke-width="1.4"/>
            <path d="M3 12h18" stroke="currentColor" stroke-width="1.4"/>
          </symbol>
          <symbol id="ic-shuffle" viewBox="0 0 24 24">
            <path d="M3 7h4l10 10h4M3 17h4l4-4M17 7h4l-3-3M21 17l-3 3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
          </symbol>
          <symbol id="ic-robot" viewBox="0 0 24 24">
            <rect x="4" y="7" width="16" height="12" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <path d="M12 4v3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            <circle cx="12" cy="3.4" r="1.2" fill="currentColor"/>
            <circle cx="9" cy="13" r="1.4" fill="currentColor"/>
            <circle cx="15" cy="13" r="1.4" fill="currentColor"/>
          </symbol>
          <symbol id="ic-sparkles" viewBox="0 0 24 24">
            <path d="M12 3l1.8 4.8L18 9.6l-4.2 1.8L12 16l-1.8-4.6L6 9.6l4.2-1.8z" fill="currentColor"/>
            <path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z" fill="currentColor"/>
          </symbol>
          <symbol id="ic-check" viewBox="0 0 24 24">
            <path d="M5 12l5 5 9-11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </symbol>
          <symbol id="ic-alert" viewBox="0 0 24 24">
            <path d="M12 3l10 18H2z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
            <path d="M12 10v5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            <circle cx="12" cy="18" r="1.1" fill="currentColor"/>
          </symbol>
          <symbol id="ic-user" viewBox="0 0 24 24">
            <circle cx="12" cy="8" r="3.5" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </symbol>
          <symbol id="ic-loop" viewBox="0 0 24 24">
            <path d="M5 9a7 7 0 0 1 12-3l2 2M19 15a7 7 0 0 1-12 3l-2-2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            <path d="M19 4v4h-4M5 20v-4h4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
          </symbol>
          <symbol id="ic-box" viewBox="0 0 24 24">
            <rect x="4" y="4" width="16" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/>
          </symbol>
          <symbol id="ic-branch" viewBox="0 0 24 24">
            <path d="M12 3v6M12 9l-5 5v7M12 9l5 5v7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="12" cy="3.6" r="1.6" fill="currentColor"/>
            <circle cx="7"  cy="20.4" r="1.6" fill="currentColor"/>
            <circle cx="17" cy="20.4" r="1.6" fill="currentColor"/>
          </symbol>
        </defs>

        <!-- Static backdrop fills the whole viewport so panning never reveals white -->
        <rect width="100%" height="100%" fill="url(#wfBg)" />
        <rect width="100%" height="100%" fill="url(#wfDots)" />

        <!-- Pan/zoom group -->
        <g :transform="transform">
          <!-- Local backdrop sized to the actual graph (extends visual region) -->
          <rect :width="layout.width" :height="layout.height" fill="url(#wfBg)" />

        <!-- Edges -->
        <g class="wf-edges">
          <g
            v-for="e in layout.edges"
            :key="e.id"
            :class="['wf-edge', {
              'wf-edge-implicit': e.implicit,
              'wf-edge-active': hoverIdx === e.source.idx || hoverIdx === e.target.idx || selectedIdx === e.source.idx || selectedIdx === e.target.idx,
              'wf-edge-clickable': editable && !e.implicit,
              'wf-edge-branch': e.source.task.task_type === 'branch',
              'wf-edge-conditional': !!e.target.task.condition,
            }]"
            @click.stop="editable && !e.implicit && removeEdge(e.source.idx, e.target.idx)"
          >
            <path :d="edgePath(e.source, e.target)" class="wf-edge-base" />
            <path :d="edgePath(e.source, e.target)" class="wf-edge-glow" filter="url(#wfGlow)" />
            <path :d="edgePath(e.source, e.target)" class="wf-edge-hit" />
            <circle r="2.6" class="wf-edge-pulse">
              <animateMotion :dur="`${3 + (e.target.idx % 3) * 0.4}s`" repeatCount="indefinite" :path="edgePath(e.source, e.target)" />
            </circle>
            <!-- Condition badge — shown when the target task carries a condition -->
            <g
              v-if="e.target.task.condition"
              class="wf-edge-label"
              :transform="`translate(${edgeMidpoint(e.source, e.target).x}, ${edgeMidpoint(e.source, e.target).y})`"
            >
              <rect
                :x="-Math.min(120, e.target.task.condition.length * 4 + 14) / 2"
                y="-11"
                :width="Math.min(120, e.target.task.condition.length * 4 + 14)"
                height="22"
                rx="11"
                class="wf-edge-label-bg"
              />
              <text class="wf-edge-label-text" text-anchor="middle" dy="3.5">
                {{ (e.target.task.condition || '').length > 22 ? e.target.task.condition.slice(0, 21) + '…' : e.target.task.condition }}
              </text>
              <title>{{ e.target.task.condition }}</title>
            </g>
            <title v-if="editable && !e.implicit">Click to remove dependency</title>
          </g>
        </g>

        <!-- Nodes -->
        <g class="wf-nodes">
          <g
            v-for="n in layout.nodes"
            :key="n.idx"
            :transform="`translate(${n.x}, ${n.y})`"
            :class="['wf-node', {
              'wf-node-active': hoverIdx === n.idx || selectedIdx === n.idx,
              'wf-node-connect-source': connectingFrom === n.idx,
              'wf-node-connect-target': connectingFrom !== null && connectingFrom !== n.idx && hoverIdx === n.idx,
              'wf-node-branch': n.task.task_type === 'branch',
            }]"
            @mouseenter="hoverIdx = n.idx"
            @mouseleave="hoverIdx = null"
            @click.stop="onNodeClick(n.idx)"
          >
            <!-- Outer aura -->
            <rect
              :width="NODE_W" :height="NODE_H"
              :rx="n.task.task_type === 'branch' ? 28 : 14"
              :ry="n.task.task_type === 'branch' ? 28 : 14"
              :fill="metaFor(n.task.task_type).accent"
              opacity="0.12"
              filter="url(#wfNodeGlow)"
            />
            <!-- Core card -->
            <rect
              :width="NODE_W" :height="NODE_H"
              :rx="n.task.task_type === 'branch' ? 26 : 12"
              :ry="n.task.task_type === 'branch' ? 26 : 12"
              fill="#0b2540"
              :stroke="metaFor(n.task.task_type).accent"
              :stroke-width="n.task.task_type === 'branch' ? 1.8 : 1.4"
              :stroke-dasharray="n.task.task_type === 'branch' ? '6 4' : ''"
            />
            <!-- Icon disk -->
            <circle cx="28" cy="39" r="18"
              :fill="metaFor(n.task.task_type).accent" opacity="0.18" />
            <circle cx="28" cy="39" r="18"
              fill="none"
              :stroke="metaFor(n.task.task_type).accent"
              stroke-width="1.2"
              opacity="0.85" />
            <g :style="{ color: metaFor(n.task.task_type).accent }" transform="translate(16, 27)">
              <use :href="`#ic-${metaFor(n.task.task_type).icon}`" width="24" height="24" />
            </g>
            <!-- Text -->
            <text x="56" y="32" class="wf-node-name">
              {{ (n.task.name || `Task ${n.task.order_index ?? n.idx + 1}`).slice(0, 22) }}
            </text>
            <text x="56" y="50" class="wf-node-type" :fill="metaFor(n.task.task_type).accent">
              {{ metaFor(n.task.task_type).label }}
            </text>
            <text x="56" y="66" class="wf-node-attach">
              {{ nodeAttachmentLabel(n.task).slice(0, 26) }}
            </text>
            <!-- Step number badge -->
            <g :transform="`translate(${NODE_W - 26}, 12)`">
              <rect width="20" height="18" rx="6" fill="#0a1f3a" stroke="#1e3a8a" stroke-width="0.8"/>
              <text x="10" y="12" text-anchor="middle" class="wf-node-step">
                {{ n.task.order_index ?? n.idx + 1 }}
              </text>
            </g>
          </g>
        </g>
        </g>
      </svg>

      <div v-if="selectedTask" class="wf-viz-detail" @click.stop>
        <div class="wf-viz-detail-row">
          <span class="wf-viz-detail-label">Name</span>
          <span v-if="!editable || !editingName" class="wf-viz-detail-value wf-viz-clickable" @click="editable && startNameEdit()">
            {{ selectedTask.name || '—' }}
          </span>
          <input
            v-else
            v-model="nameDraft"
            class="wf-viz-input"
            autofocus
            @blur="commitNameEdit"
            @keyup.enter="commitNameEdit"
            @keyup.escape="editingName = false"
          >
        </div>
        <div class="wf-viz-detail-row">
          <span class="wf-viz-detail-label">Type</span>
          <select
            v-if="editable"
            class="wf-viz-input wf-viz-select"
            :value="selectedTask.task_type"
            @change="changeTaskType(selectedIdx, $event.target.value)"
          >
            <option v-for="t in TASK_TYPES" :key="t" :value="t">{{ metaFor(t).label }}</option>
          </select>
          <span v-else class="wf-viz-detail-value">{{ metaFor(selectedTask.task_type).label }}</span>
        </div>
        <div class="wf-viz-detail-row" v-if="nodeAttachmentLabel(selectedTask)">
          <span class="wf-viz-detail-label">Bound</span>
          <span class="wf-viz-detail-value">{{ nodeAttachmentLabel(selectedTask) }}</span>
        </div>
        <div class="wf-viz-detail-row">
          <span class="wf-viz-detail-label">Order</span>
          <span class="wf-viz-detail-value">#{{ selectedTask.order_index }}</span>
        </div>
        <div class="wf-viz-detail-row">
          <span class="wf-viz-detail-label">On error</span>
          <select
            v-if="editable"
            class="wf-viz-input wf-viz-select"
            :value="selectedTask.error_handling || 'fail'"
            @change="changeErrorHandling(selectedIdx, $event.target.value)"
          >
            <option v-for="p in ERROR_POLICIES" :key="p" :value="p">{{ p }}</option>
          </select>
          <span v-else class="wf-viz-detail-value">{{ selectedTask.error_handling || 'fail' }}</span>
        </div>
        <div class="wf-viz-detail-row">
          <span class="wf-viz-detail-label">Retry</span>
          <input
            v-if="editable"
            type="number" min="0" max="10"
            class="wf-viz-input wf-viz-input-num"
            :value="selectedTask.retry_count ?? 0"
            @input="changeRetry(selectedIdx, $event.target.value)"
          >
          <span v-else class="wf-viz-detail-value">× {{ selectedTask.retry_count ?? 0 }}</span>
        </div>
        <div class="wf-viz-detail-row" v-if="Array.isArray(selectedTask.depends_on) && selectedTask.depends_on.length">
          <span class="wf-viz-detail-label">Depends on</span>
          <span class="wf-viz-detail-value">{{ selectedTask.depends_on.join(', ') }}</span>
        </div>
        <div class="wf-viz-detail-row wf-viz-detail-row-stack">
          <span class="wf-viz-detail-label">Condition</span>
          <input
            v-if="editable"
            class="wf-viz-input wf-viz-input-cond"
            :value="selectedTask.condition || ''"
            placeholder="e.g.  intent == &quot;billing&quot;   (blank = always run)"
            @input="changeCondition(selectedIdx, $event.target.value)"
          >
          <span v-else class="wf-viz-detail-value">{{ selectedTask.condition || '— always —' }}</span>
        </div>

        <div v-if="editable" class="wf-viz-detail-actions">
          <button
            class="wf-tool-btn wf-tool-text"
            :class="{ 'wf-tool-active': connectingFrom === selectedIdx }"
            @click="connectingFrom === selectedIdx ? cancelConnect() : startConnect(selectedIdx)"
            :title="connectingFrom === selectedIdx ? 'Cancel connect' : 'Click here, then click another node to make it depend on this one'"
          >
            {{ connectingFrom === selectedIdx ? '✕ Cancel' : '→ Connect' }}
          </button>
          <button
            class="wf-tool-btn wf-tool-text wf-tool-danger"
            @click="deleteTask(selectedIdx)"
            title="Delete this task"
          >🗑 Delete</button>
        </div>

        <button class="wf-viz-detail-close" @click="selectedIdx = null" aria-label="Close">×</button>
      </div>

      <!-- Connect-mode banner -->
      <div v-if="connectingFrom !== null" class="wf-viz-banner" @click="cancelConnect">
        <span class="wf-viz-banner-pulse" />
        Click a target node to add a dependency from
        <strong>{{ props.tasks[connectingFrom]?.name || `task ${connectingFrom + 1}` }}</strong>
        — or click here to cancel.
      </div>
    </div>
  </div>
</template>

<style scoped>
.wf-viz {
  border-radius: 12px;
  overflow: hidden;
  background: #06132a;
  border: 1px solid #1e3a8a;
  margin-bottom: 18px;
}

.wf-viz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(90deg, #061226, #0b2545 60%, #061226);
  border-bottom: 1px solid #1e3a8a;
  color: #cbd5e1;
  font-size: 13px;
}
.wf-viz-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e0f2fe;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.wf-viz-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #22d3ee;
  box-shadow: 0 0 10px #22d3ee, 0 0 20px rgba(34, 211, 238, 0.5);
  animation: wfPulse 2.4s ease-in-out infinite;
}
.wf-viz-meta { color: #94a3b8; font-variant-numeric: tabular-nums; }

.wf-viz-empty {
  padding: 48px 24px;
  text-align: center;
  color: #94a3b8;
  background: radial-gradient(circle at 50% 50%, #0b2545 0%, #06132a 70%);
}

.wf-viz-canvas {
  position: relative;
  overflow: hidden;
  height: 460px;
  cursor: grab;
  user-select: none;
}
.wf-viz-canvas.wf-viz-panning { cursor: grabbing; }

.wf-viz-svg {
  display: block;
  width: 100%;
  height: 100%;
}

.wf-viz-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid #1e3a8a;
  border-radius: 8px;
}
.wf-tool-btn {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  color: #cbd5e1;
  font-size: 16px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  line-height: 1;
  padding: 0;
}
.wf-tool-btn:hover {
  background: rgba(34, 211, 238, 0.15);
  border-color: rgba(34, 211, 238, 0.45);
  color: #67e8f9;
}
.wf-tool-text {
  width: auto;
  padding: 0 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.wf-tool-zoom {
  min-width: 44px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  color: #67e8f9;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.wf-tool-sep {
  width: 1px;
  height: 18px;
  background: #1e3a8a;
  margin: 0 4px;
}
.wf-tool-active {
  background: rgba(34, 211, 238, 0.2);
  border-color: #22d3ee;
  color: #67e8f9;
}
.wf-tool-add {
  background: rgba(34, 211, 238, 0.12);
  border-color: rgba(34, 211, 238, 0.4);
  color: #67e8f9;
}
.wf-tool-add:hover {
  background: rgba(34, 211, 238, 0.25);
}
.wf-tool-danger {
  color: #fb7185;
}
.wf-tool-danger:hover {
  background: rgba(251, 113, 133, 0.15);
  border-color: rgba(251, 113, 133, 0.5);
  color: #fda4af;
}

.wf-edge-base {
  fill: none;
  stroke: #1e40af;
  stroke-width: 1.4;
  opacity: 0.55;
}
.wf-edge-glow {
  fill: none;
  stroke: url(#wfEdge);
  stroke-width: 2.2;
  opacity: 0.85;
  transition: stroke-width 0.2s, opacity 0.2s;
}
.wf-edge-implicit .wf-edge-glow {
  stroke-dasharray: 6 6;
  opacity: 0.55;
}
.wf-edge-pulse {
  fill: #e0f7ff;
  filter: drop-shadow(0 0 6px #67e8f9);
}
.wf-edge-active .wf-edge-glow {
  stroke-width: 3.2;
  opacity: 1;
}
.wf-edge-hit {
  fill: none;
  stroke: transparent;
  stroke-width: 16;
  pointer-events: stroke;
}
.wf-edge-clickable { cursor: pointer; }
.wf-edge-clickable:hover .wf-edge-glow {
  stroke: #fb7185;
  opacity: 1;
  stroke-width: 3.2;
}

/* Branch + conditional edges */
.wf-edge-branch .wf-edge-glow,
.wf-edge-conditional .wf-edge-glow {
  stroke: #fb923c;
  opacity: 0.9;
}
.wf-edge-branch .wf-edge-pulse,
.wf-edge-conditional .wf-edge-pulse {
  fill: #fed7aa;
  filter: drop-shadow(0 0 6px #fb923c);
}

.wf-edge-label { pointer-events: none; }
.wf-edge-label-bg {
  fill: rgba(11, 37, 64, 0.95);
  stroke: #fb923c;
  stroke-width: 1;
}
.wf-edge-label-text {
  fill: #fed7aa;
  font-size: 10.5px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 600;
}

.wf-node {
  cursor: pointer;
  transition: transform 0.18s ease;
}
.wf-node:hover { transform: translateY(-1px); }
.wf-node-active { filter: brightness(1.2); }
.wf-node-connect-source rect:nth-child(2) {
  stroke: #facc15 !important;
  stroke-width: 2.4 !important;
}
.wf-node-connect-target rect:nth-child(2) {
  stroke: #4ade80 !important;
  stroke-width: 2.4 !important;
  stroke-dasharray: 4 4;
}

.wf-node-name {
  fill: #f1f5f9;
  font-size: 13px;
  font-weight: 600;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.wf-node-type {
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.wf-node-attach {
  fill: #94a3b8;
  font-size: 10.5px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.wf-node-step {
  fill: #67e8f9;
  font-size: 10px;
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.wf-viz-detail {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 280px;
  background: rgba(6, 19, 42, 0.94);
  border: 1px solid #22d3ee;
  border-radius: 10px;
  padding: 14px 16px 12px;
  color: #cbd5e1;
  font-size: 12.5px;
  box-shadow: 0 0 24px rgba(34, 211, 238, 0.3);
  backdrop-filter: blur(6px);
}
.wf-viz-detail-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 0;
  border-bottom: 1px dashed rgba(148, 163, 184, 0.15);
}
.wf-viz-detail-row:last-of-type { border-bottom: none; }
.wf-viz-detail-label {
  color: #67e8f9;
  text-transform: uppercase;
  font-size: 10.5px;
  letter-spacing: 0.08em;
  font-weight: 600;
}
.wf-viz-detail-value {
  color: #e2e8f0;
  text-align: right;
  word-break: break-word;
}
.wf-viz-detail-close {
  position: absolute;
  top: 6px;
  right: 8px;
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
}
.wf-viz-detail-close:hover { color: #f1f5f9; }

.wf-viz-clickable {
  cursor: text;
  border-bottom: 1px dashed transparent;
  transition: border-color 0.15s;
}
.wf-viz-clickable:hover {
  border-color: rgba(34, 211, 238, 0.5);
}

.wf-viz-input {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid #1e3a8a;
  color: #e2e8f0;
  font-size: 12.5px;
  padding: 3px 6px;
  border-radius: 5px;
  font-family: inherit;
  outline: none;
  flex: 1;
  min-width: 0;
}
.wf-viz-input:focus {
  border-color: #22d3ee;
  box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.18);
}
.wf-viz-select {
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  padding-right: 18px;
  background-image: linear-gradient(45deg, transparent 50%, #67e8f9 50%), linear-gradient(135deg, #67e8f9 50%, transparent 50%);
  background-position: calc(100% - 10px) 50%, calc(100% - 6px) 50%;
  background-size: 4px 4px, 4px 4px;
  background-repeat: no-repeat;
}
.wf-viz-input-num {
  flex: 0 0 60px;
  text-align: right;
}
.wf-viz-input-cond {
  flex: 1;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11.5px;
}
.wf-viz-detail-row-stack {
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
}
.wf-viz-detail-row-stack .wf-viz-detail-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.wf-viz-detail-row-stack .wf-viz-detail-label::after {
  content: 'optional';
  text-transform: none;
  font-size: 9.5px;
  color: #64748b;
  font-weight: 400;
  letter-spacing: 0;
}

.wf-viz-detail-actions {
  display: flex;
  gap: 6px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(34, 211, 238, 0.2);
}
.wf-viz-detail-actions .wf-tool-btn {
  flex: 1;
}

.wf-viz-banner {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(250, 204, 21, 0.18);
  border: 1px solid #facc15;
  color: #fef3c7;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  box-shadow: 0 0 18px rgba(250, 204, 21, 0.35);
  backdrop-filter: blur(4px);
}
.wf-viz-banner strong { color: #fef9c3; }
.wf-viz-banner-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #facc15;
  box-shadow: 0 0 10px #facc15;
  animation: wfPulse 1.4s ease-in-out infinite;
}

@keyframes wfPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.6; transform: scale(1.25); }
}
</style>
