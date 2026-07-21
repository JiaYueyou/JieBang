<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import Graph from 'graphology'
import type { GraphNode, GraphType } from '@/domain/types'

const props = defineProps<{
  graph: Graph | null
  highlightedPath?: string[]
}>()

const emit = defineEmits<{
  (e: 'nodeClick', node: GraphNode | null): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
let g6Instance: any = null

onMounted(async () => {
  await nextTick()
  
  if (!containerRef.value || !props.graph) {
    console.log('GraphCanvas: container or graph is null')
    return
  }

  await initG6()
})

async function initG6() {
  const G6 = await import('@antv/g6')
  
  const nodes: any[] = []
  const edges: any[] = []
  
  props.graph?.forEachNode((nodeId: string, attrs: any) => {
    nodes.push({
      id: nodeId,
      data: {
        name: attrs.name || attrs.label || '',
        type: attrs.type,
        level: attrs.level,
        description: attrs.description || '',
        stack: attrs.stack || '',
        frequency: attrs.frequency || 0,
        level_label: attrs.level_label || '',
        total_records: attrs.total_records || 0,
        ...attrs
      },
      style: {
        x: attrs.x || Math.random() * 800 + 50,
        y: attrs.y || Math.random() * 500 + 50,
        size: attrs.size || 20,
        fill: attrs.color || '#4f6ef6',
        stroke: '#ffffff',
        lineWidth: 2,
        labelText: attrs.name || attrs.label || '',
        labelFontSize: attrs.size ? Math.max(10, attrs.size / 2) : 12,
        labelFill: '#1a1d28',
        labelPosition: 'bottom',
        labelOffset: (attrs.size || 20) / 2 + 8
      }
    })
  })
  
  props.graph?.forEachEdge((edgeId: string, attrs: any, source: string, target: string) => {
    edges.push({
      id: edgeId,
      source,
      target,
      data: {
        relation: attrs.relation || '',
        label: attrs.label || ''
      },
      style: {
        stroke: attrs.color || 'rgba(79,110,246,0.3)',
        lineWidth: 1
      }
    })
  })

  console.log('GraphCanvas: nodes', nodes.length, 'edges', edges.length)

  const width = containerRef.value!.clientWidth
  const height = containerRef.value!.clientHeight

  g6Instance = new G6.Graph({
    container: containerRef.value!,
    width,
    height,
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    autoFit: 'view',
    node: {
      type: 'circle',
      style: {
        fill: '#4f6ef6',
        stroke: '#ffffff',
        lineWidth: 2,
        labelFill: '#1a1d28',
        labelFontSize: 12
      }
    },
    edge: {
      style: {
        stroke: 'rgba(79,110,246,0.3)',
        lineWidth: 1
      }
    },
    layout: {
      type: 'force',
      preventOverlap: true,
      nodeSize: (d: any) => d.style.size || 20,
      linkDistance: 120,
      nodeStrength: -200,
      edgeStrength: 2,
      collisionStrength: 0.8,
      repulsion: 200,
      gravity: 0.1,
      damping: 0.9
    }
  })

  g6Instance.setData({ nodes, edges })
  g6Instance.render()

  g6Instance.on('node:click', (e: any) => {
    const node = e.item?.getModel()
    if (node) {
      const nodeData = {
        ...node.data,
        ...node.style,
        id: node.id,
        name: node.data?.name || '',
        type: node.data?.type || 'Job',
        level: node.data?.level || '',
        x: node.style?.x || 0,
        y: node.style?.y || 0,
        description: node.data?.description || '',
        size: node.style?.size || 20,
        color: node.style?.fill || '#4f6ef6'
      }
      emit('nodeClick', nodeData as GraphNode)
    }
  })

  g6Instance.on('canvas:click', () => {
    emit('nodeClick', null)
  })

  window.addEventListener('resize', handleResize)
}

function handleResize() {
  if (g6Instance && containerRef.value) {
    const width = containerRef.value.clientWidth
    const height = containerRef.value.clientHeight
    g6Instance.changeSize(width, height)
  }
}

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (g6Instance) {
    g6Instance.destroy()
    g6Instance = null
  }
})

watch(() => props.graph, async (newGraph) => {
  await nextTick()
  
  if (!containerRef.value) return
  
  if (g6Instance) {
    g6Instance.destroy()
    g6Instance = null
  }

  if (newGraph) {
    await initG6()
  }
})
</script>

<template>
  <div ref="containerRef" class="sigma-container"></div>
</template>

<style scoped>
.sigma-container {
  width: 100%;
  height: 100%;
  min-height: 600px;
  background:
    radial-gradient(circle at 50% 20%, rgba(79,110,246,.06), transparent 34%),
    var(--color-bg-base);
  cursor: grab;
  position: relative;
  overflow: hidden;
}

.sigma-container:active {
  cursor: grabbing;
}
</style>
