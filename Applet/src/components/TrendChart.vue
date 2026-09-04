<script setup lang="ts">
import { ref, watch, onUnmounted, getCurrentInstance } from 'vue'
import { onReady } from '@dcloudio/uni-app'

const props = withDefaults(
  defineProps<{
    /** x 轴标签 */
    labels: string[]
    /** 双序列：主（岗位入库）+ 副（匹配评估） */
    series: { name: string; color: string; data: number[] }[]
    height?: number
  }>(),
  { height: 380 },
)

const canvasId = 'trend-canvas'
const ready = ref(false)

let canvas: any = null
let ctx: any = null
let cssW = 0
let cssH = 0
let rafId = 0
let instance: any = null

onReady(() => {
  instance = getCurrentInstance()
  setTimeout(initCanvas, 80)
})

onUnmounted(() => {
  if (rafId && canvas?.cancelAnimationFrame) canvas.cancelAnimationFrame(rafId)
})

watch(
  () => props.series,
  () => {
    if (ready.value) startLoop()
  },
  { deep: true },
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
      startLoop()
    })
}

function startLoop() {
  if (!canvas?.requestAnimationFrame) {
    drawFrame(1)
    return
  }
  if (rafId) canvas.cancelAnimationFrame(rafId)
  const start = Date.now()
  const tick = () => {
    const t = Math.min(1, (Date.now() - start) / 750)
    drawFrame(1 - Math.pow(1 - t, 3))
    if (t < 1) rafId = canvas.requestAnimationFrame(tick)
  }
  rafId = canvas.requestAnimationFrame(tick)
}

/* 平滑曲线：相邻中点二次贝塞尔 */
function tracePath(points: { x: number; y: number }[]) {
  ctx.beginPath()
  ctx.moveTo(points[0].x, points[0].y)
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1]
    const cur = points[i]
    const mx = (prev.x + cur.x) / 2
    ctx.quadraticCurveTo(mx, prev.y, mx, (prev.y + cur.y) / 2)
    ctx.quadraticCurveTo(mx, cur.y, cur.x, cur.y)
  }
}

function drawFrame(t: number) {
  if (!ctx) return
  const padL = 34
  const padR = 14
  const padT = 18
  const padB = 30
  const w = cssW - padL - padR
  const h = cssH - padT - padB

  const all = props.series.flatMap((s) => s.data)
  const max = Math.max(...all, 10) * 1.15
  const n = props.labels.length

  ctx.clearRect(0, 0, cssW, cssH)

  // 横向网格 + y 轴刻度
  ctx.strokeStyle = 'rgba(26, 29, 40, 0.06)'
  ctx.lineWidth = 1
  ctx.fillStyle = '#989eae'
  ctx.font = '9px "DIN Alternate", monospace'
  ctx.textAlign = 'right'
  for (let i = 0; i <= 3; i++) {
    const y = padT + (h * i) / 3
    ctx.beginPath()
    ctx.moveTo(padL, y)
    ctx.lineTo(cssW - padR, y)
    ctx.stroke()
    ctx.fillText(String(Math.round((max * (3 - i)) / 3)), padL - 6, y + 3)
  }

  // x 轴标签
  ctx.textAlign = 'center'
  const step = Math.ceil(n / 5)
  for (let i = 0; i < n; i += step) {
    const x = padL + (w * i) / (n - 1)
    ctx.fillText(props.labels[i], x, cssH - 10)
  }

  // 序列
  for (const s of props.series) {
    const pts = s.data.map((v, i) => ({
      x: padL + (w * i) / (n - 1),
      y: padT + h - (v / max) * h,
    }))

    // 渐变面积
    const grad = ctx.createLinearGradient(0, padT, 0, padT + h)
    grad.addColorStop(0, s.color + '3d')
    grad.addColorStop(1, s.color + '00')
    tracePath(pts)
    ctx.lineTo(pts[pts.length - 1].x, padT + h)
    ctx.lineTo(pts[0].x, padT + h)
    ctx.closePath()
    ctx.fillStyle = grad
    ctx.fill()

    // 折线（按进度绘制）
    ctx.beginPath()
    ctx.strokeStyle = s.color
    ctx.lineWidth = 2.4
    ctx.lineJoin = 'round'
    ctx.lineCap = 'round'
    const visible = 1 + (pts.length - 1) * t
    tracePath(pts.slice(0, Math.ceil(visible)))
    ctx.stroke()

    // 末端点
    if (t >= 1) {
      const last = pts[pts.length - 1]
      ctx.fillStyle = s.color
      ctx.beginPath()
      ctx.arc(last.x, last.y, 3.4, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 1.6
      ctx.stroke()
    }
  }
}
</script>

<template>
  <view class="trend-wrap" :style="{ height: height + 'rpx' }">
    <canvas :id="canvasId" type="2d" class="trend-canvas" />
    <view v-if="!ready" class="skeleton" style="position: absolute; inset: 20rpx; border-radius: 16rpx" />
  </view>
</template>

<style lang="scss" scoped>
.trend-wrap {
  position: relative;
  width: 100%;
}

.trend-canvas {
  width: 100%;
  height: 100%;
}
</style>
