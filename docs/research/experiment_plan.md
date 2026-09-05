# Controlled Experimental Evaluation Plan for Enterprise RAG Architecture

## 1. Research Objective

The primary objective of this experiment is to rigorously and empirically evaluate the performance of an advanced enterprise Retrieval-Augmented Generation (RAG) architecture against standard baseline configurations. Specifically, we investigate whether integrating **adaptive document chunking**, **hybrid retrieval (Dense + BM25)**, **cross-encoder reranking**, **context compression**, **query-aware evidence selection**, and **GraphRAG entity traversal** significantly improves retrieval accuracy, factual grounding, answer relevance, and resistance to hallucination without incurring prohibitive latency overhead.

---

## 2. Research Questions (RQs)

* **RQ1 (Adaptive Chunking Impact):** Does domain-adaptive document chunking improve retrieval recall and precision compared with fixed-size chunking across heterogeneous document types?
* **RQ2 (Hybrid Retrieval & Reranking Efficacy):** Does combining dense vector retrieval with lexical BM25 search and cross-encoder reranking improve top-K context relevance compared to single-modality vector retrieval?
* **RQ3 (Query-Aware Evidence Selection & Leakage Reduction):** Does sentence-level query-aware evidence selection reduce cross-entity context leakage and raw section header contamination compared with passing raw retrieved context?
* **RQ4 (End-to-End Grounded Answer Quality):** Does the complete RAG pipeline improve overall factual correctness, citation coverage, and grounding score compared with simpler RAG baselines?
* **RQ5 (GraphRAG Contribution & Latency Trade-off):** What is the incremental performance contribution of GraphRAG entity graph traversal (B5a vs. B5b), and what is the exact latency overhead introduced by each stage of the pipeline?

---

## 3. Hypotheses

* **H1 (Chunking Quality - Directional):** Domain-adaptive document chunking yields higher retrieval recall and precision than fixed-size chunking across heterogeneous document formats.
* **H2 (Retrieval Relevance):** Hybrid RRF fusion + Cross-Encoder reranking will yield higher Context Precision@5 than dense vector search alone.
* **H3 (Leakage & Hallucination Suppression - Directional):** Query-aware evidence selection reduces cross-entity context leakage and hallucination compared with passing raw retrieved context.
* **H4 (Out-of-Domain Safety):** Multi-stage verification will achieve grounded refusal (zero ungrounded claims and zero citations) on out-of-domain/unanswerable queries.
* **H5 (Multi-hop Reasoning):** Multi-query transformation and GraphRAG traversal will preserve chronological multi-hop narrative structure across multi-chunk questions.

*Note: Hypotheses remain open to empirical testing across benchmark runs; none are claimed as pre-proven.*

---

## 4. Controlled System Configurations & Isolation Mechanism

To guarantee scientific ablation isolation, all experiments evaluate the same benchmark dataset (`docs/research/benchmark_dataset.json`) across **6 strictly isolated baseline configurations**.

### Qdrant Vector Store Collection Isolation
To prevent vector cross-contamination between fixed-chunk (B1) and adaptive-chunk (B2–B5) corpora, Qdrant utilizes dedicated collection namespaces:
* `research_fixed`: Isolated Qdrant collection containing fixed-size chunks (`CHUNK_SIZE = 500`, `CHUNK_OVERLAP = 100`).
* `research_adaptive`: Isolated Qdrant collection containing rules-based adaptive document chunks (`document_chunks`).

### Evidence Selection Toggle
The feature flag `EVIDENCE_SELECTION_ENABLED` in `app/core/config.py` explicitly toggles query-aware evidence selection:
* `EVIDENCE_SELECTION_ENABLED = False`: Evidence selection bypass mode (used for Baselines B1–B4).
* `EVIDENCE_SELECTION_ENABLED = True`: Sentence-level query-aware evidence selection active (used for Baselines B5a & B5b).

### Baseline Component Matrix

