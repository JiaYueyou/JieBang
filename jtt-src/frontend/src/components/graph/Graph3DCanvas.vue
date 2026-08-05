<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import Graph from 'graphology'

// 图谱节点属性（graphology 中存储的 attributes）
export interface GraphNodeAttrs {
  id: string; name: string; label?: string
  type: string; level: string; stack?: string
  x: number; y: number; z?: number
  description: string; importance?: number; frequency?: number
  color?: string; size?: number
  level_label?: string; total_records?: number
  category_key?: string; job_count?: number; category?: string
  parent_skill?: string; parent_tech_point?: string
  difficulty?: string; prerequisites?: string[]
  evidence_ids?: number[]; evidenceIds?: number[]
  source_count?: number; sourceCount?: number
  core_stack?: string[]; common_solutions?: Array<{ name: string; purpose: string }>
}

const props = defineProps<{
  graph: Graph | null
  highlightedPath?: string[]
  highlightedNodeIds?: string[]
  pinnedNodeIds?: string[]
}>()

const emit = defineEmits<{
  (e: 'nodeClick', node: GraphNodeAttrs | null): void
  (e: 'nodePin', nodeId: string, pinned: boolean): void
}>()

const pinnedNodes = ref<Set<string>>(new Set(props.pinnedNodeIds || []))

const containerRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const levelColors: Record<string, string> = {
  'L1': '#122d6e', 'L2': '#2f47b8', 'L3': '#3f5ae0',
  'L4': '#7893de', 'L5': '#b4c2f2'
}

const levelSizes: Record<string, number> = {
  'L1': 30, 'L2': 24, 'L3': 19, 'L4': 18, 'L5': 16
}

const levelFontSizes: Record<string, number> = {
  'L1': 12, 'L2': 11, 'L3': 10, 'L4': 10, 'L5': 10
}

onMounted(async () => {
  await nextTick()
  if (!containerRef.value) return
  await initChart()
})

async function initChart() {
  if (!containerRef.value) return
  chartInstance = echarts.init(containerRef.value)
  chartInstance.setOption(buildOption())
  enableFullCanvasRoaming()

  chartInstance.on('click', (params: any) => {
    if (params.dataType === 'node') {
      const nodeId = params.data.id
      const nextPinned = !pinnedNodes.value.has(nodeId)
      pinnedNodes.value.clear()
      if (nextPinned) pinnedNodes.value.add(nodeId)
      pinnedNodes.value = new Set(pinnedNodes.value)

      emit('nodePin', nodeId, nextPinned)
      emit('nodeClick', params.data as GraphNodeAttrs)
      updateChart()
    } else {
      emit('nodeClick', null)
    }
  })

  resizeObserver = new ResizeObserver(() => {
    if (chartInstance && containerRef.value) chartInstance.resize()
  })
  resizeObserver.observe(containerRef.value)
}

