import json
import logging
import google.generativeai as genai
from app.core.config import settings
from app.schemas.query_analysis import QueryAnalysis

logger = logging.getLogger("app.services.query_analyzer")

class QueryAnalyzerService:
    def __init__(self):
        self.model_name = settings.QUERY_ANALYZER_MODEL

    def analyze(self, query: str) -> QueryAnalysis:
        cleaned_query = query.strip()
        if not cleaned_query:
            return QueryAnalysis(
                raw_query="",
                intent="conversational",
                complexity="Simple",
                keywords=[],
                suggested_filters=None,
                intent_confidence=1.0,
                complexity_confidence=1.0,
                reasoning="Empty user query."
            )

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.info("Warning: GEMINI_API_KEY is not set. Running fallback rule-based query analysis.")
            return self._fallback_analyze(cleaned_query)

        try:
            genai.configure(api_key=api_key)
            
            system_instruction = (
                "You are an advanced query analysis agent. Analyze the user's search or chat query and classify it.\n"
                "You MUST return a JSON object with the following fields:\n"
                "1. 'intent': One of: factual, summarization, comparison, explanation, procedural, analytical, conversational, multi-intent.\n"
                "   Choose 'multi-intent' if the query exhibits multiple clear intents (e.g. asking to compare AND summarize).\n"
                "2. 'complexity': One of: Simple, Medium, Complex.\n"
                "   Consider factors: query length, number of entities, number of intents, multi-part structure, comparison/summarization request, and reasoning depth.\n"
                "3. 'intent_confidence': A float score between 0.0 and 1.0 representing classification confidence.\n"
                "4. 'complexity_confidence': A float score between 0.0 and 1.0 representing classification confidence.\n"
                "5. 'keywords': A list of key search terms extracted from the query.\n"
                "6. 'suggested_filters': An optional dictionary of filters if applicable (keep as null if none).\n"
                "7. 'reasoning': A detailed text explanation explaining why you chose this intent classification and complexity level.\n"
                "8. 'query_classification': One of: informational, keyword, conversational.\n"
                "9. 'ambiguity_score': A float between 0.0 and 1.0 indicating if the query is vague, missing details, or lacks clear context.\n"
                "10. 'missing_context': A boolean indicating if crucial details/context are missing to answer the query.\n"
                "11. 'detected_entities': A list of names, places, database names, or specific entities extracted.\n"
                "12. 'technical_keywords': A list of technical terms, acronyms, or code elements detected.\n"
                "\n"
                "Ensure the response is valid JSON and strictly adheres to this schema. Do not add any markdown formatting outside JSON."
            )
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            
            # Request JSON output
            response = model.generate_content(
                f"Analyze this query: '{cleaned_query}'",
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.QUERY_ANALYZER_TEMPERATURE,
                    response_mime_type="application/json"
                )
            )
            
            if response and response.text:
                data = json.loads(response.text.strip())
                
                # Validate intent
                valid_intents = {"factual", "summarization", "comparison", "explanation", "procedural", "analytical", "conversational", "multi-intent"}
                intent = data.get("intent", "factual")
                if intent not in valid_intents:
                    intent = "factual"
                    
                # Validate complexity
                valid_complexities = {"Simple", "Medium", "Complex"}
                complexity = data.get("complexity", "Simple")
                if complexity not in valid_complexities:
                    complexity = "Simple"
                    
                # Validate confidence scores
                intent_conf = float(data.get("intent_confidence", 1.0))
                intent_conf = max(0.0, min(1.0, intent_conf))
                
                complexity_conf = float(data.get("complexity_confidence", 1.0))
                complexity_conf = max(0.0, min(1.0, complexity_conf))
                
                # Format keywords
                keywords = data.get("keywords", [])
                if not isinstance(keywords, list):
                    keywords = [str(keywords)]
                keywords = [str(k) for k in keywords]
                
                suggested_filters = data.get("suggested_filters")
                if not isinstance(suggested_filters, dict):
                    suggested_filters = None
                    
                reasoning = data.get("reasoning", "LLM-based classification decision.")
                
                # Parse additional Query Transformation fields
                query_classification = data.get("query_classification", "informational")
                if query_classification not in {"informational", "keyword", "conversational"}:
                    query_classification = "informational"
                    
                ambiguity_score = float(data.get("ambiguity_score", 0.0))
                ambiguity_score = max(0.0, min(1.0, ambiguity_score))
                
                missing_context = bool(data.get("missing_context", False))
                
                detected_entities = data.get("detected_entities", [])
                if not isinstance(detected_entities, list):
                    detected_entities = [str(detected_entities)]
                detected_entities = [str(e) for e in detected_entities]
                
                technical_keywords = data.get("technical_keywords", [])
                if not isinstance(technical_keywords, list):
                    technical_keywords = [str(technical_keywords)]
                technical_keywords = [str(k) for k in technical_keywords]
                
                # Log classification reasoning
                logger.info(f"Gemini Query Analysis for query='{cleaned_query}': intent={intent} ({intent_conf}), complexity={complexity} ({complexity_conf}), reasoning='{reasoning}'")

                return QueryAnalysis(
                    raw_query=cleaned_query,
                    intent=intent,
                    complexity=complexity,
                    keywords=keywords,
                    suggested_filters=suggested_filters,
                    intent_confidence=round(intent_conf, 2),
                    complexity_confidence=round(complexity_conf, 2),
                    reasoning=reasoning,
                    query_classification=query_classification,
                    ambiguity_score=round(ambiguity_score, 2),
                    missing_context=missing_context,
                    detected_entities=detected_entities,
                    technical_keywords=technical_keywords
                )
            else:
                logger.warning("Empty response from Gemini API during query analysis. Falling back to rule-based analysis.")
                return self._fallback_analyze(cleaned_query)
                
        except Exception as e:
            logger.error(f"Error calling Gemini API for query analysis: {e}. Falling back to rule-based analysis.", exc_info=True)
            return self._fallback_analyze(cleaned_query)

    def _fallback_analyze(self, query: str) -> QueryAnalysis:
        import re
        cleaned = query.strip()
        lower_q = cleaned.lower()
        
        # Tokenize and strip punctuation
        words = [w.strip("?,.:;!") for w in cleaned.split() if w.strip()]
        word_count = len(words)
        
        # 1. Intent Classification Scoring
        intent_scores = {
            "conversational": 0,
            "summarization": 0,
            "comparison": 0,
            "explanation": 0,
            "procedural": 0,
            "analytical": 0,
            "factual": 0
        }
        
        # Heuristic keywords/phrases maps
        intent_rules = {
            "conversational": ["hello", "hi", "hey", "thanks", "thank you", "greetings", "good morning", "good afternoon", "please"],
            "summarization": ["summarize", "summary", "tl;dr", "brief", "outline", "overview", "synopsis", "recap", "gist"],
            "comparison": ["compare", "difference", "versus", "vs", "similarities", "comparison", "contrast", "distinguish", "differential"],
            "explanation": ["why", "explain", "explanation", "reason", "cause", "rationalize", "how does", "what causes"],
            "procedural": ["how to", "how do i", "steps", "procedure", "guide", "instructions", "tutorial", "method", "recipe", "walkthrough"],
            "analytical": ["analyze", "analysis", "statistics", "percent", "average", "total", "count", "metrics", "trend", "data", "mean", "median", "sum"],
            "factual": ["what", "when", "who", "where", "which", "identify", "retrieve", "list", "name", "define"]
        }
        
        # Score each intent
        for intent_name, keywords in intent_rules.items():
            for kw in keywords:
                # Count match matches using regex word/phrase boundary
                matches = len(re.findall(r'\b' + re.escape(kw) + r'\b', lower_q))
                if matches > 0:
                    intent_scores[intent_name] += matches * 1.5
                    
        # Filter scoring intents
        active_intents = [name for name, score in intent_scores.items() if score > 0]
        
        # Polite/conversational triggers should not combine to form multi-intent
        if "conversational" in active_intents and len(active_intents) > 1:
            active_intents.remove("conversational")
            
        # Generic factual triggers should not combine to form multi-intent with other specific semantic intents
        if "factual" in active_intents and len(active_intents) > 1:
            active_intents.remove("factual")
        
        # Determine intent & intent reasoning
        if len(active_intents) >= 2:
            intent = "multi-intent"
            intent_confidence = settings.QUERY_ANALYZER_FALLBACK_INTENT_CONF - 0.1  # slightly lower confidence for multi-intent fallback
            intent_reason = f"Detected multiple active query intents: {', '.join(active_intents)}."
        elif len(active_intents) == 1:
            intent = active_intents[0]
            intent_confidence = settings.QUERY_ANALYZER_FALLBACK_INTENT_CONF
            intent_reason = f"Single primary intent trigger detected for '{intent}'."
        else:
            intent = "factual"  # Default
            intent_confidence = settings.QUERY_ANALYZER_FALLBACK_INTENT_CONF - 0.15 # lower confidence for default
            intent_reason = "No specific intent keywords matched; fell back to default 'factual' intent."
            
        # 2. Complexity Estimation Scoring
        # Consider length, entities, intents, multi-part, reasoning depth
        complexity_reasons = []
        comp_score = 0.0
        
        # Factor A: Query Length
        if word_count > 15:
            comp_score += 0.45
            complexity_reasons.append(f"Length of {word_count} words is long (>15 words)")
        elif word_count > 10:
            comp_score += 0.35
            complexity_reasons.append(f"Length of {word_count} words is medium-long (>10 words)")
        elif word_count > 5:
            comp_score += 0.25
            complexity_reasons.append(f"Length of {word_count} words is short-medium (>5 words)")
            
        # Factor B: Entities Count (Capitalized words in query, excluding first word)
        entities = []
        for i, word in enumerate(words):
            if i > 0 and word and word[0].isupper():
                entities.append(word)
        entity_count = len(entities)
        if entity_count >= 2:
            comp_score += 0.25
            complexity_reasons.append(f"Detected multiple entities ({entity_count}): {entities}")
        elif entity_count == 1:
            comp_score += 0.1
            complexity_reasons.append(f"Detected single entity: {entities[0]}")
            
        # Factor C: Number of Intents / Multi-part clauses
        if intent == "multi-intent":
            comp_score += 0.3
            complexity_reasons.append("Multi-intent query structure")
        # Check coordinates/subordinating conjunctions for multi-part questions
        conjunctions = ["and also", "as well as", "along with", "then", "but also", "in addition to"]
        has_conjunction = any(re.search(r'\b' + re.escape(c) + r'\b', lower_q) for c in conjunctions)
        if has_conjunction or ("," in query and any(re.search(r'\b' + re.escape(w) + r'\b', lower_q) for w in ["and", "or"])):
            comp_score += 0.2
            complexity_reasons.append("Multi-part query structure using conjunctions/clause separators")
            
        # Factor D: Reasoning Depth
        reasoning_depth_triggers = ["because", "why", "since", "consequently", "therefore", "implications", "impact of", "how does", "result of", "affecting"]
        if any(re.search(r'\b' + re.escape(t) + r'\b', lower_q) for t in reasoning_depth_triggers):
            comp_score += 0.25
            complexity_reasons.append("Reasoning depth triggers present (asking for causes/effects)")
            
        # Factor E: High-level processing intents
        if intent in ["comparison", "summarization", "procedural", "analytical"]:
            comp_score += 0.2
            complexity_reasons.append(f"Requires high-level processing ('{intent}')")
            
        # Map score to complexity
        if comp_score >= 0.75:
            complexity = "Complex"
        elif comp_score >= 0.35:
            complexity = "Medium"
        else:
            complexity = "Simple"
            
        complexity_confidence = settings.QUERY_ANALYZER_FALLBACK_COMPLEXITY_CONF
        
        reasoning_str = f"Intent [{intent}]: {intent_reason} | Complexity [{complexity}] (Score: {comp_score:.2f}): {'; '.join(complexity_reasons) if complexity_reasons else 'Short/simple query struct.'}"
        
        # Log detailed reasoning explaining classification decision
        logger.info(f"Fallback Query Analysis for query='{query}': {reasoning_str}")
        
        # Extract keywords
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "of", "to", "in", "on", "for", "with",
            "what", "how", "why", "where", "who", "when", "which", "and", "or", "but", "if", "then",
            "this", "that", "these", "those", "about", "by", "from", "at", "as", "be", "been", "have", "has", "had", "do", "does", "did"
        }
        keywords = []
        for w in words:
            w_clean = w.lower()
            if w_clean not in stop_words and len(w_clean) > 2:
                if w_clean not in keywords:
                    keywords.append(w_clean)
                    
        # Fallback Query Classification
        if intent == "conversational":
            query_classification = "conversational"
        elif word_count <= 2:
            query_classification = "keyword"
        else:
            query_classification = "informational"
            
        # Fallback Ambiguity Scoring & Missing Context
        ambiguous_terms = ["it", "this", "that", "there", "them", "do it", "fix this", "its"]
        has_ambiguous_term = any(re.search(r'\b' + re.escape(t) + r'\b', lower_q) for t in ambiguous_terms)
        
        if intent == "conversational":
            ambiguity_score = 0.0
            missing_context = False
        elif has_ambiguous_term and len(entities) == 0:
            ambiguity_score = 0.8
            missing_context = True
        elif word_count <= 2 and not any(re.search(r'\b' + re.escape(t) + r'\b', lower_q) for t in ["rag", "llm", "sql", "api", "pdf", "db"]):
            ambiguity_score = 0.6
            missing_context = True
        else:
            ambiguity_score = 0.1
            missing_context = False
            
        # Technical Keywords
        tech_vocab = {"rag", "llm", "sql", "api", "pdf", "db", "database", "postgres", "postgresql", "mysql", "qdrant", "vector", "embedding", "cross-encoder", "rerank", "hybrid", "chunking", "hallucination"}
        technical_keywords = [w for w in keywords if w in tech_vocab]
        
        return QueryAnalysis(
            raw_query=cleaned,
            intent=intent,
            complexity=complexity,
            keywords=keywords,
            suggested_filters=None,
            intent_confidence=round(intent_confidence, 2),
            complexity_confidence=round(complexity_confidence, 2),
            reasoning=reasoning_str,
            query_classification=query_classification,
            ambiguity_score=round(ambiguity_score, 2),
            missing_context=missing_context,
            detected_entities=entities,
            technical_keywords=technical_keywords
        )

query_analyzer = QueryAnalyzerService()
