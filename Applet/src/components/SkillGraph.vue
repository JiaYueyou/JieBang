<script setup lang="ts">
import { ref, watch, onUnmounted, getCurrentInstance } from 'vue'
import { onReady } from '@dcloudio/uni-app'
import type { GraphNode, GraphEdge } from '@/api/graph'

const props = defineProps<{
  nodes: GraphNode[]
  edges: GraphEdge[]
  /** 高亮的节点 id 列表（搜索命中） */
  highlights?: string[]
  selectedId?: string | null
}>()

const emit = defineEmits<{
  (e: 'select', node: GraphNode): void
}>()

const LAYER_COLORS = ['#122d6e', '#2f47b8', '#3f5ae0', '#7893de', '#b4c2f2']
const LAYER_RADII = [0, 0.32, 0.58, 0.8, 0.97]
const LAYER_NODE_R = [15, 12, 9, 7, 5.5]

interface RenderNode extends GraphNode {
  x: number
  y: number
  tx: number
  ty: number
  alpha: number
  isNew: boolean
}

const canvasId = 'skill-graph-canvas'
const ready = ref(false)

let canvas: any = null
let ctx: any = null
let cssW = 0
let cssH = 0
let rafId = 0
let animStart = 0
let renderNodes: RenderNode[] = []
let renderEdges: { s: RenderNode; t: RenderNode }[] = []
let instance: any = null

onReady(() => {
  instance = getCurrentInstance()
  setTimeout(initCanvas, 60)
})

onUnmounted(() => {
  if (rafId && canvas?.cancelAnimationFrame) canvas.cancelAnimationFrame(rafId)
})

watch(
  () => [props.nodes, props.edges, props.highlights],
  () => {
    if (ready.value) rebuild(false)
  },
)

function initCanvas() {
  const query = uni.createSelectorQuery().in(instance)
  ;(query.select(`#${canvasId}`) as any)
    .fields({ node: true, size: true })
    .exec((res: any) => {
      if (!res?.[0]?.node) return
      canvas = res[0].node
      cssW = res[0].width
      cssH = res[0].height
      const dpr = uni.getWindowInfo().pixelRatio || 2
      canvas.width = cssW * dpr
      canvas.height = cssH * dpr
      ctx = canvas.getContext('2d')
      ctx.scale(dpr, dpr)
      ready.value = true
      rebuild(true)
    })
}

