import { describe, expect, it } from "vitest";
import Graph from "graphology";
import { findBestMatchingNodeId } from "./graphSearch";

function graphWithSearchCandidates() {
  const graph = new Graph();
  graph.addNode("description-match", { name: "检索增强", description: "使用 RAG 架构" });
  graph.addNode("partial-name", { name: "RAG 评估", description: "" });
  graph.addNode("exact-name", { name: "RAG", description: "标准技能" });
  return graph;
}

describe("findBestMatchingNodeId", () => {
  it("prefers an exact node name over partial and metadata matches", () => {
    expect(findBestMatchingNodeId(graphWithSearchCandidates(), " rag ")).toBe("exact-name");
  });

  it("falls back to a partial node name", () => {
    expect(findBestMatchingNodeId(graphWithSearchCandidates(), "评估")).toBe("partial-name");
  });

  it("returns null for blank or unmatched searches", () => {
    const graph = graphWithSearchCandidates();
    expect(findBestMatchingNodeId(graph, "  ")).toBeNull();
    expect(findBestMatchingNodeId(graph, "Spring Boot")).toBeNull();
  });
});
