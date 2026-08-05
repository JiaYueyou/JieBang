import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import Graph from 'graphology'
import { getPanorama, getNodeDetail, expandNode, searchNodes, getPath, getJobTree, enrichSkill } from '@/api/graph'
import { buildGraphFromSubgraph, mergeSubgraph } from '@/data/graphBuilder'

const INITIAL_LIMIT = 50
const LOAD_MORE_STEPS = [150, 500, 1000]

export const useGraphStore = defineStore('graph', () => {
  // 核心图数据（graphology Graph 实例）
  const graph = ref<Graph>(new Graph())

  // 统计
  const nodeCount = computed(() => graph.value.order)
  const edgeCount = computed(() => graph.value.size)
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref('')

  // 渐进加载
  const currentLimit = ref(INITIAL_LIMIT)
  const hasMore = ref(true)
  const enrichingNodeId = ref<string | null>(null)
  const enrichedNodeIds = ref<Set<string>>(new Set())

  async function fetchPanorama(params?: {
    stack?: string; level?: string; node_type?: string; keyword?: string; limit?: number
  }, append = false) {
    loading.value = true
    error.value = ''
    try {
      const data = await getPanorama({ ...params, limit: params?.limit ?? currentLimit.value })
      if (append) {
        mergeSubgraph(graph.value, data)
      } else {
        graph.value = buildGraphFromSubgraph(data)
      }
      hasMore.value = data.truncated || data.nodes.length >= currentLimit.value
      loaded.value = true
      return data
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载图谱失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function loadMore() {
    const next = LOAD_MORE_STEPS.find(s => s > currentLimit.value)
    if (next) {
      currentLimit.value = next
    } else {
      currentLimit.value = 1000
      hasMore.value = false
    }
    await fetchPanorama({ limit: currentLimit.value })
  }

  async function enrichNode(nodeId: string) {
    if (enrichingNodeId.value) return
    enrichingNodeId.value = nodeId
    try {
      const data = await enrichSkill(nodeId)
      mergeSubgraph(graph.value, data)
      enrichedNodeIds.value = new Set([...enrichedNodeIds.value, nodeId])
      return data
    } finally {
      enrichingNodeId.value = null
    }
  }

  async function fetchNodeDetail(nodeId: string) {
    const data = await getNodeDetail(nodeId)
    mergeSubgraph(graph.value, data)
    return data
  }

  async function expand(nodeId: string, depth = 2) {
    loading.value = true
    try {
      const data = await expandNode(nodeId, depth)
      mergeSubgraph(graph.value, data)
      return data
    } finally {
      loading.value = false
    }
  }

  async function search(query: string, type?: string) {
    loading.value = true
    try {
      const data = await searchNodes(query, type)
      graph.value = buildGraphFromSubgraph(data)
      return data
    } finally {
      loading.value = false
    }
  }

  async function findPath(fromId: string, toId: string) {
    loading.value = true
    try {
      const data = await getPath(fromId, toId)
      graph.value = buildGraphFromSubgraph(data)
      return data
    } finally {
      loading.value = false
    }
  }

  async function fetchJobTree(jobId: number, depth = 5) {
    loading.value = true
    try {
      const data = await getJobTree(jobId, depth)
      graph.value = buildGraphFromSubgraph(data)
      return data
    } finally {
      loading.value = false
    }
  }

  return {
    graph, nodeCount, edgeCount, loading, loaded, error,
    currentLimit, hasMore, enrichingNodeId, enrichedNodeIds,
    fetchPanorama, loadMore, enrichNode,
    fetchNodeDetail, expand, search, findPath, fetchJobTree,
  }
})
