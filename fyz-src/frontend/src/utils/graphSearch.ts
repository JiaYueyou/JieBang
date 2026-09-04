import type Graph from "graphology";

function normalize(value: unknown): string {
  return typeof value === "string" ? value.trim().toLocaleLowerCase() : "";
}

/**
 * Pick the node that best represents a graph search. Exact node-name matches
 * take precedence over prefixes, partial names, and descriptive metadata.
 */
export function findBestMatchingNodeId(graph: Graph | null, keyword: string): string | null {
  const query = normalize(keyword);
  if (!graph || !query) return null;

  let bestId: string | null = null;
  let bestScore = 0;

  graph.forEachNode((id, attrs) => {
    const name = normalize(attrs.name || attrs.label);
    const metadata = [attrs.description, attrs.parent_skill, attrs.parent_tech_point]
      .map(normalize)
      .filter(Boolean);

    let score = 0;
    if (name === query) score = 400;
    else if (name.startsWith(query)) score = 300;
    else if (name.includes(query)) score = 200;
    else if (metadata.some(value => value === query)) score = 150;
    else if (metadata.some(value => value.includes(query))) score = 100;

    if (score > 0 && (score > bestScore || (score === bestScore && (bestId === null || id.localeCompare(bestId) < 0)))) {
      bestId = id;
      bestScore = score;
    }
  });

  return bestId;
}
