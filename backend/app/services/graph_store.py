import os
import json
import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger("app.services.graph_store")

class GraphStore:
    def __init__(self, filepath: Optional[str] = None):
        if filepath:
            self.filepath = filepath
        else:
            path = settings.GRAPHRAG_STORAGE_PATH
            if not os.path.isabs(path):
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                path = os.path.join(base_dir, path)
            self.filepath = path
            
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    self.nodes = data.get("nodes", {})
                    self.edges = data.get("edges", [])
                logger.info(f"Loaded graph store from {self.filepath} with {len(self.nodes)} nodes and {len(self.edges)} edges.")
            except Exception as e:
                logger.error(f"Failed to load graph store from {self.filepath}: {e}")
                self.nodes = {}
                self.edges = []
        else:
            self.nodes = {}
            self.edges = []

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w") as f:
                json.dump({"nodes": self.nodes, "edges": self.edges}, f, indent=2)
            logger.info(f"Saved graph store to {self.filepath}.")
        except Exception as e:
            logger.error(f"Failed to save graph store: {e}")

    def add_node(self, node_id: str, name: str, node_type: str, aliases: List[str] = None, properties: Dict[str, Any] = None):
        node_id = node_id.strip().lower()
        if not node_id:
            return
            
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "id": node_id,
                "name": name,
                "type": node_type,
                "aliases": aliases or [],
                "properties": properties or {}
            }
        else:
            existing = self.nodes[node_id]
            existing["aliases"] = list(set(existing.get("aliases", []) + (aliases or [])))
            if properties:
                existing.setdefault("properties", {}).update(properties)

    def add_edge(self, source: str, target: str, relationship_type: str, description: Optional[str] = None, confidence: float = 1.0, properties: Dict[str, Any] = None):
        source = source.strip().lower()
        target = target.strip().lower()
        if not source or not target:
            return
            
        # Ensure source and target exist in nodes
        if source not in self.nodes:
            self.add_node(source, source.title(), "Concept")
        if target not in self.nodes:
            self.add_node(target, target.title(), "Concept")

        # Check duplicate edges
        for edge in self.edges:
            if edge["source"] == source and edge["target"] == target and edge["type"] == relationship_type:
                edge["confidence"] = max(edge["confidence"], confidence)
                if properties:
                    edge.setdefault("properties", {}).update(properties)
                return
                
        self.edges.append({
            "source": source,
            "target": target,
            "type": relationship_type,
            "description": description or "",
            "confidence": confidence,
            "properties": properties or {}
        })

    def delete_node(self, node_id: str):
        node_id = node_id.strip().lower()
        if node_id in self.nodes:
            del self.nodes[node_id]
        self.edges = [e for e in self.edges if e["source"] != node_id and e["target"] != node_id]

    def delete_document_nodes(self, document_id: int):
        doc_id_str = str(document_id)
        self.edges = [
            edge for edge in self.edges 
            if edge.get("properties", {}).get("document_id") != doc_id_str 
            and edge.get("properties", {}).get("document_id") != document_id
        ]
        
        nodes_to_delete = []
        for nid, node in self.nodes.items():
            docs = node.setdefault("properties", {}).setdefault("document_ids", [])
            # Filter doc id
            filtered_docs = [d for d in docs if str(d) != doc_id_str and d != document_id]
            node["properties"]["document_ids"] = filtered_docs
            if not filtered_docs:
                nodes_to_delete.append(nid)
                
        for nid in nodes_to_delete:
            del self.nodes[nid]
        
        self.save()

    def merge_graphs(self, nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]):
        for nid, node in nodes.items():
            self.add_node(
                node_id=nid,
                name=node["name"],
                node_type=node["type"],
                aliases=node.get("aliases", []),
                properties=node.get("properties", {})
            )
        for edge in edges:
            self.add_edge(
                source=edge["source"],
                target=edge["target"],
                relationship_type=edge["type"],
                description=edge.get("description"),
                confidence=edge.get("confidence", 1.0),
                properties=edge.get("properties")
            )
        self.save()

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self.nodes.get(node_id.strip().lower())

    def get_neighbors(self, node_id: str) -> List[Dict[str, Any]]:
        node_id = node_id.strip().lower()
        neighbors = []
        for edge in self.edges:
            if edge["source"] == node_id:
                neighbors.append({
                    "node_id": edge["target"],
                    "relationship": edge["type"],
                    "description": edge.get("description", ""),
                    "confidence": edge.get("confidence", 1.0),
                    "direction": "out"
                })
            elif edge["target"] == node_id:
                neighbors.append({
                    "node_id": edge["source"],
                    "relationship": edge["type"],
                    "description": edge.get("description", ""),
                    "confidence": edge.get("confidence", 1.0),
                    "direction": "in"
                })
        return neighbors

    def get_statistics(self) -> Dict[str, Any]:
        num_nodes = len(self.nodes)
        num_edges = len(self.edges)
        
        # Calculate components using BFS
        visited = set()
        components = 0
        largest_comp = 0
        
        # Adjacency list representation
        adj = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            s, t = edge["source"], edge["target"]
            if s in adj and t in adj:
                adj[s].append(t)
                adj[t].append(s)
                
        for nid in self.nodes:
            if nid not in visited:
                components += 1
                comp_size = 0
                queue = [nid]
                visited.add(nid)
                while queue:
                    curr = queue.pop(0)
                    comp_size += 1
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                largest_comp = max(largest_comp, comp_size)
                
        avg_degree = (2.0 * num_edges / num_nodes) if num_nodes > 0 else 0.0
        density = (2.0 * num_edges / (num_nodes * (num_nodes - 1))) if num_nodes > 1 else 0.0
        
        entity_freq = {}
        for node in self.nodes.values():
            ntype = node["type"]
            entity_freq[ntype] = entity_freq.get(ntype, 0) + 1
            
        rel_freq = {}
        for edge in self.edges:
            etype = edge["type"]
            rel_freq[etype] = rel_freq.get(etype, 0) + 1
            
        return {
            "node_count": num_nodes,
            "edge_count": num_edges,
            "connected_components": components,
            "average_degree": round(avg_degree, 4),
            "largest_component_size": largest_comp,
            "entity_frequencies": entity_freq,
            "relationship_frequencies": rel_freq,
            "graph_density": round(density, 4),
            "graph_coverage": 1.0  # Placeholder or actual coverage
        }

    def clear(self):
        self.nodes = {}
        self.edges = []
        if os.path.exists(self.filepath):
            try:
                os.remove(self.filepath)
            except Exception as e:
                logger.error(f"Failed to delete graph store file: {e}")

graph_store = GraphStore()
