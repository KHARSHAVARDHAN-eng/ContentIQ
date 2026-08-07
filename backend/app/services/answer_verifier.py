import time
import json
import logging
import re
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
import numpy as np

from app.core.config import settings
from app.schemas.answer_verification import AnswerVerificationResult, ClaimVerificationResult
from app.services.claim_extractor import claim_extractor
from app.services.embedding_service import embedding_service

logger = logging.getLogger("app.services.answer_verifier")

class AnswerVerifierService:
    def verify(self, answer: str, context_chunks: List[Dict[str, Any]]) -> AnswerVerificationResult:
        start_time = time.time()
        
        # Normalize chunk IDs to string for comparison consistency
        normalized_chunks = []
        for c in context_chunks:
            normalized_c = dict(c)
            if "chunk_id" in normalized_c:
                normalized_c["chunk_id"] = str(normalized_c["chunk_id"])
            normalized_chunks.append(normalized_c)
        context_chunks = normalized_chunks

        # Handle empty/missing outputs
        if not answer:
            return AnswerVerificationResult(
                verified=True,
                overall_verification_score=1.0,
                claim_verifications=[],
                verification_summary="Empty answer provided.",
                claim_count=0,
                verified_count=0,
                partially_supported_count=0,
                unsupported_count=0,
                contradicted_count=0,
                latency_ms=0,
                metadata={"reason": "Empty answer"}
            )

        # 1. Claim Extraction
        claims = claim_extractor.extract_claims(answer)
        if not claims or not context_chunks:
            # If no context is available, all claims are unsupported
            claim_verifications = []
            for c in claims:
                claim_verifications.append(
                    ClaimVerificationResult(
                        claim_id=c["claim_id"],
                        claim_text=c["claim_text"],
                        verification_label="UNSUPPORTED",
                        confidence_score=0.0,
                        supporting_chunks=[],
                        evidence_text="",
                        explanation="No retrieved context chunks available for verification."
                    )
                )
            
            latency_ms = int((time.time() - start_time) * 1000)
            return AnswerVerificationResult(
                verified=False if claims else True,
                overall_verification_score=0.0 if claims else 1.0,
                claim_verifications=claim_verifications,
                verification_summary="All claims are unsupported due to missing retrieved context." if claims else "No claims found.",
                claim_count=len(claims),
                verified_count=0,
                partially_supported_count=0,
                unsupported_count=len(claims),
                contradicted_count=0,
                latency_ms=latency_ms,
                metadata={"reason": "No context or no claims"}
            )

        # 2. Claim Verification
        claim_verifications = []
        api_key = settings.GEMINI_API_KEY
        
        if api_key and settings.ANSWER_VERIFICATION_ENABLED:
            try:
                claim_verifications = self._verify_with_llm(claims, context_chunks, api_key)
            except Exception as e:
                logger.warning(f"LLM answer verification failed: {e}. Falling back to rule-based verifier.")
                claim_verifications = self._verify_with_rules(claims, context_chunks)
        else:
            claim_verifications = self._verify_with_rules(claims, context_chunks)

        # 3. Aggregate results and score
        verified_count = sum(1 for cv in claim_verifications if cv.verification_label == "VERIFIED")
        partially_supported_count = sum(1 for cv in claim_verifications if cv.verification_label == "PARTIALLY_SUPPORTED")
        unsupported_count = sum(1 for cv in claim_verifications if cv.verification_label == "UNSUPPORTED")
        contradicted_count = sum(1 for cv in claim_verifications if cv.verification_label == "CONTRADICTED")
        
        total_claims = len(claim_verifications)
        if total_claims > 0:
            overall_score = (verified_count + 0.5 * partially_supported_count) / total_claims
        else:
            overall_score = 1.0

        verified = overall_score >= settings.MIN_VERIFICATION_SCORE
        latency_ms = int((time.time() - start_time) * 1000)

        # Generate summary
        summary = (
            f"Factual verification completed. Claims: {total_claims} (Verified: {verified_count}, "
            f"Partially Supported: {partially_supported_count}, Unsupported: {unsupported_count}, "
            f"Contradicted: {contradicted_count}). Overall Verification Score: {overall_score:.2f}."
        )

        logger.info(
            f"Answer Verification: Total Claims: {total_claims} | Score: {overall_score:.2f} | "
            f"Verified: {verified} | Latency: {latency_ms}ms"
        )

        return AnswerVerificationResult(
            verified=verified,
            overall_verification_score=float(round(overall_score, 2)),
            claim_verifications=claim_verifications,
            verification_summary=summary,
            claim_count=total_claims,
            verified_count=verified_count,
            partially_supported_count=partially_supported_count,
            unsupported_count=unsupported_count,
            contradicted_count=contradicted_count,
            latency_ms=latency_ms,
            metadata={"debug": settings.ANSWER_VERIFICATION_DEBUG}
        )

    def _verify_with_llm(self, claims: List[Dict[str, Any]], context_chunks: List[Dict[str, Any]], api_key: str) -> List[ClaimVerificationResult]:
        genai.configure(api_key=api_key)
        
        # Prepare context representation for prompt
        evidence_text_blocks = []
        for c in context_chunks:
            evidence_text_blocks.append(
                f"Chunk ID: {c.get('chunk_id')}\n"
                f"Document: {c.get('document_name')}\n"
                f"Content: {c.get('chunk_text')}\n"
                "---"
            )
        evidence_context = "\n".join(evidence_text_blocks)

        system_instruction = (
            "You are an expert fact-checking agent. Your job is to verify a set of individual factual claims against the provided evidence context chunks.\n"
            "For each claim, you must return:\n"
            "1. 'claim_id': The exact claim ID provided.\n"
            "2. 'verification_label': Must be one of 'VERIFIED', 'PARTIALLY_SUPPORTED', 'UNSUPPORTED', or 'CONTRADICTED'.\n"
            "   - 'VERIFIED': The claim is fully and directly supported by the context.\n"
            "   - 'PARTIALLY_SUPPORTED': The claim is mostly supported, but contains minor details not found in the context.\n"
            "   - 'UNSUPPORTED': The context contains no information directly confirming or denying the claim.\n"
            "   - 'CONTRADICTED': The context explicitly denies or states the opposite of the claim.\n"
            "3. 'confidence_score': A float between 0.0 and 1.0 indicating your certainty.\n"
            "4. 'supporting_chunks': A list of Chunk IDs that contain the supporting or contradicting evidence.\n"
            "5. 'evidence_text': The exact phrase/sentence from the context verifying/contradicting the claim.\n"
            "6. 'explanation': A brief sentence explaining your choice.\n\n"
            "Return a JSON object containing a 'verifications' list of items adhering strictly to the schema."
        )

        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=system_instruction
        )

        claims_payload = json.dumps(claims)
        prompt = (
            f"EVIDENCE CONTEXT:\n{evidence_context}\n\n"
            f"CLAIMS TO VERIFY:\n{claims_payload}"
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )

        if response and response.text:
            data = json.loads(response.text.strip())
            verifications_raw = data.get("verifications", [])
            
            # Map back to ClaimVerificationResult
            results = []
            claims_map = {c["claim_id"]: c["claim_text"] for c in claims}
            for vr in verifications_raw:
                c_id = vr.get("claim_id")
                if c_id in claims_map:
                    results.append(
                        ClaimVerificationResult(
                            claim_id=c_id,
                            claim_text=claims_map[c_id],
                            verification_label=vr.get("verification_label", "UNSUPPORTED"),
                            confidence_score=float(vr.get("confidence_score", 0.0)),
                            supporting_chunks=[str(cid) for cid in vr.get("supporting_chunks", [])],
                            evidence_text=vr.get("evidence_text", ""),
                            explanation=vr.get("explanation", "")
                        )
                    )
            
            # Pad any claims that LLM missed
            results_ids = {r.claim_id for r in results}
            for c in claims:
                if c["claim_id"] not in results_ids:
                    results.append(
                        ClaimVerificationResult(
                            claim_id=c["claim_id"],
                            claim_text=c["claim_text"],
                            verification_label="UNSUPPORTED",
                            confidence_score=0.0,
                            supporting_chunks=[],
                            evidence_text="",
                            explanation="Failed to verify via LLM response mapping."
                        )
                    )
            return results
            
        raise ValueError("Invalid verification response from Gemini")

    def _verify_with_rules(self, claims: List[Dict[str, Any]], context_chunks: List[Dict[str, Any]]) -> List[ClaimVerificationResult]:
        results = []
        
        # Precompute chunk sentence embeddings to speed up semantic matching
        chunk_sentences: List[Tuple[str, str, np.ndarray]] = [] # (chunk_id, sentence_text, embedding)
        for c in context_chunks:
            cid = c.get("chunk_id", "")
            text = c.get("chunk_text", "")
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            for s in sentences:
                if len(s) >= 10:
                    emb = embedding_service.get_embedding(s)
                    chunk_sentences.append((cid, s, np.array(emb)))

        for c in claims:
            claim_id = c["claim_id"]
            claim_text = c["claim_text"]
            claim_emb = np.array(embedding_service.get_embedding(claim_text))
            
            best_similarity = 0.0
            best_chunk_id = ""
            best_sentence = ""

            for cid, sent, sent_emb in chunk_sentences:
                sim = self._cosine_similarity(claim_emb, sent_emb)
                if sim > best_similarity:
                    best_similarity = sim
                    best_chunk_id = cid
                    best_sentence = sent

            # Exclude negations to detect contradictions
            negation_words = ["not", "never", "no", "cannot", "isn't", "aren't", "wasn't", "weren't", "don't", "doesn't", "didn't", "won't", "can't", "shouldn't", "wouldn't"]
            is_claim_negated = any(w in claim_text.lower().split() for w in negation_words)
            is_evidence_negated = any(w in best_sentence.lower().split() for w in negation_words)

            if best_similarity >= settings.VERIFICATION_CONFIDENCE_THRESHOLD:
                # High similarity
                if is_claim_negated != is_evidence_negated and best_similarity >= 0.85:
                    label = "CONTRADICTED"
                    explanation = f"Contradiction detected: claim negation state matches opposite assertion (similarity: {best_similarity:.2f})."
                else:
                    label = "VERIFIED"
                    explanation = f"Verified: High semantic match found in context (similarity: {best_similarity:.2f})."
                confidence = best_similarity
                supporting = [best_chunk_id] if best_chunk_id else []
                evidence = best_sentence
            elif best_similarity >= 0.60:
                # Moderate similarity
                if is_claim_negated != is_evidence_negated:
                    label = "CONTRADICTED"
                    explanation = f"Contradiction detected: claim negation state matches opposite assertion (similarity: {best_similarity:.2f})."
                else:
                    label = "PARTIALLY_SUPPORTED"
                    explanation = f"Partially supported: Moderate match found in context (similarity: {best_similarity:.2f})."
                confidence = best_similarity
                supporting = [best_chunk_id] if best_chunk_id else []
                evidence = best_sentence
            else:
                # Low similarity
                label = "UNSUPPORTED"
                confidence = best_similarity
                supporting = []
                evidence = ""
                explanation = f"Unsupported: No matching factual statement found in context (highest similarity: {best_similarity:.2f})."

            results.append(
                ClaimVerificationResult(
                    claim_id=claim_id,
                    claim_text=claim_text,
                    verification_label=label,
                    confidence_score=float(round(confidence, 2)),
                    supporting_chunks=supporting,
                    evidence_text=evidence,
                    explanation=explanation
                )
            )

        return results

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

answer_verifier = AnswerVerifierService()
