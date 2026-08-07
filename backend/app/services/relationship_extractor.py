import re
import json
import logging
from typing import List, Dict, Any, Set
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger("app.services.relationship_extractor")

RELATIONSHIP_KEYWORDS = {
    "uses": ["uses", "using", "utilize", "apply", "applies"],
    "depends_on": ["depends on", "depend on", "rely on", "reliance", "requires", "require"],
    "part_of": ["part of", "member of", "element of", "belongs to", "belonging to"],
    "authored_by": ["authored by", "written by", "author", "write", "writer"],
    "created_by": ["created by", "built by", "designed by", "produced by", "made by"],
    "connected_to": ["connected to", "linked to", "associated with", "joins", "connects"],
    "located_in": ["located in", "situated in", "found in", "inside", "within"],
    "parent_of": ["parent of", "mother of", "father of", "leads to", "controls"],
    "child_of": ["child of", "son of", "daughter of", "derived from", "descendant"],
    "references": ["references", "refers to", "cites", "citation", "referring"],
}

class RelationshipExtractor:
    def extract_relationships(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        api_key = settings.GEMINI_API_KEY
        if api_key:
            try:
                return self._extract_with_llm(text, entities, api_key)
            except Exception as e:
                logger.warning(f"LLM relationship extraction failed: {e}. Falling back to rule-based extractor.")
                
        return self._extract_rule_based(text, entities)

    def _extract_with_llm(self, text: str, entities: List[Dict[str, Any]], api_key: str) -> List[Dict[str, Any]]:
        genai.configure(api_key=api_key)
        
        entities_list = [e["name"] for e in entities]
        system_instruction = (
            "You are a precise Relationship Extraction agent. Identify relationships between the provided entities in the text.\n"
            "Valid relationship types: uses, depends_on, part_of, authored_by, created_by, connected_to, located_in, parent_of, child_of, references, related_to.\n"
            "Return a JSON array containing objects matching this schema:\n"
            "[\n"
            "  {\n"
            "    \"source\": \"canonical name of source entity (string, exact case-match from provided list)\",\n"
            "    \"target\": \"canonical name of target entity (string, exact case-match from provided list)\",\n"
            "    \"type\": \"relationship type (string: uses | depends_on | part_of | authored_by | created_by | connected_to | located_in | parent_of | child_of | references | related_to)\",\n"
            "    \"description\": \"short explanation of why this link exists in context (string)\",\n"
            "    \"confidence\": 0.95\n"
            "  }\n"
            "]\n"
            "Only return relationships where both source and target are present in the provided entities list.\n"
            "Do not return extra markup, markdown fences or explanations outside the JSON."
        )

        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=system_instruction
        )

        prompt = f"ENTITIES:\n{json.dumps(entities_list)}\n\nTEXT:\n{text}"
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )

        if response and response.text:
            return json.loads(response.text.strip())
        return []

    def _extract_rule_based(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Split text into sentences for sentence-level co-occurrence checking
        sentences = re.split(r'(?<=[.!?])\s+', text)
        relationships = []
        seen_edges: Set[tuple] = set()

        if len(entities) < 2:
            return []

        for sentence in sentences:
            sentence_lower = sentence.lower()
            # Find which entities occur in this sentence
            present_entities = []
            for ent in entities:
                ent_name = ent["name"]
                # Match entity name as a substring (ignoring case)
                if ent_name.lower() in sentence_lower:
                    present_entities.append(ent)
            
            # If two or more entities occur in the same sentence, evaluate relationships
            if len(present_entities) >= 2:
                for i in range(len(present_entities)):
                    for j in range(i + 1, len(present_entities)):
                        ent1 = present_entities[i]["name"]
                        ent2 = present_entities[j]["name"]
                        
                        # Avoid duplicate bidirectional edges within the same block
                        edge_key = (ent1.lower(), ent2.lower())
                        if edge_key in seen_edges:
                            continue
                        seen_edges.add(edge_key)

                        # Check verb/linking keyword patterns between ent1 and ent2
                        rel_type = "related_to"
                        confidence = 0.50
                        description = f"{ent1} is co-mentioned with {ent2} in context."

                        # Find matching relation keywords in the sentence
                        for ktype, keywords in RELATIONSHIP_KEYWORDS.items():
                            for kw in keywords:
                                if kw in sentence_lower:
                                    rel_type = ktype
                                    confidence = 0.75
                                    description = f"Sentence implies {ent1} {ktype.replace('_', ' ')} {ent2}."
                                    break
                            if rel_type != "related_to":
                                break

                        relationships.append({
                            "source": ent1,
                            "target": ent2,
                            "type": rel_type,
                            "description": description,
                            "confidence": confidence
                        })

        return relationships

relationship_extractor = RelationshipExtractor()
