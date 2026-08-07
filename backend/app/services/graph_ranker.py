import logging
from typing import List, Dict, Any, Set

from app.core.config import settings

logger = logging.getLogger("app.services.graph_ranker")

class GraphRanker:
    def calculate_pagerank(self, node_ids: Set[str], edges: List[Dict[str, Any]], iterations: int = 10, d: float = 0.85) -> Dict[str, float]:
        """
        Runs a standard PageRank iteration algorithm over the subgraph nodes and edges.
        """
        N = len(node_ids)
        if N == 0:
            return {}
            
        # Initialize PageRank uniform weights
        pagerank = {nid: 1.0 / N for nid in node_ids}
        
        # Build adjacency structures
        in_edges = {nid: [] for nid in node_ids}
        out_degree = {nid: 0 for nid in node_ids}
        
        for edge in edges:
            s, t = edge["source"], edge["target"]
            # Since edges are undirected in our logic, treat connections bidirectionally
            if s in node_ids and t in node_ids:
                in_edges[t].append((s, edge.get("confidence", 1.0)))
                in_edges[s].append((t, edge.get("confidence", 1.0)))
                out_degree[s] += 1
                out_degree[t] += 1

        for _ in range(iterations):
            new_pagerank = {}
            for u in node_ids:
                sum_pr = 0.0
                for v, weight in in_edges[u]:
                    # Distribute PageRank divided by connections, scaled by relation confidence
                    if out_degree[v] > 0:
                        sum_pr += (pagerank[v] / out_degree[v]) * weight
                new_pagerank[u] = (1.0 - d) / N + d * sum_pr
            pagerank = new_pagerank

        return pagerank

    def rank_hybrid_chunks(
        self,
        vector_hits: List[Dict[str, Any]],
        graph_hits: List[Dict[str, Any]],
        pagerank_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicates, scores, and ranks aggregated chunks from vector search and graph retrieval.
        """
        hybrid_weight = settings.GRAPHRAG_HYBRID_WEIGHT
        ranked_chunks = []
        seen_ids = set()

        # Map chunk IDs to their vector metadata
        vector_map = {str(hit["chunk_id"]): hit for hit in vector_hits}
        # Map chunk IDs to their graph metadata
        graph_map = {str(hit["chunk_id"]): hit for hit in graph_hits}

        all_chunk_ids = set(vector_map.keys()) | set(graph_map.keys())

        for cid in all_chunk_ids:
            score = 0.0
            vector_hit = vector_map.get(cid)
            graph_hit = graph_map.get(cid)
            
            # Find the best PageRank centrality score associated with this chunk's nodes
            chunk_centrality = 0.0
            for nid, pr in pagerank_scores.items():
                from app.services.graph_store import graph_store
                node = graph_store.get_node(nid)
                if node:
                    cids = node.get("properties", {}).get("chunk_ids", [])
                    if cid in [str(x) for x in cids]:
                        chunk_centrality = max(chunk_centrality, pr)

            # Combined score mapping: vector scores are preserved as primary, graph hits add a small boost
            if vector_hit and graph_hit:
                v_score = vector_hit["score"]
                g_score = graph_hit.get("score", 0.8) + chunk_centrality
                score = v_score + hybrid_weight * (g_score * 0.2)
            elif vector_hit:
                score = vector_hit["score"]
            else:
                # Graph retrieved only
                g_score = graph_hit.get("score", 0.8) + chunk_centrality
                score = hybrid_weight * (g_score * 0.5)

            # Retain the base hit metadata (preferring vector metadata for ranking/text consistency)
            base_hit = vector_hit or graph_hit
            # Copy to prevent mutate
            merged_hit = dict(base_hit)
            merged_hit["score"] = round(score, 4)
            merged_hit["is_graph_retrieved"] = (graph_hit is not None)
            
            ranked_chunks.append(merged_hit)

        # Sort descending
        ranked_chunks.sort(key=lambda x: x["score"], reverse=True)
        return ranked_chunks

graph_ranker = GraphRanker()
