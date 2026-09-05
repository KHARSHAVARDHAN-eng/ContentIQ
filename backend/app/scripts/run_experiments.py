import os
import sys
import time
import json
import csv
import logging
import math
import numpy as np
import scipy.stats as stats
from typing import List, Dict, Any

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.document_chunk import DocumentChunk
from app.models.chunk_embedding import ChunkEmbedding
from app.models.rag_evaluation import RAGEvaluation
from app.models.chat_history import ChatSession, ChatMessage
from app.models.study_tool import FlashCardDeck, FlashCard, StudyPack
from app.services.vector_store import vector_store
from app.services.embedding_service import embedding_service
from app.services.adaptive_chunking import adaptive_chunker, RulesBasedAdaptiveChunker
from app.services.hybrid_retriever import hybrid_retriever
from app.services.bm25_retriever import bm25_retriever
from app.services.reranker import reranker
from app.services.context_compressor import context_compressor
from app.services.evidence_selector import evidence_selector
from app.services.graph_retriever import GraphRetriever
from app.services.llm_service import llm_service
from app.services.hallucination_detector import hallucination_detector
from app.services.answer_verifier import answer_verifier
from app.services.confidence_engine import confidence_engine
from app.services.evaluation_engine import evaluation_engine

logger = logging.getLogger("run_experiments")
logging.basicConfig(level=logging.INFO)

# Ground truth text corpora for the 5 benchmark domains
DOMAIN_DOCUMENTS = {
    "Literature": {
        "name": "ramayana_full.txt",
        "text": (
            "Section 1: The Abduction of Sita at Panchavati.\n"
            "Maricha disguised himself as a golden deer to lure Rama away from the hermitage. "
            "Sita requested Rama to capture the deer. Lakshmana later left the hut after hearing a deceptive cry imitating Rama. "
            "Ravana, disguised as a mendicant, seized the opportunity to abduct Sita from Panchavati and carried her off in his flying chariot, Pushpaka Vimana, to Lanka.\n\n"
            "Section 2: Jatayu's Sacrifice.\n"
            "The noble bird king Jatayu bravely fought Ravana in an attempt to rescue Sita. "
            "Ravana clipped Jatayu's wings, leaving him mortally wounded. "
            "When Rama and Lakshmana arrived searching for Sita, Jatayu provided the initial location clue that Ravana had abducted Sita and taken her south.\n\n"
            "Section 3: The Alliance with Sugriva.\n"
            "Rama and Lakshmana searched tirelessly, meeting Shabari and eventually Sugriva at Mount Rishyamuka. "
            "Sugriva formed an alliance with Rama, regained his kingdom from Vali with Rama's assistance, and mobilized his monkey army, sending search parties in four cardinal directions to locate Sita.\n\n"
            "Section 4: Hanuman's Mission in Lanka.\n"
            "Hanuman led the southern search party, leaped across the ocean to Lanka, and located Sita in Ashoka Vatika. "
            "He conveyed Rama's message and signet ring, defeated many warriors, allowed himself to be captured, set parts of Lanka ablaze with his burning tail, and returned to report to Rama."
        )
    },
    "Financial": {
        "name": "Financial_Report.pdf",
        "text": (
            "Acme Corp Corporate & Earnings Report FY2025.\n"
            "In Q3 2025, Acme Corp completed the acquisition of Beta Ltd for $2 billion following regulatory approval. "
            "Beta Ltd previously employed 4,000 people across its engineering and operations divisions. "
            "Acme Corp later opened a state-of-the-art research and development center in London. "
            "Acme Corp reported a revenue growth of 18% in FY2025 following the successful acquisition integration."
        )
    },
    "Legal / HR": {
        "name": "offerLetter.pdf",
        "text": (
            "Employment Offer Agreement.\n"
            "Position: Data Analyst Intern\n"
            "Duration of internship: 4 month internship\n"
            "Confidentiality & Data Protection: All company data, analytics models, and client lists remain strictly proprietary. "
            "The candidate must maintain strict confidentiality regarding proprietary analytics models and client information throughout and after the 4 month internship period."
        )
    },
    "Sci-Fi Fiction": {
        "name": "DocumentIQ_Test_Story.txt",
        "text": (
            "The Starlight-7 Chronicle.\n"
            "This is a mock test story for Raman Iyer.\n"
            "Raman Iyer used a brass telescope named Starlight-7 at his hilltop observatory. "
            "It was an antique telescope he cherished for observing celestial anomalies and stellar formations. "
            "Maya logged telescope telemetric readings alongside Raman during their evening observations."
        )
    },
    "Scanned / OCR": {
        "name": "test_ocr_asset.png",
        "text": (
            "Scanned Technical Asset & OCR Validation Document.\n"
            "Secret OCR Code: Antigravity RAG works!\n"
            "Scanned PDF secret message: Qdrant matches!\n"
            "Extraction metadata: Resolution 800x200 pixels with high OCR confidence."
        )
    }
}