/* ── 布局：分层放射，同层等角分布，兄弟节点按父节点角度聚簇 ── */
function rebuild(initial: boolean) {
  const nodes = props.nodes
  if (!nodes.length || !ctx) return

  const layerOf = new Map(nodes.map((n) => [n.id, n.layer]))
  const prevPos = new Map(renderNodes.map((n) => [n.id, n]))

  const nodeAngle = new Map<string, number>()

  // 父节点 = 层级更小的端点
  function parentOf(id: string): string | null {
    for (const e of props.edges) {
      if (e.target === id && (layerOf.get(e.source) ?? 99) < layerOf.get(id)!) return e.source
      if (e.source === id && (layerOf.get(e.target) ?? 99) < layerOf.get(id)!) return e.target
    }
    return null
  }

  // 分层分组
  const layers = new Map<number, GraphNode[]>()
  for (const n of nodes) {
    if (!layers.has(n.layer)) layers.set(n.layer, [])
    layers.get(n.layer)!.push(n)
  }
  const layerKeys = [...layers.keys()].sort((a, b) => a - b)
  const ringOf = new Map<number, number>()
  layerKeys.forEach((k, i) => ringOf.set(k, i))
  const rings = Math.max(layerKeys.length - 1, 1)

  // 自顶向下：先给上层定角，再按父角度聚簇排序下层
  for (const k of layerKeys) {
    const group = layers.get(k)!
    if (k === layerKeys[0]) {
      group.forEach((n, i) => nodeAngle.set(n.id, (2 * Math.PI * i) / group.length))
      continue
    }
    const parentAngle = new Map<string, number>()
    for (const n of group) {
      const p = parentOf(n.id)
      parentAngle.set(n.id, p != null && nodeAngle.has(p) ? nodeAngle.get(p)! : Math.random() * Math.PI * 2)
    }
    group.sort((a, b) => parentAngle.get(a.id)! - parentAngle.get(b.id)!)
    group.forEach((n, i) => {
      nodeAngle.set(n.id, (2 * Math.PI * i) / group.length)
    })
  }

  const cx = cssW / 2
  const cy = cssH / 2
  const maxR = Math.min(cssW, cssH) / 2 - 36

  const next: RenderNode[] = nodes.map((n) => {
    const ring = ringOf.get(n.layer) ?? 0
    const r = maxR * LAYER_RADII[Math.min(ring, LAYER_RADII.length - 1)] * (rings === 0 ? 0 : 1)
    const angle = nodeAngle.get(n.id) ?? Math.random() * Math.PI * 2
    const prev = prevPos.get(n.id)
    return {
      ...n,
      x: prev ? prev.x : cx + Math.cos(angle) * r,
      y: prev ? prev.y : cy + Math.sin(angle) * r,
      tx: cx + Math.cos(angle) * r,
      ty: cy + Math.sin(angle) * r,
      alpha: prev ? prev.alpha : initial ? 0 : 0.1,
      isNew: !prev,
    }
  })

  const nodeMap = new Map(next.map((n) => [n.id, n]))
  renderNodes = next
  renderEdges = props.edges
    .map((e) => {
      const s = nodeMap.get(e.source)
      const t = nodeMap.get(e.target)
      return s && t ? { s, t } : null
    })
    .filter(Boolean) as typeof renderEdges

  animStart = Date.now()
  startLoop()
}

/* ── 渲染循环 ── */
function startLoop() {
  if (!canvas?.requestAnimationFrame) {
    drawFrame(1)
    return
  }
  if (rafId) canvas.cancelAnimationFrame(rafId)
  const tick = () => {
    const t = Math.min(1, (Date.now() - animStart) / 650)
    drawFrame(easeOutQuart(t))
    if (t < 1) rafId = canvas.requestAnimationFrame(tick)
  }
  rafId = canvas.requestAnimationFrame(tick)
}

function easeOutQuart(t: number) {
  return 1 - Math.pow(1 - t, 4)
}