function buildOption(): any {
  const nodes: any[] = []
  const links: any[] = []
  const categories: any[] = []

  const levelCategories = [
    { name: 'L1 Job', itemStyle: { color: '#122d6e' } },
    { name: 'L2 SkillArea', itemStyle: { color: '#2f47b8' } },
    { name: 'L3 TechStack', itemStyle: { color: '#3f5ae0' } },
    { name: 'L4 TechPoint', itemStyle: { color: '#7893de' } },
    { name: 'L5 KnowledgePoint', itemStyle: { color: '#b4c2f2' } }
  ]

  levelCategories.forEach(cat => categories.push({ name: cat.name, itemStyle: cat.itemStyle }))

  const levelToCategoryIndex: Record<string, number> = {
    'L1': 0, 'L2': 1, 'L3': 2, 'L4': 3, 'L5': 4
  }
  const searchMatches = new Set(props.highlightedNodeIds || [])
  const hasSearchMatches = searchMatches.size > 0

  props.graph?.forEachNode((nodeId: string, attrs: any) => {
    const level = attrs.level || 'L3'
    const size = attrs.size || levelSizes[level] || 20
    const color = attrs.color || levelColors[level] || '#4f6ef6'
    const categoryIndex = levelToCategoryIndex[level] || 2
    const isHighlighted = props.highlightedPath?.includes(nodeId)
    const isSearchMatch = searchMatches.has(nodeId)
    const isPinned = pinnedNodes.value.has(nodeId)
    const pinnedSize = isPinned ? size * 1.2 : size

    nodes.push({
      id: nodeId,
      name: attrs.name || attrs.label || '',
      type: attrs.type,
      level: level,
      category: categoryIndex,
      description: attrs.description || '',
      stack: attrs.stack || '',
      frequency: attrs.frequency || 0,
      level_label: attrs.level_label || '',
      total_records: attrs.total_records || 0,
      category_key: attrs.category_key || '',
      job_count: attrs.job_count || 0,
      parent_skill: attrs.parent_skill || '',
      parent_tech_point: attrs.parent_tech_point || '',
      difficulty: attrs.difficulty || '',
      prerequisites: attrs.prerequisites || [],
      evidence_ids: attrs.evidence_ids || attrs.evidenceIds || [],
      source_count: attrs.source_count || attrs.sourceCount || 0,
      core_stack: attrs.core_stack || [],
      common_solutions: attrs.common_solutions || [],
      x: attrs.x || (Math.random() - 0.5) * 800,
      y: attrs.y || (Math.random() - 0.5) * 600,
      fixed: isPinned,
      itemStyle: {
        color: isPinned || isSearchMatch ? '#f59e4b' : color,
        borderColor: isSearchMatch ? '#fff7ed' : '#ffffff',
        borderWidth: isPinned || isSearchMatch ? 4 : 2,
        opacity: hasSearchMatches && !isSearchMatch ? 0.22 : isHighlighted || isPinned ? 1 : 0.9,
        shadowBlur: isPinned || isSearchMatch ? 30 : isHighlighted ? 20 : 10,
        shadowColor: isPinned || isSearchMatch ? 'rgba(245, 158, 75, 0.85)' : isHighlighted ? 'rgba(79, 110, 246, 0.7)' : 'rgba(0, 0, 0, 0.2)',
        shadowOffsetY: isPinned ? 5 : 3
      },
      symbolSize: isSearchMatch ? pinnedSize * 1.45 : pinnedSize,
      label: {
        show: true,
        position: 'bottom',
        distance: isPinned ? 12 : 8,
        fontSize: isPinned ? (levelFontSizes[level] || 12) + 2 : levelFontSizes[level] || 12,
        color: isPinned || isSearchMatch ? '#b45309' : '#1a1d28',
        formatter: (p: any) => p.name,
        fontWeight: 'bold',
        opacity: hasSearchMatches && !isSearchMatch ? 0.2 : 1
      },
      zlevel: isPinned ? 10 : level === 'L1' ? 5 : level === 'L2' ? 4 : level === 'L3' ? 3 : level === 'L4' ? 2 : 1
    })
  })

  props.graph?.forEachEdge((_edgeId: string, attrs: any, source: string, target: string) => {
    const sourcePinned = pinnedNodes.value.has(source)
    const targetPinned = pinnedNodes.value.has(target)
    const hasPinnedNode = sourcePinned || targetPinned
    links.push({
      source, target,
      relation: attrs.relation || '',
      lineStyle: {
        color: hasPinnedNode ? 'rgba(245, 158, 75, 0.7)' : 'rgba(79, 110, 246, 0.4)',
        width: hasPinnedNode ? 2.5 : 1.5,
        curveness: 0.1
      }
    })
  })

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      padding: [12, 16],
      textStyle: { color: '#1a1d28', fontSize: 14 },
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const data = params.data
          const isPinned = pinnedNodes.value.has(data.id)
          return `<div style="font-weight: bold; margin-bottom: 8px; color: ${data.itemStyle.color}">${data.name}${isPinned ? ' 🔒' : ''}</div>
                  <div>类型: ${data.type}</div>
                  <div>层级: ${data.level}</div>
                  <div>${isPinned ? '状态: <span style="color: #f59e4b">已锁定，再次点击可取消</span>' : '提示: 点击锁定节点'}</div>
                  <div>${data.description || ''}</div>`
        } else if (params.dataType === 'edge') {
          return `<div>关系: ${params.data.relation || '关联'}</div>`
        }
        return ''
      }
    },
    legend: {
      show: true,
      data: levelCategories.slice(0, 3).map(c => c.name),
      top: 10, right: 20,
      textStyle: { color: '#64748b', fontSize: 12 },
      itemWidth: 16, itemHeight: 16
    },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      animation: true,
      animationDuration: 1500,
      animationEasingUpdate: 'quinticInOut',
      focusNodeAdjacency: true,
      data: nodes, links: links, categories: categories,
      force: {
        repulsion: 250,
        gravity: 0.1,
        edgeLength: [100, 200],
        edgeForce: 0.5,
        friction: 0.6
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 3, color: '#4f6ef6' },
        itemStyle: {
          borderWidth: 4,
          shadowBlur: 25,
          shadowColor: 'rgba(79, 110, 246, 0.7)',
          shadowOffsetY: 5
        },
        label: { show: true, fontSize: 14, opacity: 1 }
      },
      select: {
        itemStyle: {
          borderWidth: 4,
          borderColor: '#4f6ef6',
          shadowBlur: 30,
          shadowColor: 'rgba(79, 110, 246, 0.8)'
        }
      },
      lineStyle: {
        color: 'rgba(79, 110, 246, 0.3)',
        width: 1.5,
        curveness: 0.1
      },
      label: {
        show: true,
        position: 'bottom',
        fontSize: 12,
        color: '#1a1d28',
        formatter: (params: any) => params.name,
        fontWeight: 'bold',
        opacity: 0.8
      }
    }]
  }
}