FIXED_CHUNK_SIZE = 500
FIXED_CHUNK_OVERLAP = 100

COLLECTION_FIXED = "research_fixed"
COLLECTION_ADAPTIVE = "research_adaptive"

def fixed_size_chunking(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += (chunk_size - chunk_overlap)
    return chunks

def seed_environment(db) -> User:
    print("=== Seeding Research Database & Vector Collections ===")
    user = db.query(User).filter(User.email == "research_eval@example.com").first()
    if not user:
        user = User(
            email="research_eval@example.com",
            hashed_password="hashed_research_password",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Clean existing research documents for user
    existing_docs = db.query(Document).filter(Document.user_id == user.id).all()
    for d in existing_docs:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).delete()
        db.delete(d)
    db.commit()

    # Re-create collections in Qdrant
    vector_store.create_collection(COLLECTION_FIXED, vector_size=384)
    vector_store.create_collection(COLLECTION_ADAPTIVE, vector_size=384)

    bm25_fixed_corpus = []
    bm25_adaptive_corpus = []

    fixed_point_id = 10000
    adaptive_point_id = 20000

    chunker = RulesBasedAdaptiveChunker()

    for domain_key, doc_info in DOMAIN_DOCUMENTS.items():
        doc_name = doc_info["name"]
        text_content = doc_info["text"]

        doc_record = Document(
            user_id=user.id,
            name=doc_name,
            path=f"uploads/{doc_name}",
            size=str(len(text_content.encode('utf-8'))),
            status="INDEXED"
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        # 1. Fixed Chunking -> COLLECTION_FIXED
        raw_fixed_chunks = fixed_size_chunking(text_content, FIXED_CHUNK_SIZE, FIXED_CHUNK_OVERLAP)
        fixed_points = []
        for idx, chunk_str in enumerate(raw_fixed_chunks):
            c_record = DocumentChunk(
                document_id=doc_record.id,
                chunk_index=idx,
                chunk_text=chunk_str,
                chunk_length=len(chunk_str),
                page_number=1
            )
            db.add(c_record)
            db.commit()
            db.refresh(c_record)

            vec = embedding_service.get_embedding(chunk_str)
            fixed_points.append({
                "chunk_id": fixed_point_id,
                "document_id": doc_record.id,
                "page_number": 1,
                "chunk_text": chunk_str,
                "vector": vec
            })
            bm25_fixed_corpus.append({
                "chunk_id": str(fixed_point_id),
                "document_id": doc_record.id,
                "page_number": 1,
                "chunk_text": chunk_str
            })
            fixed_point_id += 1

        vector_store.upsert_chunks_bulk(fixed_points, collection_name=COLLECTION_FIXED)

        # 2. Adaptive Chunking -> COLLECTION_ADAPTIVE
        raw_adaptive_chunks, meta = chunker.chunk_text(text_content, doc_name)
        adaptive_points = []
        for idx, chunk_str in enumerate(raw_adaptive_chunks):
            c_record = DocumentChunk(
                document_id=doc_record.id,
                chunk_index=idx + 100,
                chunk_text=chunk_str,
                chunk_length=len(chunk_str),
                page_number=1
            )
            db.add(c_record)
            db.commit()
            db.refresh(c_record)

            vec = embedding_service.get_embedding(chunk_str)
            adaptive_points.append({
                "chunk_id": adaptive_point_id,
                "document_id": doc_record.id,
                "page_number": 1,
                "chunk_text": chunk_str,
                "vector": vec
            })
            bm25_adaptive_corpus.append({
                "chunk_id": str(adaptive_point_id),
                "document_id": doc_record.id,
                "page_number": 1,
                "chunk_text": chunk_str
            })
            adaptive_point_id += 1

        vector_store.upsert_chunks_bulk(adaptive_points, collection_name=COLLECTION_ADAPTIVE)

    print(f"Seeding complete. User ID: {user.id}. Fixed chunks: {fixed_point_id - 10000}, Adaptive chunks: {adaptive_point_id - 20000}.")
    return user

def run_single_pipeline_query(
    db,
    user: User,
    question: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Executes a single benchmark question under a controlled baseline configuration.
    Measures retrieval, reranking, synthesis, and grounding stages.
    """
    start_total = time.perf_counter()
    
    col_name = config["collection_name"]
    use_hybrid = config["use_hybrid"]
    use_reranker = config["use_reranker"]
    use_compression = config["use_compression"]
    use_evidence_selection = config["use_evidence_selection"]
    use_graphrag = config["use_graphrag"]
    use_verification = config["use_verification"]
    top_k = config["top_k"]
    
    # Set feature flag settings for run
    settings.HYBRID_RETRIEVAL_ENABLED = use_hybrid
    settings.RERANKER_ENABLED = use_reranker
    settings.CONTEXT_COMPRESSION_ENABLED = use_compression
    settings.EVIDENCE_SELECTION_ENABLED = use_evidence_selection
    settings.GRAPHRAG_ENABLED = use_graphrag
    
    user_doc_ids = [doc.id for doc in db.query(Document).filter(Document.user_id == user.id).all()]

    # Stage 1: Retrieval
    t_ret_start = time.perf_counter()
    retrieved_hits, hr_meta = hybrid_retriever.search(
        db=db,
        query=question,
        user_doc_ids=user_doc_ids,
        limit=10 if use_reranker else top_k,
        collection_name=col_name
    )
    t_ret_end = time.perf_counter()
    retrieval_latency = (t_ret_end - t_ret_start) * 1000.0

    # GraphRAG Traversal (if enabled)
    graph_chunks = []
    if use_graphrag:
        try:
            g_retriever = GraphRetriever()
            graph_chunks, _ = g_retriever.retrieve_graph_context(db, question, user_doc_ids, depth=2)
        except Exception as ge:
            logger.warning(f"GraphRAG traversal error: {ge}")

    # Combine hits
    combined_hits = list(retrieved_hits)
    if graph_chunks:
        existing_cids = {h["chunk_id"] for h in combined_hits}
        for gc in graph_chunks:
            if gc.get("chunk_id") not in existing_cids:
                gc["score"] = 0.50
                combined_hits.append(gc)

    # Stage 2: Reranking (if enabled)
    t_rerank_start = time.perf_counter()
    if use_reranker and combined_hits:
        reranked_hits, _ = reranker.rerank(question, combined_hits)
        candidate_chunks = reranked_hits[:top_k]
    else:
        candidate_chunks = combined_hits[:top_k]
    t_rerank_end = time.perf_counter()
    rerank_latency = (t_rerank_end - t_rerank_start) * 1000.0

    # Stage 3: Context Compression (if enabled)
    if use_compression and candidate_chunks:
        comp_res = context_compressor.compress(question, candidate_chunks)
        compressed_c = comp_res.compressed_chunks
        if compressed_c:
            candidate_chunks = [
                {
                    "chunk_id": cc.chunk_id,
                    "document_id": cc.document_id,
                    "document_name": cc.document_name,
                    "page_number": cc.page_number,
                    "chunk_text": cc.chunk_text,
                    "score": cc.score
                } for cc in compressed_c
            ]

    # Stage 4: Synthesis & Evidence Selection
    t_gen_start = time.perf_counter()
    gen_result = llm_service.generate_answer(question, candidate_chunks)
    t_gen_end = time.perf_counter()
    gen_latency = (t_gen_end - t_gen_start) * 1000.0

    answer = gen_result.get("answer", "")
    citations = gen_result.get("sources", [])

    # Stage 5: Verification & Grounding (if enabled)
    pipeline_outputs = {}
    if use_verification and candidate_chunks and answer:
        h_res = hallucination_detector.detect(question, candidate_chunks, answer)
        v_res = answer_verifier.verify(answer, candidate_chunks)
        c_res = confidence_engine.compute_confidence(
            answer=answer,
            citations=citations,
            hallucination_detection=h_res,
            answer_verification=v_res
        )
        pipeline_outputs = {
            "hallucination_detection": h_res,
            "answer_verification": v_res,
            "confidence": c_res
        }

    total_latency = (time.perf_counter() - start_total) * 1000.0

    return {
        "question": question,
        "answer": answer,
        "citations": citations,
        "candidate_chunks": candidate_chunks,
        "pipeline_outputs": pipeline_outputs,
        "stage_latencies": {
            "retrieval_ms": round(retrieval_latency, 2),
            "rerank_ms": round(rerank_latency, 2),
            "generation_ms": round(gen_latency, 2),
            "total_ms": round(total_latency, 2)
        }
    }

def main():
    print("==================================================")
    print(" STARTING CONTROLLED RAG ABLATION BENCHMARK RUN   ")
    print("==================================================")

    db = SessionLocal()
    try:
        user = seed_environment(db)

        # Load benchmark dataset
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        dataset_path = os.path.join(project_root, "../docs/research/benchmark_dataset.json")
        if not os.path.exists(dataset_path):
            dataset_path = os.path.join(project_root, "docs/research/benchmark_dataset.json")
        with open(dataset_path, "r") as f:
            dataset = json.load(f)

        print(f"Loaded {len(dataset)} benchmark questions from {dataset_path}.")

        # 6 Baseline Configurations
        configurations = {
            "B1": {
                "name": "B1 Basic RAG",
                "collection_name": COLLECTION_FIXED,
                "use_hybrid": False,
                "use_reranker": False,
                "use_compression": False,
                "use_evidence_selection": False,
                "use_graphrag": False,
                "use_verification": False,
                "top_k": 5
            },
            "B2": {
                "name": "B2 Adaptive Chunking",
                "collection_name": COLLECTION_ADAPTIVE,
                "use_hybrid": False,
                "use_reranker": False,
                "use_compression": False,
                "use_evidence_selection": False,
                "use_graphrag": False,
                "use_verification": False,
                "top_k": 5
            },
            "B3": {
                "name": "B3 Adaptive + Hybrid",
                "collection_name": COLLECTION_ADAPTIVE,
                "use_hybrid": True,
                "use_reranker": False,
                "use_compression": False,
                "use_evidence_selection": False,
                "use_graphrag": False,
                "use_verification": False,
                "top_k": 5
            },
            "B4": {
                "name": "B4 Adaptive + Hybrid + Reranker",
                "collection_name": COLLECTION_ADAPTIVE,
                "use_hybrid": True,
                "use_reranker": True,
                "use_compression": False,
                "use_evidence_selection": False,
                "use_graphrag": False,
                "use_verification": False,
                "top_k": 5
            },
            "B5a": {
                "name": "B5a Full System (No GraphRAG)",
                "collection_name": COLLECTION_ADAPTIVE,
                "use_hybrid": True,
                "use_reranker": True,
                "use_compression": True,
                "use_evidence_selection": True,
                "use_graphrag": False,
                "use_verification": True,
                "top_k": 5
            },
            "B5b": {
                "name": "B5b Full System (With GraphRAG)",
                "collection_name": COLLECTION_ADAPTIVE,
                "use_hybrid": True,
                "use_reranker": True,
                "use_compression": True,
                "use_evidence_selection": True,
                "use_graphrag": True,
                "use_verification": True,
                "top_k": 5
            }
        }

        # Warm-up query before timed evaluation
        print("\nPerforming warm-up query...")
        run_single_pipeline_query(db, user, "Warm-up question for system initialization", configurations["B1"])

        raw_results = {}
        configuration_summaries = {}

        output_dir = os.path.join(project_root, "../docs/research/results")
        if not os.path.exists(os.path.dirname(output_dir)):
            output_dir = os.path.join(project_root, "docs/research/results")
        os.makedirs(output_dir, exist_ok=True)

        for cfg_id, cfg in configurations.items():
            print(f"\n--- Evaluating Configuration {cfg_id}: {cfg['name']} ---")
            cfg_raw_items = []
            
            context_precisions = []
            context_recalls = []
            faithfulness_scores = []
            relevancy_scores = []
            hallucination_rates = []
            verification_scores = []
            citation_coverages = []
            latencies = []

            for idx, q_item in enumerate(dataset):
                q_id = q_item["id"]
                domain = q_item["domain"]
                q_text = q_item["question"]
                q_type = q_item["question_type"]
                ref_docs = q_item.get("reference_documents", [])
                ground_truth = q_item.get("ground_truth_answer", "")

                out = run_single_pipeline_query(db, user, q_text, cfg)

                # Evaluate using evaluation engine
                eval_res = evaluation_engine.evaluate_response(
                    question=q_text,
                    answer=out["answer"],
                    citations=out["citations"],
                    context_chunks=out["candidate_chunks"],
                    pipeline_outputs=out["pipeline_outputs"],
                    ground_truth=ground_truth,
                    reference_documents=ref_docs
                )

                m_dict = eval_res.metrics
                cp = m_dict.get("context_precision", None)
                cp_val = cp.score if cp else 1.0

                cr = m_dict.get("context_recall", None)
                cr_val = cr.score if cr else 1.0

                fa = m_dict.get("faithfulness", None)
                fa_val = fa.score if fa else 1.0

                ar = m_dict.get("answer_relevancy", None)
                ar_val = ar.score if ar else 1.0

                hr = m_dict.get("hallucination_rate", None)
                hr_val = hr.score if hr else 0.0

                vs = m_dict.get("verification_success", None)
                vs_val = vs.score if vs else 1.0

                cc = m_dict.get("citation_coverage", None)
                cc_val = cc.score if cc else 1.0

                lat_val = out["stage_latencies"]["total_ms"]

                context_precisions.append(cp_val)
                context_recalls.append(cr_val)
                faithfulness_scores.append(fa_val)
                relevancy_scores.append(ar_val)
                hallucination_rates.append(hr_val)
                verification_scores.append(vs_val)
                citation_coverages.append(cc_val)
                latencies.append(lat_val)

                item_result = {
                    "question_id": q_id,
                    "domain": domain,
                    "question_type": q_type,
                    "question": q_text,
                    "answer": out["answer"],
                    "citations": out["citations"],
                    "retrieved_chunks_count": len(out["candidate_chunks"]),
                    "retrieved_documents": list({c.get("document_name") for c in out["candidate_chunks"] if c.get("document_name")}),
                    "metrics": {
                        "context_precision": cp_val,
                        "context_recall": cr_val,
                        "faithfulness": fa_val,
                        "answer_relevancy": ar_val,
                        "hallucination_rate": hr_val,
                        "verification_success": vs_val,
                        "citation_coverage": cc_val,
                        "overall_score": eval_res.overall_score
                    },
                    "stage_latencies": out["stage_latencies"]
                }
                cfg_raw_items.append(item_result)

                print(f"[{cfg_id}] Q{idx+1:02d}/{len(dataset)} ({q_id}): Relevancy={ar_val:.2f}, Faithfulness={fa_val:.2f}, Latency={lat_val:.0f}ms")

            raw_results[cfg_id] = {
                "config": cfg,
                "items": cfg_raw_items
            }

            configuration_summaries[cfg_id] = {
                "name": cfg["name"],
                "context_precision_mean": float(np.mean(context_precisions)),
                "context_precision_std": float(np.std(context_precisions)),
                "context_recall_mean": float(np.mean(context_recalls)),
                "context_recall_std": float(np.std(context_recalls)),
                "faithfulness_mean": float(np.mean(faithfulness_scores)),
                "faithfulness_std": float(np.std(faithfulness_scores)),
                "answer_relevancy_mean": float(np.mean(relevancy_scores)),
                "answer_relevancy_std": float(np.std(relevancy_scores)),
                "hallucination_rate_mean": float(np.mean(hallucination_rates)),
                "hallucination_rate_std": float(np.std(hallucination_rates)),
                "verification_success_mean": float(np.mean(verification_scores)),
                "verification_success_std": float(np.std(verification_scores)),
                "citation_coverage_mean": float(np.mean(citation_coverages)),
                "citation_coverage_std": float(np.std(citation_coverages)),
                "latency_p50_ms": float(np.percentile(latencies, 50)),
                "latency_p95_ms": float(np.percentile(latencies, 95)),
                "latency_mean_ms": float(np.mean(latencies))
            }

        # Statistical Comparisons (Paired Wilcoxon Signed-Rank Tests)
        print("\n=== Calculating Statistical Comparisons (Wilcoxon Signed-Rank Tests) ===")
        paired_comparisons = [
            ("B1", "B2", "Adaptive Chunking Impact"),
            ("B2", "B3", "Hybrid Retrieval Impact"),
            ("B3", "B4", "Cross-Encoder Reranking Impact"),
            ("B4", "B5a", "Context Compression & Evidence Selection Impact"),
            ("B5a", "B5b", "GraphRAG Traversal Contribution")
        ]

        stat_results = {}
        for c1, c2, label in paired_comparisons:
            ar1 = [it["metrics"]["answer_relevancy"] for it in raw_results[c1]["items"]]
            ar2 = [it["metrics"]["answer_relevancy"] for it in raw_results[c2]["items"]]
            
            diffs = np.array(ar2) - np.array(ar1)
            nonzero_diffs = diffs[diffs != 0]

            if len(nonzero_diffs) > 0:
                stat_res = stats.wilcoxon(ar1, ar2, zero_method='pratt')
                p_val = float(stat_res.pvalue)
                stat_val = float(stat_res.statistic)
            else:
                p_val = 1.0
                stat_val = 0.0

            mean_diff = float(np.mean(diffs))
            direction = "positive improvement" if mean_diff > 0 else ("no change" if mean_diff == 0 else "degradation")
            sig = bool(p_val < 0.05)

            stat_results[f"{c1}_vs_{c2}"] = {
                "comparison": label,
                "baseline_1": c1,
                "baseline_2": c2,
                "mean_diff": round(mean_diff, 4),
                "effect_direction": direction,
                "statistic": round(stat_val, 4),
                "p_value": round(p_val, 5),
                "statistically_significant_alpha_0_05": sig
            }
            print(f"Paired Test {c1} vs {c2} ({label}): Mean Diff = {mean_diff:+.4f}, p-value = {p_val:.5f}, Significant = {sig}")

        # Save machine-readable outputs
        print("\n=== Saving Results ===")
        raw_path = os.path.join(output_dir, "raw_results.json")
        with open(raw_path, "w") as f:
            json.dump(raw_results, f, indent=2)

        summary_json_path = os.path.join(output_dir, "summary.json")
        with open(summary_json_path, "w") as f:
            json.dump(configuration_summaries, f, indent=2)

        summary_csv_path = os.path.join(output_dir, "summary.csv")
        with open(summary_csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Configuration", "Context Precision", "Context Recall", "Faithfulness",
                "Answer Relevancy", "Hallucination Rate", "Verification Success",
                "Citation Coverage", "Median Latency (ms)", "P95 Latency (ms)"
            ])
            for cfg_id, s in configuration_summaries.items():
                writer.writerow([
                    s["name"],
                    f"{s['context_precision_mean']:.4f}",
                    f"{s['context_recall_mean']:.4f}",
                    f"{s['faithfulness_mean']:.4f}",
                    f"{s['answer_relevancy_mean']:.4f}",
                    f"{s['hallucination_rate_mean']:.4f}",
                    f"{s['verification_success_mean']:.4f}",
                    f"{s['citation_coverage_mean']:.4f}",
                    f"{s['latency_p50_ms']:.2f}",
                    f"{s['latency_p95_ms']:.2f}"
                ])

        stats_path = os.path.join(output_dir, "statistical_analysis.json")
        with open(stats_path, "w") as f:
            json.dump(stat_results, f, indent=2)

        exp_config_path = os.path.join(output_dir, "experiment_config.json")
        exp_config = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": {
                "os": sys.platform,
                "python_version": sys.version
            },
            "models": {
                "embedding_model": settings.EMBEDDING_MODEL_NAME,
                "reranker_model": settings.RERANKER_MODEL_NAME,
                "llm_model": settings.GEMINI_MODEL,
                "temperature": 0.0
            },
            "parameters": {
                "fixed_chunk_size": FIXED_CHUNK_SIZE,
                "fixed_chunk_overlap": FIXED_CHUNK_OVERLAP,
                "dense_top_k": 5,
                "rerank_top_k": 5,
                "rrf_k": 60.0,
                "max_context_tokens": settings.MAX_CONTEXT_TOKENS
            },
            "configurations": configurations
        }
        with open(exp_config_path, "w") as f:
            json.dump(exp_config, f, indent=2)

        print(f"Results successfully saved to:\n  - {raw_path}\n  - {summary_csv_path}\n  - {stats_path}\n  - {exp_config_path}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
