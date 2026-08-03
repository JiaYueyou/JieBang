import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getPanorama, getNodeDetail, expandNode, searchNodes, getPath, getJobTree } from '@/api/graph'
import type { Neo4jGraphNode, Neo4jGraphEdge } from '@/types'

export const useGraphStore = defineStore('graph', () => {
  const nodes = ref<Neo4jGraphNode[]>([])
  const edges = ref<Neo4jGraphEdge[]>([])
  const nodeCount = ref(0)
  const edgeCount = ref(0)
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref('')

  async function fetchPanorama(params?: {
    stack?: string; level?: string; node_type?: string; keyword?: string; limit?: number
  }) {
    loading.value = true
    error.value = ''
    try {
      const data = await getPanorama(params)
      nodes.value = data.nodes
      edges.value = data.edges
      nodeCount.value = data.node_count
      edgeCount.value = data.edge_count
      loaded.value = true
      return data
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载图谱失败'
      throw e
    } finally {
      loading.value = false
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
    fetchPanorama, fetchNodeDetail, expand, search, findPath, fetchJobTree,
  }
})