function updateChart() {
  if (!chartInstance) return
  chartInstance.setOption(buildOption(), { notMerge: false, lazyUpdate: false })
  enableFullCanvasRoaming()
}

function enableFullCanvasRoaming() {
  if (!chartInstance || !containerRef.value) return
  const seriesModel = (chartInstance as any).getModel()?.getSeriesByIndex(0)
  const coordinateSystem = seriesModel?.coordinateSystem
  if (!coordinateSystem) return
  coordinateSystem.containPoint = ([x, y]: [number, number]) =>
    x >= 0 && y >= 0 && x <= containerRef.value!.clientWidth && y <= containerRef.value!.clientHeight
}

onUnmounted(() => {
  if (resizeObserver) { resizeObserver.disconnect(); resizeObserver = null }
  if (chartInstance) { chartInstance.dispose(); chartInstance = null }
})

watch(() => props.graph, async () => {
  await nextTick()
  if (!containerRef.value) return
  if (chartInstance) { chartInstance.dispose(); chartInstance = null }
  if (props.graph) await initChart()
}, { deep: true })

watch(() => props.highlightedPath, async () => {
  await nextTick()
  if (chartInstance && props.graph) {
    chartInstance.dispose(); chartInstance = null
    await initChart()
  }
})

watch(() => props.highlightedNodeIds, async () => {
  await nextTick()
  updateChart()
}, { deep: true })

watch(() => props.pinnedNodeIds, async (ids) => {
  pinnedNodes.value = new Set(ids || [])
  await nextTick()
  updateChart()
}, { deep: true })
</script>

<template>
  <div ref="containerRef" class="graph-3d-container"></div>
</template>

<style scoped>
.graph-3d-container {
  width: 100%;
  height: 100%;
  min-height: 0;
  background:
    radial-gradient(circle at 50% 20%, rgba(79,110,246,.06), transparent 34%),
    linear-gradient(180deg, rgba(248,250,252,1) 0%, rgba(241,245,249,1) 100%);
  cursor: grab;
  position: relative;
  overflow: hidden;
}

.graph-3d-container:active {
  cursor: grabbing;
}
</style>