function drawFrame(t: number) {
  if (!ctx) return
  const cx = cssW / 2
  const cy = cssH / 2
  const maxR = Math.min(cssW, cssH) / 2 - 36
  const highlightSet = new Set(props.highlights ?? [])
  const now = Date.now()

  ctx.clearRect(0, 0, cssW, cssH)

  // 背景同心环
  ctx.strokeStyle = 'rgba(122, 143, 222, 0.14)'
  ctx.lineWidth = 1
  for (let i = 1; i <= 4; i++) {
    ctx.beginPath()
    ctx.arc(cx, cy, maxR * LAYER_RADII[i], 0, Math.PI * 2)
    ctx.stroke()
  }

  // 插值节点位置
  for (const n of renderNodes) {
    n.x = n.x + (n.tx - n.x) * t
    n.y = n.y + (n.ty - n.y) * t
    n.alpha = Math.min(1, n.alpha + 0.06 * t + 0.015)
  }

  // 边
  ctx.lineWidth = 1
  for (const e of renderEdges) {
    const grad = ctx.createLinearGradient(e.s.x, e.s.y, e.t.x, e.t.y)
    grad.addColorStop(0, 'rgba(47, 71, 184, 0.20)')
    grad.addColorStop(1, 'rgba(180, 194, 242, 0.32)')
    ctx.strokeStyle = grad
    ctx.beginPath()
    ctx.moveTo(e.s.x, e.s.y)
    ctx.lineTo(e.t.x, e.t.y)
    ctx.stroke()
  }

  // 节点
  for (const n of renderNodes) {
    const ringIdx = Math.min(Math.max(n.layer - 1, 0), LAYER_NODE_R.length - 1)
    const r = LAYER_NODE_R[ringIdx]
    ctx.globalAlpha = n.alpha
    const color = LAYER_COLORS[ringIdx]

    if (highlightSet.has(n.id)) {
      const pulse = 3 + Math.sin(now / 240) * 2
      ctx.strokeStyle = 'rgba(79, 110, 246, 0.85)'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(n.x, n.y, r + pulse + 2, 0, Math.PI * 2)
      ctx.stroke()
    }

    if (props.selectedId === n.id) {
      ctx.strokeStyle = 'rgba(79, 110, 246, 0.9)'
      ctx.lineWidth = 2.5
      ctx.beginPath()
      ctx.arc(n.x, n.y, r + 6, 0, Math.PI * 2)
      ctx.stroke()
      ctx.fillStyle = 'rgba(79, 110, 246, 0.14)'
      ctx.beginPath()
      ctx.arc(n.x, n.y, r + 11, 0, Math.PI * 2)
      ctx.fill()
    }

    if (ringIdx === 0) {
      const glow = ctx.createRadialGradient(n.x, n.y, 2, n.x, n.y, r * 2.6)
      glow.addColorStop(0, 'rgba(18, 45, 110, 0.22)')
      glow.addColorStop(1, 'rgba(18, 45, 110, 0)')
      ctx.fillStyle = glow
      ctx.beginPath()
      ctx.arc(n.x, n.y, r * 2.6, 0, Math.PI * 2)
      ctx.fill()
    }

    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2)
    ctx.fill()

    if (ringIdx >= 3) {
      ctx.strokeStyle = 'rgba(255,255,255,0.9)'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }

    ctx.fillStyle = ringIdx === 0 ? '#1a1d28' : '#5a5f6e'
    const fontSize = ringIdx === 0 ? 13 : ringIdx === 1 ? 12 : 10.5
    ctx.font = `${ringIdx <= 1 ? 600 : 400} ${fontSize}px -apple-system, sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    const label = n.label.length > 6 ? n.label.slice(0, 6) + '…' : n.label
    ctx.fillText(label, n.x, n.y + r + 3)
    ctx.globalAlpha = 1
  }
}

/* ── 触摸拾取 ── */
function onTouchStart(e: any) {
  const touch = e.touches?.[0] ?? e.changedTouches?.[0]
  if (!touch) return
  const x = touch.x ?? touch.clientX ?? 0
  const y = touch.y ?? touch.clientY ?? 0
  let best: RenderNode | null = null
  let bestD = 26 * 26
  for (const n of renderNodes) {
    const dx = n.x - x
    const dy = n.y - y
    const d = dx * dx + dy * dy
    if (d < bestD) {
      bestD = d
      best = n
    }
  }
  if (best) {
    emit('select', {
      id: best.id,
      label: best.label,
      type: best.type,
      layer: best.layer,
      root_id: best.root_id,
    })
  }
}

defineExpose({ initCanvas })
</script>

<template>
  <view class="graph-wrap">
    <canvas :id="canvasId" type="2d" class="graph-canvas" @touchstart="onTouchStart" />
    <view v-if="!ready" class="graph-loading">
      <view class="skeleton" style="width: 70%; height: 24rpx" />
      <view class="skeleton" style="width: 50%; height: 24rpx; margin-top: 16rpx" />
    </view>
  </view>
</template>

<style lang="scss" scoped>
.graph-wrap {
  position: relative;
  height: 860rpx;
  margin: 0 32rpx;
  background: $card;
  border-radius: $radius-lg;
  border: 1rpx solid rgba(232, 235, 240, 0.7);
  overflow: hidden;
}

.graph-canvas {
  width: 100%;
  height: 100%;
}

.graph-loading {
  position: absolute;
  top: 40rpx;
  left: 48rpx;
}
</style>
