import { describe, expect, it } from "vitest";
import Graph from "graphology";
import { computeHighlightNodeIds, computePathNodeIds } from "./graphPath";

function addNode(graph: Graph, id: string, level: string, type: string) {
  graph.addNode(id, { id, name: id, type, level });
}

function buildLineGraph(): Graph {
  // Job(role-a) -> SkillArea(backend) -> TechStack(java) -> TechPoint(mybatis) -> KnowledgePoint(cache)
  const graph = new Graph();
  addNode(graph, "job:a", "L1", "Job");
  addNode(graph, "skill:backend", "L2", "SkillArea");
  addNode(graph, "stack:java", "L3", "TechStack");
  addNode(graph, "point:mybatis", "L4", "TechPoint");
  addNode(graph, "knowledge:cache", "L5", "KnowledgePoint");
  graph.addEdge("job:a", "skill:backend", { relation: "REQUIRES_AREA" });
  graph.addEdge("skill:backend", "stack:java", { relation: "CONTAINS" });
  graph.addEdge("stack:java", "point:mybatis", { relation: "REFINES_TO" });
  graph.addEdge("point:mybatis", "knowledge:cache", { relation: "HAS_KNOWLEDGE" });
  return graph;
}

describe("computePathNodeIds", () => {
  it("返回 L1 到 L5 完整路径节点集合（含两端）", () => {
    const graph = buildLineGraph();
    const path = computePathNodeIds(graph, "knowledge:cache");
    expect(path).toContain("knowledge:cache");
    expect(path).toContain("point:mybatis");
    expect(path).toContain("stack:java");
    expect(path).toContain("skill:backend");
    expect(path).toContain("job:a");
    expect(path.length).toBe(5);
  });

  it("多 L1 起点时选择最近的路径", () => {
    const graph = buildLineGraph();
    // 第二个 Job 直接挂在 stack:java 上（路径更短）
    addNode(graph, "job:b", "L1", "Job");
    graph.addEdge("job:b", "stack:java", { relation: "REQUIRES_AREA" });
    const path = computePathNodeIds(graph, "point:mybatis");
    // 最近路径 job:b -> stack:java -> point:mybatis
    expect(path).toContain("job:b");
    expect(path).not.toContain("job:a");
    expect(path).not.toContain("skill:backend");
    expect(path.length).toBe(3);
  });

  it("孤立节点（无 L1 可达）回退为仅目标节点自身", () => {
    const graph = buildLineGraph();
    addNode(graph, "point:orphan", "L4", "TechPoint");
    const path = computePathNodeIds(graph, "point:orphan");
    expect(path).toEqual(["point:orphan"]);
  });

  it("无选中（null）返回空数组", () => {
    const graph = buildLineGraph();
    expect(computePathNodeIds(graph, null)).toEqual([]);
  });

  it("目标节点不在图中返回空数组", () => {
    const graph = buildLineGraph();
    expect(computePathNodeIds(graph, "missing:node")).toEqual([]);
  });

  it("目标为 L1 自身时路径仅含自身", () => {
    const graph = buildLineGraph();
    const path = computePathNodeIds(graph, "job:a");
    expect(path).toEqual(["job:a"]);
  });
});

describe("computeHighlightNodeIds", () => {
  function buildBranchGraph(): Graph {
    // job:a -> skill:backend -> stack:java -> point:mybatis -> knowledge:cache
    //                              stack:java -> point:springboot -> knowledge:autoconfig
    // job:a -> skill:ai -> stack:python -> point:pandas
    const graph = new Graph();
    addNode(graph, "job:a", "L1", "Job");
    addNode(graph, "skill:backend", "L2", "SkillArea");
    addNode(graph, "skill:ai", "L2", "SkillArea");
    addNode(graph, "stack:java", "L3", "TechStack");
    addNode(graph, "stack:python", "L3", "TechStack");
    addNode(graph, "point:mybatis", "L4", "TechPoint");
    addNode(graph, "point:springboot", "L4", "TechPoint");
    addNode(graph, "point:pandas", "L4", "TechPoint");
    addNode(graph, "knowledge:cache", "L5", "KnowledgePoint");
    addNode(graph, "knowledge:autoconfig", "L5", "KnowledgePoint");
    const edges: Array<[string, string]> = [
      ["job:a", "skill:backend"], ["job:a", "skill:ai"],
      ["skill:backend", "stack:java"], ["skill:ai", "stack:python"],
      ["stack:java", "point:mybatis"], ["stack:java", "point:springboot"],
      ["stack:python", "point:pandas"],
      ["point:mybatis", "knowledge:cache"],
      ["point:springboot", "knowledge:autoconfig"],
    ];
    for (const [s, t] of edges) graph.addEdge(s, t, { relation: "CONTAINS" });
    return graph;
  }

  it("选中 L3 时展开的 L4/L5 后代保持正常（在集合内）", () => {
    const graph = buildBranchGraph();
    const ids = computeHighlightNodeIds(graph, "stack:java");
    // 向上路径
    expect(ids).toContain("job:a");
    expect(ids).toContain("skill:backend");
    expect(ids).toContain("stack:java");
    // 向下展开后代：L4 + L5（BFS 深度 2）
    expect(ids).toContain("point:mybatis");
    expect(ids).toContain("point:springboot");
    expect(ids).toContain("knowledge:cache");
    expect(ids).toContain("knowledge:autoconfig");
    // 无关分支（AI 方向）不包含
    expect(ids).not.toContain("skill:ai");
    expect(ids).not.toContain("stack:python");
    expect(ids).not.toContain("point:pandas");
  });

  it("选中 L2 时下级 L3 保持正常", () => {
    const graph = buildBranchGraph();
    const ids = computeHighlightNodeIds(graph, "skill:backend");
    expect(ids).toContain("stack:java");
    expect(ids).toContain("point:mybatis"); // L3 的下级 L4 也在（深度 2 内）
    expect(ids).not.toContain("stack:python");
  });

  it("选中 L4 时其 L5 下级保持正常", () => {
    const graph = buildBranchGraph();
    const ids = computeHighlightNodeIds(graph, "point:springboot");
    expect(ids).toContain("knowledge:autoconfig");
    expect(ids).toContain("stack:java"); // 向上路径
    expect(ids).not.toContain("point:pandas"); // 无关分支
  });

  it("孤立节点（无 L1 可达）回退为仅目标节点自身", () => {
    const graph = buildBranchGraph();
    addNode(graph, "point:orphan", "L4", "TechPoint");
    const ids = computeHighlightNodeIds(graph, "point:orphan");
    expect(ids).toEqual(["point:orphan"]);
  });

  it("无选中（null）返回空数组", () => {
    const graph = buildBranchGraph();
    expect(computeHighlightNodeIds(graph, null)).toEqual([]);
  });
});
