import { ref } from "vue";

export type FavoriteTargetType = "job" | "resume";

interface StoredFavorite {
  key: string;
  type: FavoriteTargetType;
  targetId: string;
  title: string;
  createdAt: string;
}

const STORAGE_KEY = "jiebang:favorites";

function readFavorites(): StoredFavorite[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

const favorites = ref<StoredFavorite[]>(readFavorites());

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites.value));
}

function favoriteKey(type: FavoriteTargetType, targetId: string | number) {
  return `${type}:${String(targetId)}`;
}

export function useFavorites() {
  function isFavorite(type: FavoriteTargetType, targetId: string | number) {
    const key = favoriteKey(type, targetId);
    return favorites.value.some((item) => item.key === key);
  }

  function toggleFavorite(type: FavoriteTargetType, targetId: string | number, title: string) {
    const key = favoriteKey(type, targetId);
    const existingIndex = favorites.value.findIndex((item) => item.key === key);

    if (existingIndex >= 0) {
      favorites.value.splice(existingIndex, 1);
      persist();
      return false;
    }

    favorites.value.unshift({
      key,
      type,
      targetId: String(targetId),
      title,
      createdAt: new Date().toISOString(),
    });
    persist();
    return true;
  }

  return { favorites, isFavorite, toggleFavorite };
}
