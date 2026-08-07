import re
import json
import logging
from typing import List, Dict, Any
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger("app.services.entity_extractor")

# Common keywords mapping to classify rule-based entities
KEYWORD_MAPPING = {
    "organization": ["company", "inc", "corp", "limited", "ltd", "association", "university", "foundation", "agency", "organization"],
    "location": ["city", "country", "state", "nation", "mountain", "river", "capital", "island", "street", "road", "park"],
    "technology": ["software", "hardware", "framework", "system", "algorithm", "python", "javascript", "rag", "database", "ai", "model"],
    "product": ["version", "device", "telescope", "tool", "app", "application", "instrument", "model"],
    "event": ["conference", "meeting", "launch", "war", "anniversary", "birthday", "summit"]
}

class EntityExtractor:
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        api_key = settings.GEMINI_API_KEY
        if api_key:
            try:
                return self._extract_with_llm(text, api_key)
            except Exception as e:
                logger.warning(f"LLM entity extraction failed: {e}. Falling back to rule-based extractor.")
                
        return self._extract_rule_based(text)

    def _extract_with_llm(self, text: str, api_key: str) -> List[Dict[str, Any]]:
        genai.configure(api_key=api_key)
        
        system_instruction = (
            "You are a precise Named Entity Recognition (NER) agent. Extract all major entities from the provided text.\n"
            "Entities to extract: person, organization, location, technology, product, event, date, abbreviation, alias, concept.\n"
            "Return a JSON array containing objects matching this schema:\n"
            "[\n"
            "  {\n"
            "    \"name\": \"canonical name of entity (string, capitalized appropriately)\",\n"
            "    \"type\": \"entity type (string: Person, Organization, Location, Technology, Product, Event, Date, Abbreviation, Alias, Concept)\",\n"
            "    \"aliases\": [\"alias1\", \"alias2\"],\n"
            "    \"description\": \"brief summary context (string or null)\"\n"
            "  }\n"
            "]\n"
            "Do not return extra markup, markdown fences or explanations outside the JSON."
        )

        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=system_instruction
        )

        response = model.generate_content(
            f"TEXT TO EXTRACT:\n{text}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )

        if response and response.text:
            return json.loads(response.text.strip())
        return []

    def _extract_rule_based(self, text: str) -> List[Dict[str, Any]]:
        raw_matches = re.findall(r'\b[A-Z][a-zA-Z0-9\-]*(?:\s+[A-Z][a-zA-Z0-9\-]*)*\b', text)
        
        entities_map = {}
        text_lower = text.lower()

        for match in raw_matches:
            name = match.strip()
            # Ignore short words or numbers or common words that might get capitalized at start of line
            if len(name) < 3 or name.lower() in [
                "the", "and", "for", "this", "that", "with", "from", "your", "they", "document", "page", "section"
            ]:
                continue
                
            canonical_name = name
            entity_id = canonical_name.lower()
            
            if entity_id in entities_map:
                continue

            # Basic entity classification heuristic
            entity_type = "Concept"
            for ktype, keywords in KEYWORD_MAPPING.items():
                if any(kw in text_lower for kw in keywords) and any(kw in name.lower() for kw in keywords):
                    entity_type = ktype.title()
                    break

            # Date check
            if re.search(r'\b(19|20)\d{2}\b', name) or any(m in name.lower() for m in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]):
                entity_type = "Date"

            # Person check (has space, capital letter, no common keywords)
            if " " in name and entity_type == "Concept":
                entity_type = "Person"

            entities_map[entity_id] = {
                "name": canonical_name,
                "type": entity_type,
                "aliases": [],
                "description": f"Extracted via rule-based heuristics from text context."
            }

        return list(entities_map.values())

entity_extractor = EntityExtractor()
