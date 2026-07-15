import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { mockPositions } from '@/mock/data/positions'
import { mockLearningPaths } from '@/mock/data/learning'
import { mockNotes } from '@/mock/data/notes'
import type { FavoriteType, Note } from '@/types'

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
  }
})
