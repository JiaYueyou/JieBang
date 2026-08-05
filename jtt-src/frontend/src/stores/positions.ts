import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { JobPosition, Neo4jGraphNode, Neo4jGraphEdge } from '@/types'
import { positionsApi } from '@/api/positions'
import { positionFromApi } from '@/utils/transform'

export const usePositionsStore = defineStore('positions', () => {
  const positions = ref<JobPosition[]>([])
  const currentPosition = ref<JobPosition | null>(null)
  const graphNodes = ref<Neo4jGraphNode[]>([])
  const graphEdges = ref<Neo4jGraphEdge[]>([])
  const loading = ref(false)
  const total = ref(0)

  const fetchPositions = async (params?: Record<string, any>) => {
    loading.value = true
    try {
      const res: any = await positionsApi.getList(params || {})
      positions.value = (res.data.list || []).map(positionFromApi)
      total.value = res.data.total
    } finally {
      loading.value = false
    }
  }

  const fetchDetail = async (id: string) => {
    loading.value = true
    try {
      const res: any = await positionsApi.getDetail(id)
      currentPosition.value = positionFromApi(res.data)
    } finally {
      loading.value = false
    }
  }

  const fetchGraph = async (params?: Record<string, any>) => {
    const res: any = await positionsApi.getKnowledgeGraph(params)
    graphNodes.value = res.data.nodes
    graphEdges.value = res.data.edges
  }

  return { positions, currentPosition, graphNodes, graphEdges, loading, total, fetchPositions, fetchDetail, fetchGraph }
})