| Configuration | Qdrant Namespace | Chunking Strategy | Retrieval Mode | Reranker | Context Compression | Evidence Selection (`EVIDENCE_SELECTION_ENABLED`) | GraphRAG (`GRAPHRAG_ENABLED`) | Verification |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **B1: Basic RAG** | `research_fixed` | Fixed (500 tokens) | Dense Vector | OFF | OFF | OFF | OFF | OFF |
| **B2: Adaptive Chunking** | `research_adaptive` | Adaptive Rules | Dense Vector | OFF | OFF | OFF | OFF | OFF |
| **B3: Adaptive + Hybrid** | `research_adaptive` | Adaptive Rules | Dense + BM25 RRF | OFF | OFF | OFF | OFF | OFF |
| **B4: Adaptive + Hybrid + Reranker** | `research_adaptive` | Adaptive Rules | Dense + BM25 RRF | ON | OFF | OFF | OFF | OFF |
| **B5a: Full Pipeline WITHOUT GraphRAG** | `research_adaptive` | Adaptive Rules | Dense + BM25 RRF | ON | ON | ON | OFF | ON |
| **B5b: Full Pipeline WITH GraphRAG** | `research_adaptive` | Adaptive Rules | Dense + BM25 RRF + Graph | ON | ON | ON | ON | ON |

---

## 5. Detailed Baseline Specifications

### Baseline 1: Basic RAG
* **Collection Namespace:** `research_fixed`
* **Chunking:** Fixed-size chunking (`CHUNK_SIZE = 500`, `CHUNK_OVERLAP = 100`)
* **Retrieval:** Single-modality Dense Vector Retrieval (`all-MiniLM-L6-v2`, `Top-K = 5`)
* **Reranking:** Disabled
* **Compression / Evidence Selection:** Disabled (`EVIDENCE_SELECTION_ENABLED = False`)
* **GraphRAG:** Disabled (`GRAPHRAG_ENABLED = False`)
* **Verification & Grounding:** Disabled

### Baseline 2: Adaptive Chunking RAG
* **Collection Namespace:** `research_adaptive`
* **Chunking:** Adaptive Chunking Strategy (`ADAPTIVE_CHUNKING_STRATEGY = "rules"`, domain-tailored sizes)
* **Retrieval:** Single-modality Dense Vector Retrieval (`Top-K = 5`)
* **Reranking:** Disabled
* **Compression / Evidence Selection:** Disabled (`EVIDENCE_SELECTION_ENABLED = False`)
* **GraphRAG:** Disabled (`GRAPHRAG_ENABLED = False`)
* **Verification & Grounding:** Disabled

### Baseline 3: Adaptive + Hybrid RAG
* **Collection Namespace:** `research_adaptive`
* **Chunking:** Adaptive Chunking Strategy
* **Retrieval:** Hybrid Retrieval (Dense Vector 0.5 + BM25 Sparse 0.5, RRF fusion $k=60.0$, `Top-K = 5`)
* **Reranking:** Disabled
* **Compression / Evidence Selection:** Disabled (`EVIDENCE_SELECTION_ENABLED = False`)
* **GraphRAG:** Disabled (`GRAPHRAG_ENABLED = False`)
* **Verification & Grounding:** Disabled

### Baseline 4: Adaptive + Hybrid + Reranker
* **Collection Namespace:** `research_adaptive`
* **Chunking:** Adaptive Chunking Strategy
* **Retrieval:** Hybrid Retrieval (`Top-K = 10`)
* **Reranking:** Cross-Encoder Reranking (`cross-encoder/ms-marco-MiniLM-L-2-v2`, Retained `Top-K = 5`, Score Threshold = 0.02)
* **Compression / Evidence Selection:** Disabled (`EVIDENCE_SELECTION_ENABLED = False`)
* **GraphRAG:** Disabled (`GRAPHRAG_ENABLED = False`)
* **Verification & Grounding:** Disabled

