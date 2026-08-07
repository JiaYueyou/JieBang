import Graph from "graphology";

/**
 * 计算从 L1（Job）节点到目标选中节点的无向路径节点集合。
 *
 * 语义：选中某节点后，只保留该节点所在"L1→L5 路径"上的节点正常显示，
 * 其余节点弱化。路径在本地 masterGraph 上计算（L1~L5 数据已合并其中，
 * 免额外请求）。
 *
 * - 从所有 L1 Job 节点出发 BFS 到 targetId，取最近路径；
 * - 返回路径上全部节点 id（含两端，保证 L1~L5 各级节点正常显示）；
 * - 无 L1 可达路径时回退为仅目标节点自身（孤立节点仍可被选中高亮）；
 * - 无目标/图中无目标节点时返回空数组（无选中态）。
 */
export function computePathNodeIds(graph: Graph, targetId: string | null): string[] {
  if (!targetId || !graph.hasNode(targetId)) return [];

  // 找所有 L1 Job 节点
  const l1Nodes: string[] = [];
  graph.forEachNode((nodeId: string, attrs: any) => {
    if ((attrs.level === "L1" || attrs.type === "Job") && nodeId !== targetId) {
      l1Nodes.push(nodeId);
    }
  });

  // BFS（无向）：从所有 L1 起点同步扩展，先到达 targetId 的即最近路径
  const visited = new Set<string>(l1Nodes);
  const prev = new Map<string, string>();
  const queue = [...l1Nodes];
  let found = false;
  while (queue.length > 0 && !found) {
    const current = queue.shift()!;
    graph.forEachNeighbor(current, (neighborId: string) => {
      if (found || visited.has(neighborId)) return;
      visited.add(neighborId);
      prev.set(neighborId, current);
      if (neighborId === targetId) {
        found = true;
        return;
      }
      queue.push(neighborId);
    });
  }

  if (!found) {
    // 孤立节点（无 L1 可达路径）：仅目标节点自身
    return [targetId];
  }

  // 回溯路径
  const path: string[] = [targetId];
  let cursor = targetId;
  while (prev.has(cursor)) {
    cursor = prev.get(cursor)!;
    path.push(cursor);
  }
  return path;
}

function levelNumber(level: string | undefined): number {
  const match = /^L(\d+)$/.exec(level || "");
  return match ? parseInt(match[1], 10) : 0;
}

/**
 * 计算选中节点后的完整高亮集合 = 向上路径 + 向下展开后代。
 *
 * 语义：选中节点后，路径上 L1~L5 保持正常显示，同时该节点已展开的
 * 下级节点（如点击 L3 后展开的 L4/L5）也应保持正常颜色，其余节点弱化。
 *
 * - 向上：复用 computePathNodeIds（L1→选中节点路径）；
 * - 向下：从选中节点出发，扩展层级严格递增的邻居（子级方向），
 *   BFS 深度 2（L3→L4→L5、L2→L3、L4→L5 均覆盖）；
 * - 无目标/图中无目标节点时返回空数组。
 */
export function computeHighlightNodeIds(graph: Graph, targetId: string | null): string[] {
  if (!targetId || !graph.hasNode(targetId)) return [];
  const set = new Set<string>(computePathNodeIds(graph, targetId));
  const targetLevel = levelNumber(graph.getNodeAttributes(targetId)?.level);
  if (targetLevel <= 0) return [...set];

  const queue: Array<{ id: string; depth: number }> = [{ id: targetId, depth: 0 }];
  while (queue.length > 0) {
    const { id, depth } = queue.shift()!;
    if (depth >= 2) continue;
    graph.forEachNeighbor(id, (neighborId: string) => {
      const neighborLevel = levelNumber(graph.getNodeAttributes(neighborId)?.level);
      if (neighborLevel > targetLevel && !set.has(neighborId)) {
        set.add(neighborId);
        queue.push({ id: neighborId, depth: depth + 1 });
      }
    });
  }
  return [...set];
}
