import json
import traceback
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.rag_evaluation import RAGEvaluation
from app.models.document import Document
from app.core.config import settings
from app.core.database import SessionLocal
import google.generativeai as genai

class EvaluationService:
    def log_chat_event(
        self,
        user_id: int,
        query: str,
        answer: str,
        latency_ms: int,
        citations: List[Dict[str, Any]]
    ):
        """
        Runs async/sync RAG quality assessment and inserts an evaluation log into the DB.
        """
        db = SessionLocal()
        try:
            # Extract document ID from citations if present
            document_id = None
            if citations:
                # Find document name matching first citation
                doc_name = citations[0].get("document_name")
                if doc_name:
                    doc = db.query(Document).filter(Document.name == doc_name, Document.user_id == user_id).first()
                    if doc:
                        document_id = doc.id

            # Compile context from citations
            context_text = "\n".join([c.get("chunk_text", "") for c in citations])
            
            # Compute scores via Gemini or programmatic fallback
            faithfulness, relevance = self.evaluate_rag_response(query, answer, context_text)

            eval_entry = RAGEvaluation(
                query=query,
                answer=answer,
                latency_ms=latency_ms,
                retrieved_chunks_count=len(citations),
                user_feedback=0,
                faithfulness_score=faithfulness,
                answer_relevance_score=relevance,
                user_id=user_id,
                document_id=document_id
            )
            db.add(eval_entry)
            db.commit()
            db.refresh(eval_entry)
            print(f"Logged RAG Evaluation entry: ID {eval_entry.id}, Faithfulness: {faithfulness}, Relevance: {relevance}")
            return eval_entry.id
        except Exception as e:
            print(f"Failed to log evaluation: {e}")
            traceback.print_exc()
            return None
        finally:
            db.close()

    def evaluate_rag_response(self, query: str, answer: str, context: str) -> Tuple[float, float]:
        """
        Evaluates faithfulness (groundedness) and query relevance using Gemini.
        Falls back programmatically if key is not configured.
        """
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return self._compute_fallback_scores(query, answer, context)

        if not context or not answer:
            return 0.0, 0.0

        try:
            import time
            import logging
            logger = logging.getLogger("app.services.eval_service")
            
            genai.configure(api_key=api_key)
            system_instruction = (
                "You are an evaluator for a RAG system.\n"
                "Evaluate the RAG output based on: \n"
                "1. Faithfulness (Groundedness): Is the answer fully grounded in the provided context? (0.0 = not grounded, 1.0 = fully grounded)\n"
                "2. Relevance: Does the answer address the question? (0.0 = not relevant, 1.0 = fully relevant)\n"
                "Return ONLY a JSON block like: {\"faithfulness\": 0.95, \"relevance\": 1.0}. Do not add markup or explanations."
            )
            
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=system_instruction
            )
            
            prompt = (
                f"Context:\n{context}\n\n"
                f"User Question:\n{query}\n\n"
                f"Generated Answer:\n{answer}\n"
            )
            
            # Request response from model with retry and exponential backoff
            max_retries = 3
            backoff_factor = 2
            initial_delay = 1.0 # seconds
            
            response = None
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.0
                        )
                    )
                    break
                except Exception as ex:
                    last_exception = ex
                    logger.warning(f"Gemini API evaluation attempt {attempt + 1} failed: {ex}. Retrying...")
                    if attempt < max_retries - 1:
                        sleep_time = initial_delay * (backoff_factor ** attempt)
                        time.sleep(sleep_time)
            
            if response is None:
                raise last_exception
            
            text = response.text.strip()
            # Clean up potential markdown formatting block
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            scores = json.loads(text)
            faithfulness = float(scores.get("faithfulness", 1.0))
            relevance = float(scores.get("relevance", 1.0))
            
            # Clamp scores between 0.0 and 1.0
            return max(0.0, min(1.0, faithfulness)), max(0.0, min(1.0, relevance))
        except Exception as e:
            import logging
            logger = logging.getLogger("app.services.eval_service")
            logger.error(f"Gemini evaluation error: {e}", exc_info=True)
            return self._compute_fallback_scores(query, answer, context)

    def _compute_fallback_scores(self, query: str, answer: str, context: str) -> Tuple[float, float]:
        """
        Simple deterministic overlap metric fallback scoring.
        """
        if not answer:
            return 0.0, 0.0
            
        # Groundedness fallback: check percentage of answer words present in context
        ans_words = [w.lower().strip(",.?!:;()\"'") for w in answer.split() if len(w) > 3]
        if not ans_words:
            faithfulness = 1.0
        else:
            ctx_lower = context.lower()
            matches = sum(1 for w in ans_words if w in ctx_lower)
            faithfulness = round(matches / len(ans_words), 2)
            
        # Relevance fallback: check query keywords in answer
        q_words = [w.lower().strip(",.?!:;()\"'") for w in query.split() if len(w) > 3]
        if not q_words:
            relevance = 1.0
        else:
            ans_lower = answer.lower()
            matches = sum(1 for w in q_words if w in ans_lower)
            relevance = round(matches / len(q_words), 2)
            
        return faithfulness, relevance

    def get_user_logs(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        # Join documents table to obtain the document name
        results = db.query(
            RAGEvaluation, Document.name
        ).outerjoin(
            Document, RAGEvaluation.document_id == Document.id
        ).filter(
            RAGEvaluation.user_id == user_id
        ).order_by(
            RAGEvaluation.created_at.desc()
        ).all()

        logs = []
        for eval_model, doc_name in results:
            log_dict = {
                "id": eval_model.id,
                "query": eval_model.query,
                "answer": eval_model.answer,
                "latency_ms": eval_model.latency_ms,
                "retrieved_chunks_count": eval_model.retrieved_chunks_count,
                "user_feedback": eval_model.user_feedback,
                "faithfulness_score": eval_model.faithfulness_score,
                "answer_relevance_score": eval_model.answer_relevance_score,
                "created_at": eval_model.created_at,
                "user_id": eval_model.user_id,
                "document_id": eval_model.document_id,
                "document_name": doc_name
            }
            logs.append(log_dict)
        return logs

    def get_aggregate_stats(self, db: Session, user_id: int) -> Dict[str, Any]:
        """
        Aggregates RAG telemetry performance metrics.
        """
        # Fetch all evaluations for user
        evals = db.query(RAGEvaluation).filter(RAGEvaluation.user_id == user_id).all()
        
        total = len(evals)
        if total == 0:
            return {
                "total_queries": 0,
                "avg_latency_ms": 0.0,
                "avg_faithfulness": 0.0,
                "avg_relevance": 0.0,
                "thumbs_up_count": 0,
                "thumbs_down_count": 0,
                "positive_feedback_pct": 0.0,
                "daily_metrics": []
            }
            
        avg_latency = sum(e.latency_ms for e in evals) / total
        avg_faith = sum(e.faithfulness_score or 0.0 for e in evals) / total
        avg_rel = sum(e.answer_relevance_score or 0.0 for e in evals) / total
        
        thumbs_up = sum(1 for e in evals if e.user_feedback == 1)
        thumbs_down = sum(1 for e in evals if e.user_feedback == -1)
        rated = sum(1 for e in evals if e.user_feedback != 0)
        
        positive_feedback_pct = round((thumbs_up / rated) * 100, 1) if rated > 0 else 0.0
        
        # Aggregate daily metrics
        # Group evaluations by date (YYYY-MM-DD)
        daily_groups = {}
        for e in evals:
            date_str = e.created_at.strftime("%Y-%m-%d")
            if date_str not in daily_groups:
                daily_groups[date_str] = []
            daily_groups[date_str].append(e)
            
        daily_metrics = []
        for date_str, day_evals in sorted(daily_groups.items()):
            day_total = len(day_evals)
            day_latency = sum(e.latency_ms for e in day_evals) / day_total
            day_faith = sum(e.faithfulness_score or 0.0 for e in day_evals) / day_total
            day_rel = sum(e.answer_relevance_score or 0.0 for e in day_evals) / day_total
            
            day_up = sum(1 for e in day_evals if e.user_feedback == 1)
            day_down = sum(1 for e in day_evals if e.user_feedback == -1)
            day_rated = day_up + day_down
            day_pos_pct = round((day_up / day_rated) * 100, 1) if day_rated > 0 else 0.0
            
            daily_metrics.append({
                "date": date_str,
                "avg_latency": round(day_latency, 1),
                "avg_faithfulness": round(day_faith, 2),
                "avg_relevance": round(day_rel, 2),
                "total_queries": day_total,
                "positive_feedback_pct": day_pos_pct
            })
            
        return {
            "total_queries": total,
            "avg_latency_ms": round(avg_latency, 1),
            "avg_faithfulness": round(avg_faith, 2),
            "avg_relevance": round(avg_rel, 2),
            "thumbs_up_count": thumbs_up,
            "thumbs_down_count": thumbs_down,
            "positive_feedback_pct": positive_feedback_pct,
            "daily_metrics": daily_metrics
        }

eval_service = EvaluationService()