### Baseline 5a: Full Pipeline WITHOUT GraphRAG
* **Collection Namespace:** `research_adaptive`
* **Chunking:** Adaptive Chunking Strategy
* **Query Processing:** Query Transformation (Multi-Query Generation, Ambiguity Scoring, Expansion)
* **Retrieval:** Hybrid Retrieval (Dense + BM25 RRF)
* **Reranking:** Cross-Encoder Reranking
* **Context Compression:** Sentence-level redundancy elimination and token compression (`MAX_CONTEXT_TOKENS = 2048`)
* **Evidence Selection:** Sentence-level query-aware evidence selection (`EVIDENCE_SELECTION_ENABLED = True`)
* **GraphRAG:** Disabled (`GRAPHRAG_ENABLED = False`)
* **Synthesis & Verification:** Grounded LLM generation, Hallucination Detection, Claim Verification, Citation Mapping, and Self-Reflection Confidence Scoring

### Baseline 5b: Full Pipeline WITH GraphRAG
* **Collection Namespace:** `research_adaptive`
* **Chunking:** Adaptive Chunking Strategy
* **Query Processing:** Query Transformation
* **Retrieval:** Hybrid Retrieval + Knowledge Graph RAG (`GRAPHRAG_ENABLED = True`, Traversal Depth = 2, Graph Weight = 0.30)
* **Reranking:** Cross-Encoder Reranking
* **Context Compression:** Sentence-level redundancy elimination and token compression
* **Evidence Selection:** Sentence-level query-aware evidence selection (`EVIDENCE_SELECTION_ENABLED = True`)
* **GraphRAG:** Enabled (`GRAPHRAG_ENABLED = True`)
* **Synthesis & Verification:** Full verification pipeline active

---

## 6. Multi-Domain Benchmark Dataset Specification

The evaluation benchmark incorporates 35 questions (`docs/research/benchmark_dataset.json`) across 5 distinct document domains (~7 questions per domain) to evaluate generalizability across structured, semi-structured, and unstructured corpora.

### Domain Breakdown

1. **Literature (7 Questions):** `ramayana_full.txt` (Multi-section epic narrative; entity overlap, complex relationships, multi-character story arcs).
2. **Financial / Corporate (7 Questions):** `Financial_Report.pdf` (Corporate acquisition & earnings document; quantitative metrics, company entities, financial figures).
3. **Legal / HR (7 Questions):** `offerLetter.pdf` (Structured employment agreement; position titles, contract durations, unpunctuated line breaks).
4. **Sci-Fi Fiction (7 Questions):** `DocumentIQ_Test_Story.txt` (Short narrative; proper nouns like Raman Iyer and Starlight-7, character motivations).
5. **Scanned / OCR (7 Questions):** `test_ocr_asset.png` / `test_scanned_pdf.pdf` (Scanned image & PDF technical documents; OCR noise, text layout).

---

## 7. Metrics & Evaluation Dimensions

### A. Retrieval Metrics
* **Context Precision@K:** Ratio of relevant chunks positioned at top ranks.
* **Context Recall:** Ratio of expected reference documents/chunks successfully retrieved.
* **Retrieval Precision & Recall:** Precision and recall of individual retrieved text snippets against expected ground-truth targets.

### B. Generation & Grounding Metrics
* **Faithfulness (Grounding Score):** Percentage of factual claims in the generated response that are directly supported by retrieved context (0.0 to 1.0).
* **Answer Relevancy:** Lexical and semantic alignment between generated answer and original query.
* **Hallucination Rate:** Fraction of ungrounded or contradicted claims detected in final output (0.0 = clean).
* **Verification Success Rate:** Fraction of atomic claims successfully verified against retrieved evidence.

### C. Citation Metrics
* **Citation Coverage:** Ratio of cited statements to total factual assertions in the answer.
* **Citation Precision:** Accuracy of chunk citations attached to answer statements.

