import logging
from typing import List, Dict, Any

from app.models.document_chunk import DocumentChunk
from app.services.graph_store import graph_store
from app.services.entity_extractor import entity_extractor
from app.services.relationship_extractor import relationship_extractor

logger = logging.getLogger("app.services.graph_builder")

class GraphBuilder:
    def build_graph_for_document(self, document_id: int, chunks: List[DocumentChunk]):
        logger.info(f"Building/updating Knowledge Graph for document {document_id} with {len(chunks)} chunks.")
        
        # 1. Purge existing document subgraphs to avoid duplication on re-runs
        graph_store.delete_document_nodes(document_id)
        
        # 2. Extract and insert
        for chunk in chunks:
            text = chunk.chunk_text
            
            # Extract entities
            entities = entity_extractor.extract_entities(text)
            
            # Insert entities
            for ent in entities:
                ent_name = ent["name"]
                ent_type = ent["type"]
                aliases = ent.get("aliases", [])
                description = ent.get("description", "")
                
                # Merge document metadata into node properties
                properties = {
                    "document_ids": [document_id],
                    "chunk_ids": [chunk.id],
                    "description": description
                }
                
                graph_store.add_node(
                    node_id=ent_name,
                    name=ent_name,
                    node_type=ent_type,
                    aliases=aliases,
                    properties=properties
                )
                
            # Extract relationships using the localized entities list
            relationships = relationship_extractor.extract_relationships(text, entities)
            
            # Insert relationships
            for rel in relationships:
                source = rel["source"]
                target = rel["target"]
                rel_type = rel["type"]
                desc = rel.get("description", "")
                conf = rel.get("confidence", 1.0)
                
                properties = {
                    "document_id": document_id,
                    "chunk_id": chunk.id
                }
                
                graph_store.add_edge(
                    source=source,
                    target=target,
                    relationship_type=rel_type,
                    description=desc,
                    confidence=conf,
                    properties=properties
                )
                
        # 3. Persist modifications
        graph_store.save()
        logger.info(f"Finished graph update for document {document_id}.")

graph_builder = GraphBuilder()
