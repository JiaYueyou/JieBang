<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import Graph from 'graphology'
import type { GraphNode, GraphType } from '@/domain/types'

const props = defineProps<{
  graph: Graph | null
  highlightedPath?: string[]
  highlightedNodeIds?: string[]
  selectedNodeId?: string | null
  pathNodeIds?: string[]
}>()

const emit = defineEmits<{
  (e: 'nodeClick', node: GraphNode | null): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const levelColors: Record<string, string> = {
  'L1': '#122d6e',
  'L2': '#2f47b8',
  'L3': '#3f5ae0',
  'L4': '#7893de',
  'L5': '#b4c2f2'
}

const levelSizes: Record<string, number> = {
  'L1': 30,
  'L2': 24,
  'L3': 19,
  'L4': 18,
  'L5': 16
}

const levelFontSizes: Record<string, number> = {
  'L1': 12,
  'L2': 11,
  'L3': 10,
  'L4': 10,
  'L5': 10
}

onMounted(async () => {
  await nextTick()
  
  if (!containerRef.value) return
  
  await initChart()
})

async function initChart() {
  if (!containerRef.value) return
  
  chartInstance = echarts.init(containerRef.value)
  
  const option = buildOption()
  chartInstance.setOption(option)
  enableFullCanvasRoaming()
  
  chartInstance.on('click', (params: any) => {
    if (params.dataType === 'node') {
      const nodeData = params.data
      const graphNode: GraphNode = {
        id: nodeData.id,
        name: nodeData.name,
        type: (nodeData.type || 'Job') as GraphType,
        level: nodeData.level || '',
        x: nodeData.x || 0,
        y: nodeData.y || 0,
        description: nodeData.description || '',
        color: nodeData.color || '#4f6ef6',
        size: nodeData.size || 20,
        stack: (nodeData.stack || null) as 'ai' | 'backend' | 'data' | 'devops' | null,
        importance: nodeData.importance || 0,
        frequency: nodeData.frequency || 0,
        level_label: nodeData.level_label || '',
        total_records: nodeData.total_records || 0,
        category_key: nodeData.category_key || '',
        job_count: nodeData.job_count || 0,
        category: nodeData.category || '',
        parent_skill: nodeData.parent_skill || '',
        parent_tech_point: nodeData.parent_tech_point || '',
        difficulty: nodeData.difficulty || '',
        prerequisites: nodeData.prerequisites || [],
        evidence_ids: nodeData.evidence_ids || [],
        source_count: nodeData.source_count || 0,
        core_stack: nodeData.core_stack || [],
        common_solutions: nodeData.common_solutions || []
      }
      emit('nodeClick', graphNode)
      
      updateChart()
    } else {
      emit('nodeClick', null)
    }
  })
  
  window.addEventListener('resize', handleResize)
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
  
  levelCategories.forEach((cat, index) => {
    categories.push({
      name: cat.name,
      itemStyle: cat.itemStyle
    })
  })
  
  const levelToCategoryIndex: Record<string, number> = {
    'L1': 0,
    'L2': 1,
    'L3': 2,
    'L4': 3,
    'L5': 4
  }
  const searchMatches = new Set(props.highlightedNodeIds || [])
  const hasSearchMatches = searchMatches.size > 0
  const selectedId = props.selectedNodeId ?? null
  const hasSelected = Boolean(selectedId)
  const pathSet = new Set(props.pathNodeIds || [])
  
  props.graph?.forEachNode((nodeId: string, attrs: any) => {
    const level = attrs.level || 'L3'
    const size = attrs.size || levelSizes[level] || 20
    const color = attrs.color || levelColors[level] || '#4f6ef6'
    const categoryIndex = levelToCategoryIndex[level] || 2
    const isHighlighted = props.highlightedPath?.includes(nodeId)
    const isSearchMatch = searchMatches.has(nodeId)
    const isSelected = hasSelected && nodeId === selectedId
    // Selection takes precedence over search: its complete L1→L5 path keeps its original
    // colour, and every unrelated node is consistently reduced to 0.22 opacity.
    const isProminent = isSelected || (!hasSelected && isSearchMatch)
    const dimmed = hasSelected
      ? !isSelected && !pathSet.has(nodeId)
      : hasSearchMatches && !isSearchMatch
    
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
      itemStyle: {
        color: isProminent ? '#f59e4b' : color,
        borderColor: isProminent ? '#fff7ed' : '#ffffff',
        borderWidth: isProminent ? 4 : 2,
        opacity: dimmed ? 0.22 : isHighlighted || isSelected ? 1 : 0.9,
        shadowBlur: isProminent ? 30 : isHighlighted ? 20 : 10,
        shadowColor: isProminent ? 'rgba(245, 158, 75, 0.85)' : isHighlighted ? 'rgba(79, 110, 246, 0.7)' : 'rgba(0, 0, 0, 0.2)',
        shadowOffsetY: 3
      },
      symbolSize: isProminent ? size * 1.45 : size,
      label: {
        show: true,
        position: 'bottom',
        distance: 8,
        fontSize: levelFontSizes[level] || 12,
        color: isProminent ? '#b45309' : '#1a1d28',
        formatter: (params: any) => params.name,
        fontWeight: 'bold',
        opacity: dimmed ? 0.2 : 1
      },
      zlevel: isSelected ? 10 : level === 'L1' ? 5 : level === 'L2' ? 4 : level === 'L3' ? 3 : level === 'L4' ? 2 : 1
    })
  })
  
  props.graph?.forEachEdge((edgeId: string, attrs: any, source: string, target: string) => {
    links.push({
      source: source,
      target: target,
      relation: attrs.relation || '',
      lineStyle: {
        color: 'rgba(79, 110, 246, 0.4)',
        width: 1.5,
        curveness: 0.1
      }
    })
  })

  const isolatedLayout = links.length === 0
  if (isolatedLayout && nodes.length) {
    const columns = Math.max(1, Math.ceil(Math.sqrt(nodes.length * 1.6)))
    nodes.forEach((node, index) => {
      node.x = (index % columns) * 220
      node.y = Math.floor(index / columns) * 130
    })
  }

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      padding: [12, 16],
      textStyle: {
        color: '#1a1d28',
        fontSize: 14
      },
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const data = params.data
          return `<div style="font-weight: bold; margin-bottom: 8px; color: ${data.itemStyle.color}">${data.name}</div>
                  <div>类型: ${data.type}</div>
                  <div>层级: ${data.level}</div>
                  <div>${data.description || ''}</div>`
        } else if (params.dataType === 'edge') {
          return `<div>关系: ${params.data.relation || '关联'}</div>`
        }
        return ''
      }
    },
    legend: {
      show: true,
      data: levelCategories.map(c => c.name),
      top: 10,
      right: 20,
      textStyle: {
        color: '#64748b',
        fontSize: 12
      },
      itemWidth: 16,
      itemHeight: 16
    },
    series: [{
      type: 'graph',
      layout: isolatedLayout ? 'none' : 'force',
      roam: true,
      draggable: true,
      animation: true,
      animationDuration: 1500,
      animationEasingUpdate: 'quinticInOut',
      focusNodeAdjacency: true,
      data: nodes,
      links: links,
      categories: categories,
      force: {
        repulsion: 250,
        gravity: 0.1,
        edgeLength: [100, 200],
        edgeForce: 0.5,
        friction: 0.6
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          width: 3,
          color: '#4f6ef6'
        },
        itemStyle: {
          borderWidth: 4,
          shadowBlur: 25,
          shadowColor: 'rgba(79, 110, 246, 0.7)',
          shadowOffsetY: 5
        },
        label: {
          show: true,
          fontSize: 14,
          opacity: 1
        }
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
  const option = buildOption()
  chartInstance.setOption(option, { notMerge: false, lazyUpdate: false })
  enableFullCanvasRoaming()
}

/** Keep the current zoom and pan the requested graph node into the canvas centre. */
function centerNode(nodeId: string) {
  if (!chartInstance || !containerRef.value) return

  const seriesModel = (chartInstance as any).getModel()?.getSeriesByIndex(0)
  const data = seriesModel?.getData?.()
  const coordinateSystem = seriesModel?.coordinateSystem
  if (!data || !coordinateSystem) return

  const index = data.indexOfName(nodeId)
  const layout = index >= 0 ? data.getItemLayout(index) : null
  if (!layout) return

  const [x, y] = coordinateSystem.dataToPoint(layout)
  chartInstance.dispatchAction({
    type: 'graphRoam',
    seriesIndex: 0,
    dx: containerRef.value.clientWidth / 2 - x,
    dy: containerRef.value.clientHeight / 2 - y
  })
}

/** Public API used by the details panel when navigating a parent or child node. */
function focusNode(nodeId: string) {
  requestAnimationFrame(() => {
    centerNode(nodeId)
    // Force layout may complete shortly after the graph is re-created for a new scope.
    window.setTimeout(() => centerNode(nodeId), 220)
  })
}

function enableFullCanvasRoaming() {
  if (!chartInstance || !containerRef.value) return
  const seriesModel = (chartInstance as any).getModel()?.getSeriesByIndex(0)
  const coordinateSystem = seriesModel?.coordinateSystem
  if (!coordinateSystem) return

  // ECharts' graph roam controller normally checks the transformed node data
  // bounds, which leaves the sides of a wide canvas inactive. Keep its native
  // drag/zoom implementation but expand only the hit-test area to the canvas.
  coordinateSystem.containPoint = ([x, y]: [number, number]) => (
    x >= 0
    && y >= 0
    && x <= containerRef.value!.clientWidth
    && y <= containerRef.value!.clientHeight
  )
}

function handleResize() {
  if (chartInstance && containerRef.value) {
    chartInstance.resize()
  }
}

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

watch(() => props.graph, async (newGraph) => {
  await nextTick()
  
  if (!containerRef.value) return
  
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  
  if (newGraph) {
    await initChart()
  }
}, { deep: true })

watch(() => props.highlightedPath, async () => {
  await nextTick()
  if (chartInstance && props.graph) {
    chartInstance.dispose()
    chartInstance = null
    await initChart()
  }
})

watch(() => props.highlightedNodeIds, async () => {
  await nextTick()
  updateChart()
}, { deep: true })

watch(() => props.selectedNodeId, async () => {
  await nextTick()
  updateChart()
})

watch(() => props.pathNodeIds, async () => {
  await nextTick()
  updateChart()
}, { deep: true })

defineExpose({ focusNode })

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
