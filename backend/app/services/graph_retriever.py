import logging
from typing import List, Dict, Any, Set, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document_chunk import DocumentChunk
from app.services.graph_store import graph_store
from app.services.entity_extractor import entity_extractor

logger = logging.getLogger("app.services.graph_retriever")

class GraphRetriever:
    def retrieve_graph_context(
        self,
        db: Session,
        query: str,
        user_doc_ids: List[int],
        depth: int = 2
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extracts entities from query, performs neighborhood expansion,
        retrieves associated chunks, and returns them along with subgraph metadata.
        """
        # 1. Extract entities from the query
        query_entities = entity_extractor.extract_entities(query)
        logger.info(f"Query entities extracted: {[e['name'] for e in query_entities]}")
        
        # 2. Match entities to nodes in graph
        matched_node_ids = self._match_entities_to_nodes(query_entities)
        logger.info(f"Matched graph node IDs: {list(matched_node_ids)}")
        
        if not matched_node_ids:
            return [], {"entities": [], "relationships": []}

        # 3. Perform Neighborhood Expansion / Traversal
        traversed_nodes, traversed_edges = self._traverse_graph(matched_node_ids, depth)
        logger.info(f"Traversed {len(traversed_nodes)} nodes and {len(traversed_edges)} edges.")

        # 4. Filter by user document permissions and fetch actual chunks from DB
        chunks = self._fetch_associated_chunks(db, traversed_nodes, traversed_edges, user_doc_ids)
        
        subgraph = {
            "entities": [graph_store.nodes[nid] for nid in traversed_nodes if nid in graph_store.nodes],
            "relationships": traversed_edges
        }
        
        return chunks, subgraph

    def _match_entities_to_nodes(self, query_entities: List[Dict[str, Any]]) -> Set[str]:
        matched = set()
        graph_nodes = graph_store.nodes
        
        for q_ent in query_entities:
            q_name = q_ent["name"].lower().strip()
            
            # 1. Exact or substring match
            for nid, node in graph_nodes.items():
                node_name_lower = node["name"].lower()
                # Check exact
                if q_name == nid or q_name == node_name_lower:
                    matched.add(nid)
                    continue
                # Check aliases
                if any(q_name == a.lower().strip() for a in node.get("aliases", [])):
                    matched.add(nid)
                    continue
                # Check containment
                if q_name in node_name_lower or node_name_lower in q_name:
                    matched.add(nid)
                    
        return matched

    def _traverse_graph(self, start_nodes: Set[str], max_depth: int) -> Tuple[Set[str], List[Dict[str, Any]]]:
        visited_nodes = set(start_nodes)
        visited_edges = []
        queue = list(start_nodes)
        
        # Keep track of depth level of each queued node
        node_depth = {nid: 0 for nid in start_nodes}
        
        while queue:
            curr = queue.pop(0)
            curr_depth = node_depth.get(curr, 0)
            
            if curr_depth >= max_depth:
                continue
                
            neighbors = graph_store.get_neighbors(curr)
            for n in neighbors:
                neighbor_id = n["node_id"]
                
                # Check edge constraints
                edge_confidence = n.get("confidence", 1.0)
                if edge_confidence < settings.GRAPHRAG_CONFIDENCE_THRESHOLD:
                    continue

                if neighbor_id not in visited_nodes:
                    visited_nodes.add(neighbor_id)
                    node_depth[neighbor_id] = curr_depth + 1
                    queue.append(neighbor_id)
                    
                # Track unique edges
                # To avoid duplicating source->target vs target->source directed edges,
                # let's locate the original edge record in graph_store.edges
                for original_edge in graph_store.edges:
                    s, t = original_edge["source"], original_edge["target"]
                    if (s == curr and t == neighbor_id) or (s == neighbor_id and t == curr):
                        if original_edge not in visited_edges:
                            visited_edges.append(original_edge)

        return visited_nodes, visited_edges

    def _fetch_associated_chunks(
        self,
        db: Session,
        node_ids: Set[str],
        edges: List[Dict[str, Any]],
        user_doc_ids: List[int]
    ) -> List[Dict[str, Any]]:
        # Gather all chunk IDs referenced by the nodes and edges
        chunk_ids: Set[int] = set()
        
        # 1. From traversed nodes
        for nid in node_ids:
            node = graph_store.get_node(nid)
            if node:
                cids = node.get("properties", {}).get("chunk_ids", [])
                for cid in cids:
                    try:
                        chunk_ids.add(int(cid))
                    except (ValueError, TypeError):
                        pass
                        
        # 2. From traversed edges
        for edge in edges:
            cid = edge.get("properties", {}).get("chunk_id")
            if cid:
                try:
                    chunk_ids.add(int(cid))
                except (ValueError, TypeError):
                    pass
                    
        if not chunk_ids:
            return []
            
        # Retrieve chunks from DB filtered by authorized document IDs
        db_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.id.in_(list(chunk_ids)),
            DocumentChunk.document_id.in_(user_doc_ids)
        ).all()
        
        # Format matching the standard Hybrid search hit dictionary structure
        formatted_chunks = []
        for chunk in db_chunks:
            # We assign a default structural graph score (e.g. 0.8) which will be ranked
            formatted_chunks.append({
                "chunk_id": str(chunk.id),
                "document_id": chunk.document_id,
                "page_number": chunk.page_number,
                "chunk_text": chunk.chunk_text,
                "score": 0.80, # Base relevance weight for matching graph retrieval
                "is_graph_retrieved": True
            })
            
        return formatted_chunks

graph_retriever = GraphRetriever()
