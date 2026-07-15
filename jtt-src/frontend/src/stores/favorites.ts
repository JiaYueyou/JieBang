import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
<<<<<<< HEAD
<<<<<<< HEAD
import { favoritesApi, type FavoriteItem, type FavoriteCreate } from '@/api/favorites'

export const useFavoritesStore = defineStore('favorites', () => {
  const allFavorites = ref<FavoriteItem[]>([])
  const loading = ref(false)

  // 按类型分组
  const positionFavs = computed(() => allFavorites.value.filter(f => f.item_type === 'position'))
  const resourceFavs = computed(() => allFavorites.value.filter(f => f.item_type === 'learning_resource'))
  const errorFavs = computed(() => allFavorites.value.filter(f => f.item_type === 'quiz_error'))
  const knowledgeFavs = computed(() => allFavorites.value.filter(f => f.item_type === 'knowledge_point'))

  const positionCount = computed(() => positionFavs.value.length)
  const resourceCount = computed(() => resourceFavs.value.length)
  const errorCount = computed(() => errorFavs.value.length)
  const knowledgeCount = computed(() => knowledgeFavs.value.length)
  const totalCount = computed(() => allFavorites.value.length)

  const fetchAll = async () => {
    loading.value = true
    try {
      const res: any = await favoritesApi.getList()
      allFavorites.value = res.data || []
    } finally {
      loading.value = false
    }
  }

  const fetchByType = async (type: string) => {
    loading.value = true
    try {
      const res: any = await favoritesApi.getList(type)
      const others = allFavorites.value.filter(f => f.item_type !== type)
      allFavorites.value = [...others, ...(res.data || [])]
    } finally {
      loading.value = false
    }
  }

  const add = async (data: FavoriteCreate) => {
    const res: any = await favoritesApi.add(data)
    const fav = res.data as FavoriteItem
    const idx = allFavorites.value.findIndex(f => f.id === fav.id)
    if (idx > -1) allFavorites.value[idx] = fav
    else allFavorites.value.unshift(fav)
    return fav
  }

  const remove = async (favId: number) => {
    await favoritesApi.remove(favId)
    allFavorites.value = allFavorites.value.filter(f => f.id !== favId)
  }

  const toggle = async (data: FavoriteCreate): Promise<boolean> => {
    const existing = allFavorites.value.find(
      f => f.item_type === data.item_type && f.item_id === data.item_id
    )
    if (existing) {
      await remove(existing.id)
      return false
    } else {
      await add(data)
      return true
    }
  }

  const isFavorited = (itemType: string, itemId: string): boolean => {
    return allFavorites.value.some(f => f.item_type === itemType && f.item_id === itemId)
  }

  return {
    allFavorites, loading,
    positionFavs, resourceFavs, errorFavs, knowledgeFavs,
    positionCount, resourceCount, errorCount, knowledgeCount, totalCount,
    fetchAll, fetchByType, add, remove, toggle, isFavorited,
=======
import { mockPositions } from '@/mock/data/positions'
import { mockLearningPaths } from '@/mock/data/learning'
import { mockNotes } from '@/mock/data/notes'
import type { FavoriteType, Note } from '@/types'

=======
import { mockPositions } from '@/mock/data/positions'
import { mockLearningPaths } from '@/mock/data/learning'
import { mockNotes } from '@/mock/data/notes'
import type { FavoriteType, Note } from '@/types'

>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
interface FavoriteRecord {
  positions: string[]
  learningPaths: string[]
  notes: string[]
}

function loadFavorites(): FavoriteRecord {
  try {
    const raw = localStorage.getItem('favorites')
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return { positions: [], learningPaths: [], notes: [] }
}

function persist(record: FavoriteRecord) {
  localStorage.setItem('favorites', JSON.stringify(record))
}

export const useFavoritesStore = defineStore('favorites', () => {
  const record = ref<FavoriteRecord>(loadFavorites())

  const isFavorited = (type: FavoriteType, id: string) =>
    record.value[type === 'position' ? 'positions' : type === 'learning_path' ? 'learningPaths' : 'notes'].includes(id)

  const toggleFavorite = (type: FavoriteType, id: string) => {
    const key = type === 'position' ? 'positions' : type === 'learning_path' ? 'learningPaths' : 'notes'
    const list = record.value[key]
    const idx = list.indexOf(id)
    if (idx >= 0) {
      list.splice(idx, 1)
    } else {
      list.push(id)
    }
    persist({ ...record.value })
  }

  // 收藏的岗位
  const positionFavorites = computed(() =>
    mockPositions.filter((p) => record.value.positions.includes(p.id)),
  )
  const positionCount = computed(() => record.value.positions.length)

  // 收藏的学习路径
  const learningPathFavorites = computed(() =>
    mockLearningPaths.filter((p) => record.value.learningPaths.includes(p.id)),
  )
  const learningPathCount = computed(() => record.value.learningPaths.length)

  // 收藏的笔记
  const noteFavorites = computed(() =>
    mockNotes.filter((n) => record.value.notes.includes(n.id)),
  )
  const noteCount = computed(() => record.value.notes.length)

  const totalCount = computed(
    () => record.value.positions.length + record.value.learningPaths.length + record.value.notes.length,
  )

  return {
    record,
    isFavorited,
    toggleFavorite,
    positionFavorites,
    positionCount,
    learningPathFavorites,
    learningPathCount,
    noteFavorites,
    noteCount,
    totalCount,
<<<<<<< HEAD
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
=======
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
  }
})