### D. System Performance Metrics
* **Total End-to-End Latency (ms):** Wall-clock time from incoming query request to final HTTP response.
* **Stage Latencies (ms):** Query transformation, retrieval, reranking, evidence selection, GraphRAG traversal, LLM generation.

---

## 8. Experimental Protocol & Reproducibility Settings

```yaml
System Environment:
  OS: macOS (Darwin arm64)
  Python Version: 3.10.0
  Framework: FastAPI / Pytest / Uvicorn

Model Configurations:
  Embedding Model: "sentence-transformers/all-MiniLM-L6-v2" (384-dim)
  LLM Generator: "gemini-1.5-flash" (Temperature = 0.0)
  Reranker Model: "cross-encoder/ms-marco-MiniLM-L-2-v2"

Retrieval & Fusion Settings:
  Vector Store: Qdrant Local Client (Path: ./qdrant_data)
  Hybrid Retrieval Weights: Dense = 0.5, BM25 = 0.5
  RRF Fusion Constant (k): 60.0
  Rerank Top-K: 5 (Score Threshold = 0.02)
  GraphRAG Traversal Depth: 2 (Hybrid Weight = 0.30)

Context & Evidence Selection:
  Max Context Tokens: 2048
  Max Context Chunks: 10
  Sentence Similarity Threshold: 0.85
  Header Stripping Rule: Topic-word overlap disambiguation
```

---

## 9. Planned Result Tables

*Note: All values remain unpopulated until formal experimental execution.*

### Table 1: End-to-End Retrieval & Answer Quality Comparison

| Pipeline Configuration | Context Precision@5 | Context Recall | Faithfulness | Answer Relevancy | Hallucination Rate | Overall Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **B1: Basic RAG** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |
| **B2: Adaptive Chunking** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |
| **B3: Adaptive + Hybrid** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |
| **B4: Adaptive + Hybrid + Reranker** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |
| **B5a: Full System (No GraphRAG)** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |
| **B5b: Full System (With GraphRAG)** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |

### Table 2: Evidence Selection & Leakage Suppression Performance

| Pipeline Configuration | Raw Header Leakage | Unrelated Entity Leakage | Out-of-Domain Refusal | Citation Coverage |
| :--- | :---: | :---: | :---: | :---: |
| **B1: Basic RAG** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |
| **B4: Adaptive + Hybrid + Reranker** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |
| **B5a: Full System (No GraphRAG)** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |
| **B5b: Full System (With GraphRAG)** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |

### Table 3: GraphRAG Ablation & System Latency Breakdown (ms)

| Pipeline Configuration | Retrieval Latency | Rerank Latency | GraphRAG Latency | Evidence Selection Latency | Generation Latency | Total Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **B1: Basic RAG** | UNEXECUTED | N/A | N/A | N/A | UNEXECUTED | UNEXECUTED |
| **B4: Hybrid + Reranker** | UNEXECUTED | UNEXECUTED | N/A | N/A | UNEXECUTED | UNEXECUTED |
| **B5a: Full System (No GraphRAG)** | UNEXECUTED | UNEXECUTED | N/A | UNEXECUTED | UNEXECUTED | UNEXECUTED |
| **B5b: Full System (With GraphRAG)** | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED | UNEXECUTED |

---

## 10. Threats to Validity & Limitations

* **API LLM Nondeterminism:** While `temperature=0.0` is configured, remote LLM API updates may introduce slight lexical variations across benchmark runs.
* **Synthetic / Mock Fallback:** When `GEMINI_API_KEY` is omitted, the pipeline falls back to rule-based deterministic mock generation. Comparative benchmarks must run with live Gemini API keys to measure production LLM quality.
* **Document Corpus Size:** Current benchmark covers 5 document domains; scaling to thousands of documents may require indexing optimizations.

---
*Document Version: 2.0.0 | Status: Experiment Specification & Isolation Architecture Frozen*
