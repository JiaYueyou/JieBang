import { computed, reactive } from "vue";
import { dataProvider } from "@/data";
import type { GraphAsyncTask } from "@/domain/types";

export type GraphTaskKind = "sync" | "enrichment" | "publication";

const STORAGE_KEY = "fyz:graph-tasks:v1";
const tasks = reactive<Partial<Record<GraphTaskKind, GraphAsyncTask>>>({});
const polling = new Set<GraphTaskKind>();

function persist() {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

async function poll(kind: GraphTaskKind) {
  if (polling.has(kind)) return;
  polling.add(kind);
  try {
    while (tasks[kind] && ["queued", "running"].includes(tasks[kind]!.status)) {
      await new Promise(resolve => window.setTimeout(resolve, 1200));
      tasks[kind] = await dataProvider.graph.getTask(tasks[kind]!.task_id);
      persist();
    }
  } catch (error) {
    const current = tasks[kind];
    if (current) {
      tasks[kind] = {
        ...current,
        status: "failed",
        error_message: error instanceof Error ? error.message : "任务状态查询失败",
      };
      persist();
    }
  } finally {
    polling.delete(kind);
  }
}

async function start(kind: GraphTaskKind, starter: () => Promise<GraphAsyncTask>) {
  const active = tasks[kind];
  if (active && ["queued", "running"].includes(active.status)) return active;
  tasks[kind] = await starter();
  persist();
  void poll(kind);
  return tasks[kind]!;
}

function resume() {
  try {
    Object.assign(tasks, JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}"));
  } catch {
    sessionStorage.removeItem(STORAGE_KEY);
  }
  (Object.keys(tasks) as GraphTaskKind[]).forEach(kind => {
    if (["queued", "running"].includes(tasks[kind]?.status || "")) void poll(kind);
  });
}

function clear(kind: GraphTaskKind) {
  delete tasks[kind];
  persist();
}

export function useGraphTasks() {
  return {
    tasks,
    anyRunning: computed(() => Object.values(tasks).some(task => task && ["queued", "running"].includes(task.status))),
    startSync: () => start("sync", dataProvider.graph.startSync),
    startEnrichment: () => start("enrichment", dataProvider.graph.startEnrichment),
    startPublication: (ids: number[]) => start("publication", () => dataProvider.graph.startPublication(ids)),
    resume,
    clear,
  };
}
