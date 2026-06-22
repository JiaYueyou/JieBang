import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { mockPositions } from '@/mock/data/positions'

function loadFavorites(): Set<string> {
  try {
    const raw = localStorage.getItem('favoritePositionIds')
    if (raw) return new Set(JSON.parse(raw))
  } catch { /* ignore */ }
  return new Set()
}

function persist(ids: Set<string>) {
  localStorage.setItem('favoritePositionIds', JSON.stringify([...ids]))
}

export const useFavoritesStore = defineStore('favorites', () => {
  const favoriteIds = ref<Set<string>>(loadFavorites())

  const favorites = computed(() => mockPositions.filter((p) => favoriteIds.value.has(p.id)))

  const favoriteCount = computed(() => favoriteIds.value.size)

  const isFavorited = (positionId: string) => favoriteIds.value.has(positionId)

  const toggleFavorite = (positionId: string) => {
    const next = new Set(favoriteIds.value)
    if (next.has(positionId)) {
      next.delete(positionId)
    } else {
      next.add(positionId)
    }
    favoriteIds.value = next
    persist(next)
  }

  return { favoriteIds, favorites, favoriteCount, isFavorited, toggleFavorite }
})
