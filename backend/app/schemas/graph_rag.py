from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class Entity(BaseModel):
    id: str
    name: str
    type: str
    aliases: List[str] = []
    description: Optional[str] = None
    properties: Dict[str, Any] = {}

class Relationship(BaseModel):
    source: str
    target: str
    type: str
    description: Optional[str] = None
    confidence: float = 1.0
    properties: Dict[str, Any] = {}

class GraphStats(BaseModel):
    node_count: int
    edge_count: int
    connected_components: int
    average_degree: float
    largest_component_size: int
    entity_frequencies: Dict[str, int]
    relationship_frequencies: Dict[str, int]
    graph_density: float
    graph_coverage: float

class EntitySearchResponse(BaseModel):
    entity: Entity
    neighbors: List[Dict[str, Any]]
    score: float

class SubgraphResponse(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]

class NeighborsResponse(BaseModel):
    entity_id: str
    neighbors: List[Dict[str, Any]]

class GraphExportResponse(BaseModel):
    nodes: Dict[str, Entity]
    edges: List[Relationship]
