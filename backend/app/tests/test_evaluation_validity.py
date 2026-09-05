import pytest
import numpy as np
from unittest.mock import MagicMock
from app.core.config import settings
from app.services.vector_store import vector_store
from app.services.evaluation_engine import evaluation_engine
from app.services.llm_service import llm_service
from app.services.graph_store import graph_store
from app.services.graph_builder import graph_builder
from app.models.document_chunk import DocumentChunk
from app.core.database import SessionLocal
from app.scripts.run_experiments import seed_environment, run_single_pipeline_query, CONFIGURATIONS, COLLECTION_ADAPTIVE

def test_document_name_survives_qdrant_indexing_retrieval():
    """Test 1: Verify document_name survives Qdrant indexing and retrieval."""
    test_collection = "test_doc_name_survival"
    vector_store.create_collection(test_collection, vector_size=384)
    
    vec = [0.1] * 384
    vector_store.upsert_chunk(
        chunk_id=99991,
        document_id=55,
        page_number=1,
        chunk_text="Test chunk text for document name survival test.",
        vector=vec,
        collection_name=test_collection,
        document_name="financial_report_2025.pdf"
    )
    
    hits = vector_store.search_similar_chunks(
        query_vector=vec,
        limit=1,
        collection_name=test_collection
    )
    
    assert len(hits) == 1
    assert hits[0]["document_name"] == "financial_report_2025.pdf"
    assert hits[0]["chunk_id"] == 99991
    assert hits[0]["document_id"] == 55

def test_context_precision_uses_ground_truth_evidence_not_citations():
    """Test 2: Context Precision uses ground-truth reference evidence, ignoring citations."""
    context_chunks = [
        {"chunk_id": 1, "chunk_text": "Maricha disguised himself as a golden deer to lure Rama away from Panchavati."},
        {"chunk_id": 2, "chunk_text": "Unrelated text about baking sourdough bread in an oven."}
    ]
    # No citations provided
    citations = []
    ref_evidence = ["Maricha disguised himself as a golden deer to lure Rama"]

    eval_res = evaluation_engine.evaluate_response(
        question="How did Maricha lure Rama?",
        answer="Maricha disguised himself as a golden deer.",
        citations=citations,
        context_chunks=context_chunks,
        pipeline_outputs={},
        reference_evidence=ref_evidence
    )

    cp = eval_res.metrics["context_precision"].score
    # Chunk 1 at rank 1 contains reference evidence, Precision@1 = 1/1 = 1.0
    assert cp == 1.0

def test_context_recall_uses_reference_documents_and_evidence():
    """Test 3: Context Recall accurately uses reference evidence and reference documents."""
    context_chunks = [
        {"document_name": "ramayana_full.txt", "chunk_text": "Jatayu fought Ravana in an attempt to rescue Sita."}
    ]
    ref_evidence = ["Jatayu fought Ravana", "Hanuman leaped across the ocean to Lanka"]
    ref_docs = ["ramayana_full.txt"]

    eval_res = evaluation_engine.evaluate_response(
        question="Who tried to rescue Sita?",
        answer="Jatayu tried to rescue Sita.",
        citations=[],
        context_chunks=context_chunks,
        pipeline_outputs={},
        reference_documents=ref_docs,
        reference_evidence=ref_evidence
    )

    cr = eval_res.metrics["context_recall"].score
    # Only 1 out of 2 reference evidence items retrieved
    assert cr == 0.5

def test_faithfulness_bypasses_hallucination_detector_output():
    """Test 4: Faithfulness evaluation does not read pipeline_outputs['hallucination_detection']."""
    fake_h_det = MagicMock()
    fake_h_det.hallucination_status = "FAILED"

    context_chunks = [
        {"chunk_text": "Sita requested Rama to capture the golden deer."}
    ]
    ref_evidence = ["Sita requested Rama to capture the golden deer."]

    eval_res = evaluation_engine.evaluate_response(
        question="What did Sita request?",
        answer="Sita requested Rama to capture the golden deer.",
        citations=[],
        context_chunks=context_chunks,
        pipeline_outputs={"hallucination_detection": fake_h_det},
        reference_evidence=ref_evidence
    )

    faith = eval_res.metrics["faithfulness"].score
    # Even though fake_h_det was FAILED, independent evaluation verifies grounding against evidence
    assert faith == 1.0

