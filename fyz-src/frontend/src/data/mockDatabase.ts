import { createMockSeed } from "./mockSeed";
import type { FavoriteRecord, FavoriteTargetType, MockDatabase } from "@/domain/types";

export const MOCK_DB_KEY = "jiebang:mock-db:v1";
const LEGACY_FAVORITES_KEY = "jiebang:favorites";

function cloneSeed(): MockDatabase {
  return structuredClone(createMockSeed());
}

function migrateLegacyFavorites(db: MockDatabase): void {
  const raw = localStorage.getItem(LEGACY_FAVORITES_KEY);
  if (!raw) return;
  try {
    const legacy = JSON.parse(raw) as Array<{ type: FavoriteTargetType | "talent"; targetId: string; title: string; createdAt: string }>;
    for (const item of legacy) {
      const targetType: FavoriteTargetType = item.type === "talent" ? "resume" : item.type;
      const targetId = targetType === "job"
        ? db.jobs.find((job) => job.title === item.title)?.id
        : Number(item.targetId);
      if (!targetId || db.favorites.some((favorite) => favorite.target_type === targetType && favorite.target_id === targetId)) continue;
      const job = targetType === "job" ? db.jobs.find((value) => value.id === targetId) : undefined;
      const talent = targetType === "resume" ? db.talents.find((value) => value.resume_id === targetId) : undefined;
      const entity = job ?? talent;
      if (!entity) continue;
      db.favorites.unshift({
        id: Math.max(0, ...db.favorites.map((value) => value.id)) + 1,
        target_type: targetType,
        target_id: targetId,
        title: "name" in entity ? entity.name : entity.title,
        subtitle: "position" in entity ? entity.position : `${entity.level}岗位`,
        company: entity.company || entity.department || "",
        location: entity.location || "",
        salary: "resume_id" in entity ? entity.salary || "" : entity.salary_range,
        experience: entity.experience || "",
        education: entity.education || "",
        skills: "matched" in entity ? entity.matched : entity.skills || [],
        match: "resume_id" in entity ? entity.score : entity.match || 0,
        savedAt: new Date(item.createdAt).toLocaleDateString("zh-CN"),
        savedOrder: Date.now(),
        note: "",
        urgent: entity.urgent,
      } satisfies FavoriteRecord);
    }
  } catch {
    // Invalid legacy data is discarded.
  } finally {
    localStorage.removeItem(LEGACY_FAVORITES_KEY);
  }
}

export function loadMockDatabase(): MockDatabase {
  const raw = localStorage.getItem(MOCK_DB_KEY);
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as MockDatabase;
      if (parsed.version === 1) {
        migrateLegacyFavorites(parsed);
        saveMockDatabase(parsed);
        return parsed;
      }
    } catch {
      // Reset invalid persisted data below.
    }
  }
  const db = cloneSeed();
  migrateLegacyFavorites(db);
  saveMockDatabase(db);
  return db;
}

export function saveMockDatabase(db: MockDatabase): void {
  localStorage.setItem(MOCK_DB_KEY, JSON.stringify(db));
}

export function resetMockDatabase(): MockDatabase {
  localStorage.removeItem(MOCK_DB_KEY);
  const db = cloneSeed();
  saveMockDatabase(db);
  return db;
}
