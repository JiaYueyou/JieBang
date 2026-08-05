import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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
  }
})
