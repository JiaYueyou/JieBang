import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getPanorama, getNodeDetail, expandNode, searchNodes, getPath, getJobTree, enrichSkill } from '@/api/graph'
import type { Neo4jGraphNode, Neo4jGraphEdge } from '@/types'

const INITIAL_LIMIT = 50
const LOAD_MORE_STEPS = [150, 500, 1000]

export const useGraphStore = defineStore('graph', () => {
  const nodes = ref<Neo4jGraphNode[]>([])
  const edges = ref<Neo4jGraphEdge[]>([])
  const nodeCount = ref(0)
  const edgeCount = ref(0)
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref('')

  // 渐进加载
  const currentLimit = ref(INITIAL_LIMIT)
  const hasMore = ref(true)
  const enrichingNodeId = ref<string | null>(null)  // 正在富化的节点 ID
  const enrichedNodeIds = ref<Set<string>>(new Set())  // 已富化的节点

  async function fetchPanorama(params?: {
    stack?: string; level?: string; node_type?: string; keyword?: string; limit?: number
  }, append = false) {
    loading.value = true
    error.value = ''
    try {
      const data = await getPanorama({ ...params, limit: params?.limit ?? currentLimit.value })
      if (append) {
        // 合并新节点（去重）
        const existingIds = new Set(nodes.value.map(n => n.id))
        for (const n of data.nodes) {
          if (!existingIds.has(n.id)) nodes.value.push(n)
        }
        for (const e of data.edges) {
          if (!edges.value.some(x => x.id === e.id)) edges.value.push(e)
        }
      } else {
        nodes.value = data.nodes
        edges.value = data.edges
      }
      nodeCount.value = data.node_count
      edgeCount.value = data.edge_count
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
    // 步进到下一档 limit
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
    if (enrichingNodeId.value) return  // 防止并发
    enrichingNodeId.value = nodeId
    try {
      const data = await enrichSkill(nodeId)
      // 合并新生成的 L4/L5 节点和边
      const existingIds = new Set(nodes.value.map(n => n.id))
      for (const n of data.nodes) {
        if (!existingIds.has(n.id)) nodes.value.push(n)
      }
      for (const e of data.edges) {
        if (!edges.value.some(x => x.id === e.id)) edges.value.push(e)
      }
      enrichedNodeIds.value = new Set([...enrichedNodeIds.value, nodeId])
      nodeCount.value = nodes.value.length
      edgeCount.value = edges.value.length
      return data
    } finally {
      enrichingNodeId.value = null
    }
  }

  async function fetchNodeDetail(nodeId: string) {
    const data = await getNodeDetail(nodeId)
    nodes.value = data.nodes
    edges.value = data.edges
    return data
  }

  async function expand(nodeId: string, depth = 2) {
    loading.value = true
    try {
      const data = await expandNode(nodeId, depth)
      nodes.value = data.nodes
      edges.value = data.edges
      return data
    } finally {
      loading.value = false
    }
  }

  async function search(query: string, type?: string) {
    loading.value = true
    try {
      const data = await searchNodes(query, type)
      nodes.value = data.nodes
      edges.value = data.edges
      return data
    } finally {
      loading.value = false
    }
  }

  async function findPath(fromId: string, toId: string) {
    loading.value = true
    try {
      const data = await getPath(fromId, toId)
      nodes.value = data.nodes
      edges.value = data.edges
      return data
    } finally {
      loading.value = false
    }
  }

  async function fetchJobTree(jobId: number, depth = 5) {
    loading.value = true
    try {
      const data = await getJobTree(jobId, depth)
      nodes.value = data.nodes
      edges.value = data.edges
      return data
    } finally {
      loading.value = false
    }
  }

  return {
    nodes, edges, nodeCount, edgeCount, loading, loaded, error,
    currentLimit, hasMore, enrichingNodeId, enrichedNodeIds,
    fetchPanorama, loadMore, enrichNode,
    fetchNodeDetail, expand, search, findPath, fetchJobTree,
  }
})
