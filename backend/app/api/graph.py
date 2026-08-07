from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.api.users import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.graph_rag import (
    Entity,
    Relationship,
    GraphStats,
    EntitySearchResponse,
    SubgraphResponse,
    NeighborsResponse,
    GraphExportResponse
)
from app.services.graph_store import graph_store
from app.services.graph_retriever import graph_retriever
from app.services.graph_ranker import graph_ranker
from app.services.entity_extractor import entity_extractor

router = APIRouter()

def get_user_doc_ids(db: Session, user: User) -> set:
    user_docs = db.query(Document).filter(Document.user_id == user.id).all()
    return {doc.id for doc in user_docs}

def filter_user_graph(user_doc_ids: set) -> tuple:
    user_nodes = {}
    user_edges = []
    
    # Filter nodes
    for nid, node in graph_store.nodes.items():
        doc_ids = node.get("properties", {}).get("document_ids", [])
        if any(did in user_doc_ids or str(did) in [str(x) for x in user_doc_ids] for did in doc_ids):
            user_nodes[nid] = Entity(
                id=node["id"],
                name=node["name"],
                type=node["type"],
                aliases=node.get("aliases", []),
                description=node.get("description"),
                properties=node.get("properties", {})
            )
            
    # Filter edges
    for edge in graph_store.edges:
        doc_id = edge.get("properties", {}).get("document_id")
        if doc_id in user_doc_ids or str(doc_id) in [str(x) for x in user_doc_ids]:
            # Only retain edges connecting nodes that are also visible to the user
            s, t = edge["source"], edge["target"]
            if s in user_nodes and t in user_nodes:
                user_edges.append(
                    Relationship(
                        source=s,
                        target=t,
                        type=edge["type"],
                        description=edge.get("description"),
                        confidence=edge.get("confidence", 1.0),
                        properties=edge.get("properties", {})
                    )
                )
                
    return user_nodes, user_edges

@router.get("/entities", response_model=List[Entity])
def get_entities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_doc_ids = get_user_doc_ids(db, current_user)
    user_nodes, _ = filter_user_graph(user_doc_ids)
    return list(user_nodes.values())

@router.get("/entity/{entity_id}", response_model=Entity)
def get_entity_by_id(
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    nid = entity_id.strip().lower()
    node = graph_store.get_node(nid)
    if not node:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")
        
    user_doc_ids = get_user_doc_ids(db, current_user)
    doc_ids = node.get("properties", {}).get("document_ids", [])
    if not any(did in user_doc_ids or str(did) in [str(x) for x in user_doc_ids] for did in doc_ids):
        raise HTTPException(status_code=403, detail="Access denied to entity.")
        
    return Entity(
        id=node["id"],
        name=node["name"],
        type=node["type"],
        aliases=node.get("aliases", []),
        description=node.get("description"),
        properties=node.get("properties", {})
    )

@router.get("/search", response_model=List[EntitySearchResponse])
def search_graph(
    query: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_doc_ids = get_user_doc_ids(db, current_user)
    
    # Match input query to start nodes
    start_entities = entity_extractor.extract_entities(query)
    matched_ids = graph_retriever._match_entities_to_nodes(start_entities)
    
    results = []
    if not matched_ids:
        return []
        
    # Get user nodes/edges to restrict calculations
    user_nodes, user_edges = filter_user_graph(user_doc_ids)
    
    # Calculate PageRank on the full user subgraph to use as a centrality weight proxy
    node_keys = set(user_nodes.keys())
    pr_scores = graph_ranker.calculate_pagerank(node_keys, [e.dict() for e in user_edges])
    
    for nid in matched_ids:
        if nid in user_nodes:
            neighbors = graph_store.get_neighbors(nid)
            # Filter neighbors
            filtered_neighbors = []
            for n in neighbors:
                if n["node_id"] in user_nodes:
                    filtered_neighbors.append(n)
                    
            results.append(
                EntitySearchResponse(
                    entity=user_nodes[nid],
                    neighbors=filtered_neighbors,
                    score=round(pr_scores.get(nid, 0.5), 4)
                )
            )
            
    # Sort by PageRank score
    results.sort(key=lambda x: x.score, reverse=True)
    return results

@router.get("/subgraph", response_model=SubgraphResponse)
def get_subgraph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_doc_ids = get_user_doc_ids(db, current_user)
    user_nodes, user_edges = filter_user_graph(user_doc_ids)
    return SubgraphResponse(
        entities=list(user_nodes.values()),
        relationships=user_edges
    )

@router.get("/neighbors", response_model=NeighborsResponse)
def get_neighbors(
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    nid = entity_id.strip().lower()
    if nid not in graph_store.nodes:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")
        
    user_doc_ids = get_user_doc_ids(db, current_user)
    user_nodes, _ = filter_user_graph(user_doc_ids)
    
    if nid not in user_nodes:
        raise HTTPException(status_code=403, detail="Access denied to entity.")
        
    raw_neighbors = graph_store.get_neighbors(nid)
    filtered = [rn for rn in raw_neighbors if rn["node_id"] in user_nodes]
    
    return NeighborsResponse(
        entity_id=nid,
        neighbors=filtered
    )

@router.get("/statistics", response_model=GraphStats)
def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_doc_ids = get_user_doc_ids(db, current_user)
    user_nodes, user_edges = filter_user_graph(user_doc_ids)
    
    # Calculate stats exclusively for this user's graph portion
    num_nodes = len(user_nodes)
    num_edges = len(user_edges)
    
    visited = set()
    components = 0
    largest_comp = 0
    
    # Adjacency
    adj = {nid: [] for nid in user_nodes}
    for edge in user_edges:
        s, t = edge.source, edge.target
        if s in adj and t in adj:
            adj[s].append(t)
            adj[t].append(s)
            
    for nid in user_nodes:
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
    for node in user_nodes.values():
        ntype = node.type
        entity_freq[ntype] = entity_freq.get(ntype, 0) + 1
        
    rel_freq = {}
    for edge in user_edges:
        etype = edge.type
        rel_freq[etype] = rel_freq.get(etype, 0) + 1
        
    return GraphStats(
        node_count=num_nodes,
        edge_count=num_edges,
        connected_components=components,
        average_degree=round(avg_degree, 4),
        largest_component_size=largest_comp,
        entity_frequencies=entity_freq,
        relationship_frequencies=rel_freq,
        graph_density=round(density, 4),
        graph_coverage=1.0
    )

@router.get("/export", response_model=GraphExportResponse)
def export_graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_doc_ids = get_user_doc_ids(db, current_user)
    user_nodes, user_edges = filter_user_graph(user_doc_ids)
    return GraphExportResponse(
        nodes=user_nodes,
        edges=user_edges
    )