def test_hallucination_rate_independently_calculated():
    """Test 5: Hallucination Rate is independently calculated as 1 - Faithfulness."""
    context_chunks = [
        {"chunk_text": "Acme Corp acquired Beta Ltd for $2 billion in Q3 2025."}
    ]
    ref_evidence = ["Acme Corp acquired Beta Ltd for $2 billion."]

    # Model generates answer with an ungrounded claim
    answer = "Acme Corp acquired Beta Ltd for $2 billion. The company also launched a rocket to Alpha Centauri."

    eval_res = evaluation_engine.evaluate_response(
        question="What did Acme Corp acquire?",
        answer=answer,
        citations=[],
        context_chunks=context_chunks,
        pipeline_outputs={},
        reference_evidence=ref_evidence
    )

    faith = eval_res.metrics["faithfulness"].score
    hr = eval_res.metrics["hallucination_rate"].score

    assert faith == 0.5
    assert hr == 0.5
    assert round(faith + hr, 2) == 1.0

def test_semantic_answer_relevancy_works():
    """Test 6: Semantic Answer Relevancy uses MiniLM embedding similarity and handles refusals."""
    ans = "Acme Corp acquired Beta Ltd for $2 billion in Q3 2025."
    gt = "Acme Corp completed the acquisition of Beta Ltd for $2B."

    eval_res = evaluation_engine.evaluate_response(
        question="How much did Acme Corp pay for Beta Ltd?",
        answer=ans,
        citations=[],
        context_chunks=[],
        pipeline_outputs={},
        ground_truth=gt
    )

    ar = eval_res.metrics["answer_relevancy"].score
    assert ar > 0.70

    # Test refusal for unanswerable question
    refusal_ans = "I couldn't find information about this in the uploaded documents."
    refusal_gt = "I couldn't find information about this in the uploaded documents."

    eval_res_refusal = evaluation_engine.evaluate_response(
        question="What is the CEO's favorite color?",
        answer=refusal_ans,
        citations=[],
        context_chunks=[],
        pipeline_outputs={},
        ground_truth=refusal_gt,
        reference_evidence=[]
    )

    ar_refusal = eval_res_refusal.metrics["answer_relevancy"].score
    assert ar_refusal == 1.0

def test_gemini_mode_fails_if_api_key_missing(monkeypatch):
    """Test 7: Gemini mode fails loudly with ValueError if GEMINI_API_KEY is missing."""
    monkeypatch.setattr(settings, "RESEARCH_GENERATOR_MODE", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    with pytest.raises(ValueError, match="RESEARCH_GENERATOR_MODE is set to 'gemini' but GEMINI_API_KEY is missing"):
        llm_service.generate_answer("Test question", [{"chunk_text": "Sample context"}])

def test_graphrag_benchmark_seeding_produces_graph_context():
    """Test 8: GraphRAG benchmark seeding produces graph nodes and relationships."""
    db = SessionLocal()
    try:
        settings.GRAPHRAG_ENABLED = True
        user = seed_environment(db)
        assert len(graph_store.nodes) > 0
        assert len(graph_store.edges) > 0
    finally:
        db.close()

def test_b5a_b5b_differ_in_graphrag_context():
    """Test 9: B5a and B5b differ strictly in GraphRAG context enabling."""
    db = SessionLocal()
    try:
        user = seed_environment(db)
        question = "How did Sugriva help Rama find Sita?"

        b5a_cfg = dict(CONFIGURATIONS["B5a"])
        b5b_cfg = dict(CONFIGURATIONS["B5b"])

        out_b5a = run_single_pipeline_query(db, user, question, b5a_cfg)
        out_b5b = run_single_pipeline_query(db, user, question, b5b_cfg)

        # Assert feature flags differed as expected
        assert b5a_cfg["use_graphrag"] is False
        assert b5b_cfg["use_graphrag"] is True
        
        # Assert B5b received non-empty context and executed successfully
        assert len(out_b5b["candidate_chunks"]) > 0
        assert len(out_b5a["candidate_chunks"]) > 0
    finally:
        db.close()
