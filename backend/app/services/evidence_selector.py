import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger("app.services.evidence_selector")

class EvidenceSelector:
    def __init__(self):
        self.stopwords = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "is", "was", "were", "are", "been", "be", "have", "has", "had", "do", "does", "did",
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by",
            "about", "against", "between", "into", "through", "during", "before", "after",
            "above", "below", "from", "up", "down", "out", "off", "over", "under",
            "again", "further", "then", "once", "here", "there", "all", "any", "both", "each",
            "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "can", "will", "just", "should", "now",
            "explain", "sequence", "events", "finding", "find", "describe", "details", "her", "him", "his", "their", "them",
            "tell", "me", "happened", "happen", "happens", "does", "did", "doing", "done"
        }

    def _clean_header_noise(self, text: str) -> str:
        """
        Strips redundant section headers, document titles, or category labels from sentence starts.
        Strips header prefixes (e.g., "Hanuman's Mission in Lanka: Hanuman led...") if the header 
        is generic (e.g., "Section 1:", "Summary:") or if the text following the colon already 
        contains topic words from the header.
        Preserves key-value field labels (e.g., "Secret OCR Code: Antigravity RAG works!") where 
        the header contains the essential field key.
        """
        if not text:
            return ""
        cleaned = text.strip()
        
        generic_header_words = {"section", "chapter", "summary", "overview", "part", "note", "details", "background", "introduction"}

        for _ in range(3):
            # Check for title header prefix ending with a colon
            m = re.match(r'^(?:[A-Za-z0-9 \t\'\-\.]{2,60}):\s*(.*)$', cleaned)
            if m:
                header_part = cleaned[:m.end(0) - len(m.group(1))].rstrip(":\t ")
                rest_part = m.group(1).strip()
                
                header_words = set(re.findall(r'\b[a-z0-9]{3,}\b', header_part.lower()))
                rest_words = set(re.findall(r'\b[a-z0-9]{3,}\b', rest_part.lower()))
                
                is_generic = bool(header_words & generic_header_words)
                shares_topic_word = bool(header_words & rest_words)
                
                # Strip header if it is generic section noise or if rest_part repeats topic word
                if (is_generic or shares_topic_word) and rest_part:
                    cleaned = rest_part
            
            # Remove ALL-CAPS multi-word headers at start if followed by normal text
            cleaned = re.sub(r'^[A-Z0-9 \t:,\-\.]{4,}(?=[A-Z][a-z])', '', cleaned).strip()
        
        # Normalize multiple whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _extract_query_terms(self, question: str) -> Dict[str, Any]:
        """
        Domain-independent query parsing:
        Extracts informative terms, subject nouns/entities, and detects query intent.
        """
        q_lower = question.lower()
        raw_words = re.findall(r'\b[a-z0-9]+\b', q_lower)
        informative_terms = [w for w in raw_words if len(w) >= 3 and w not in self.stopwords]
        
        # Detect sequence/timeline intent
        is_sequence_query = any(k in q_lower for k in [
            "sequence", "timeline", "chronological", "steps", "events from", "all actions", "from ", "after ", "process"
        ])
        
        # Extract focus subject entity (e.g. noun immediately following "did", "was", "is", "how", "who")
        focus_subject_match = re.search(r'\b(?:did|was|is|does|about|for|how|who|what)\s+([A-Z][a-z0-9]+)\b', question)
        focus_subjects = set()
        if focus_subject_match:
            focus_entity = focus_subject_match.group(1).lower()
            if focus_entity not in self.stopwords and focus_entity not in {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "explain", "describe", "details"}:
                focus_subjects.add(focus_entity)

        # Subject terms: Capitalized words / Proper Nouns / ALL-CAPS acronyms from question (excluding sentence-starting question words)
        capitalized_entities = [
            w.lower() for w in re.findall(r'\b[A-Z0-9]{2,}\b|\b[A-Z][a-z0-9]+\b', question) 
            if w.lower() not in self.stopwords and w.lower() not in {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "explain", "describe", "details"}
        ]
        
        primary_subjects = focus_subjects | set(capitalized_entities) if focus_subjects else set(capitalized_entities)
        
        # Domain-independent synonym expansion for core query intent terms
        intent_synonym_map = {
            "help": {"help", "helped", "assist", "assisted", "support", "mobilize", "mobilized", "sent", "send"},
            "find": {"find", "finding", "found", "locate", "located", "locating", "search", "searching", "discover"},
            "kidnap": {"kidnap", "kidnapped", "abduct", "abducted", "abduction", "stole", "seize", "seized", "lure", "lured", "disguise", "disguised"},
            "battle": {"battle", "fought", "fight", "war", "slay", "slain", "kill", "killed", "attack"},
            "pay": {"pay", "paid", "cost", "price", "amount", "billion", "million", "dollar", "fee"},
            "acquire": {"acquire", "acquired", "acquisition", "bought", "purchase", "purchased"},
            "role": {"role", "position", "title", "job", "post", "offered", "offer"},
            "duration": {"duration", "period", "term", "month", "months", "year", "years", "time"},
            "intern": {"intern", "internship", "trainee", "apprentice"}
        }
        expanded_query_terms = set(informative_terms)
        for term in list(informative_terms):
            for base_key, syns in intent_synonym_map.items():
                if term == base_key or term in syns:
                    expanded_query_terms.update(syns)

        non_subject_terms = {w for w in expanded_query_terms if w not in primary_subjects}
        query_intent_terms = non_subject_terms
        
        # If no capitalized entities, use non-action informative terms as subjects
        if not primary_subjects:
            for t in informative_terms:
                if t not in query_intent_terms and t not in {"who", "what", "where", "when", "why", "how"}:
                    primary_subjects.add(t)

        return {
            "query_lower": q_lower,
            "raw_terms": expanded_query_terms,
            "primary_subjects": primary_subjects,
            "focus_subjects": focus_subjects,
            "query_intent_terms": query_intent_terms,
            "is_sequence": is_sequence_query
        }

    def select_evidence(self, question: str, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Domain-independent query-aware evidence selection:
        1. Parses candidate context chunks into clean sentences/clauses.
        2. Strips raw document headers and category labels.
        3. Evaluates semantic & term relevance of each sentence to the query.
        4. Prunes unrelated adjacent sentences (e.g., dropping monkey army details when asking about Sita's kidnapping).
        5. Preserves sequence flow for timeline/sequence queries.
        6. Maintains citation mapping back to original chunks.
        """
        if not context_chunks:
            return []

        q_info = self._extract_query_terms(question)
        raw_query_terms = q_info["raw_terms"]
        primary_subjects = q_info["primary_subjects"]
        query_intent_terms = q_info["query_intent_terms"]
        is_sequence = q_info["is_sequence"]
        is_process_query = (
            any(k in question.lower() for k in ["how did", "how was", "how does", "how can", "why ", "explain", "describe", "process", "sequence"]) 
            and not any(k in question.lower() for k in ["how much", "how many", "how long", "how far", "how old"])
        )

        if not raw_query_terms and not primary_subjects:
            return []

        candidate_sentences = []
        seen_norms = set()

        for chunk_idx, chunk in enumerate(context_chunks):
            text = chunk.get("chunk_text", "").strip()
            if not text:
                continue

            # Split on sentence boundaries (newlines or sentence end punctuation)
            raw_sents = [s.strip() for s in re.split(r'[\r\n]+|(?<=[.!?;])\s+', text) if s.strip()]
            for sent_idx, s in enumerate(raw_sents):
                clean_s = self._clean_header_noise(s)
                if not clean_s or len(clean_s.split()) < 3:
                    continue

                norm = re.sub(r'[^\w\s]', '', clean_s.lower()).strip()
                if not norm or norm in seen_norms:
                    continue
                seen_norms.add(norm)

                # Extract words from original sentence before header stripping so header keywords (e.g. "Position:") are preserved for subject matching
                orig_norm = re.sub(r'[^\w\s]', '', s.lower()).strip()
                s_words = set(re.findall(r'\b[a-z0-9]+\b', orig_norm))
                
                # Calculate term match overlap
                matched_query_terms = [qt for qt in raw_query_terms if qt in s_words or any(qt in w or w in qt for w in s_words if len(w) >= 4)]
                match_count = len(matched_query_terms)

                # Primary subject entity bonus: Does sentence mention core subject entity?
                subject_matches = [ps for ps in primary_subjects if ps in s_words or any(ps in w or w in ps for w in s_words if len(w) >= 4)]
                subject_score = len(subject_matches)

                # Action/intent verb bonus: Does sentence match query intent terms?
                intent_matches = [it for it in query_intent_terms if it in s_words or any(it in w or w in it for w in s_words if len(w) >= 4)]
                intent_score = len(intent_matches)

                # Sentence Relevance Score
                chunk_rank_score = float(chunk.get("score", 0.0))
                
                score = (match_count * 2.0) + (subject_score * 4.0) + (intent_score * 3.0) + (chunk_rank_score * 0.5)

                candidate_sentences.append({
                    "sentence": clean_s,
                    "norm": norm,
                    "words": s_words,
                    "match_count": match_count,
                    "subject_score": subject_score,
                    "intent_score": intent_score,
                    "score": score,
                    "chunk_index": chunk_idx,
                    "sent_index": sent_idx,
                    "chunk": chunk
                })

        if not candidate_sentences:
            return []

        # Filter out sentences with 0 query/subject matches
        matching_sents = [cs for cs in candidate_sentences if cs["match_count"] > 0 or cs["subject_score"] > 0]
        if not matching_sents:
            return []

        selected_sents = []

        if is_sequence:
            # Sequence query: Sort matching sentences chronologically by chunk_index & sent_index
            matching_sents.sort(key=lambda x: (x["chunk_index"], x["sent_index"]))
            selected_sents = matching_sents[:6]
        else:
            # Focused Query: Filter strictly for sentences that address the query's primary subject(s) AND intent
            top_sentence = max(matching_sents, key=lambda x: (x["score"], x["intent_score"], x["subject_score"], x["match_count"]))
            
            focused_candidates = []
            focus_subjects = q_info.get("focus_subjects", set())

            for cs in matching_sents:
                if cs == top_sentence:
                    focused_candidates.append(cs)
                else:
                    is_adjacent_cause_effect = (is_process_query and cs["chunk_index"] == top_sentence["chunk_index"] and abs(cs["sent_index"] - top_sentence["sent_index"]) <= 2)
                    has_intent = cs["intent_score"] > 0 or (cs["match_count"] >= 2 and cs["score"] >= top_sentence["score"] * 0.6) or is_adjacent_cause_effect
                    has_subject = (any(ps in cs["words"] for ps in primary_subjects) if primary_subjects else True) or is_adjacent_cause_effect
                    
                    if focus_subjects and not any(fs in cs["words"] for fs in focus_subjects):
                        has_subject = False

                    if has_subject and has_intent and (cs["score"] >= (top_sentence["score"] * 0.45) or is_adjacent_cause_effect):
                        focused_candidates.append(cs)

            if is_process_query:
                # Chronological sort within top chunk to preserve cause->effect narrative
                focused_candidates.sort(key=lambda x: (x["chunk_index"], x["sent_index"]))
                selected_sents = focused_candidates[:4]
            else:
                selected_sents = focused_candidates[:3]
            selected_sents.sort(key=lambda x: (x["chunk_index"], x["sent_index"]))
            selected_sents.sort(key=lambda x: (x["chunk_index"], x["sent_index"]))

        if not selected_sents:
            return []

        # Maintain Citation Mapping: Group selected sentences back by chunk
        pruned_chunks_map = {}
        for cs in selected_sents:
            cid = str(cs["chunk"].get("chunk_id", cs["chunk_index"]))
            if cid not in pruned_chunks_map:
                pruned_chunks_map[cid] = {
                    "chunk_id": cs["chunk"].get("chunk_id", cid),
                    "document_id": cs["chunk"].get("document_id", 0),
                    "document_name": cs["chunk"].get("document_name", "Unknown"),
                    "page_number": cs["chunk"].get("page_number", 1),
                    "score": cs["chunk"].get("score", 0.0),
                    "sentences": []
                }
            if cs["sentence"] not in pruned_chunks_map[cid]["sentences"]:
                pruned_chunks_map[cid]["sentences"].append(cs["sentence"])

        result_chunks = []
        for cid, data in pruned_chunks_map.items():
            combined_text = " ".join(data["sentences"]).strip()
            if combined_text:
                result_chunks.append({
                    "chunk_id": data["chunk_id"],
                    "document_id": data["document_id"],
                    "document_name": data["document_name"],
                    "page_number": data["page_number"],
                    "chunk_text": combined_text,
                    "score": data["score"]
                })

        return result_chunks


evidence_selector = EvidenceSelector()

