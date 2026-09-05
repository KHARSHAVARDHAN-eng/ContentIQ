# Controlled Experimental Evaluation Plan for Enterprise RAG Architecture

## 1. Research Objective

The primary objective of this experiment is to rigorously and empirically evaluate the performance of an advanced enterprise Retrieval-Augmented Generation (RAG) architecture against standard baseline configurations. Specifically, we investigate whether integrating **adaptive document chunking**, **hybrid retrieval (Dense + BM25)**, **cross-encoder reranking**, **context compression**, and **query-aware evidence selection** significantly improves retrieval accuracy, factual grounding, answer relevance, and resistance to hallucination without incurring prohibitive latency overhead.

---

## 2. Research Questions (RQs)

* **RQ1 (Adaptive Chunking Impact):** Does domain-adaptive document chunking improve retrieval recall and precision compared with fixed-size chunking across heterogeneous document types?
* **RQ2 (Hybrid Retrieval & Reranking Efficacy):** Does combining dense vector retrieval with lexical BM25 search and cross-encoder reranking improve top-K context relevance compared to single-modality vector retrieval?
* **RQ3 (Query-Aware Evidence Selection & Leakage Reduction):** Does sentence-level query-aware evidence selection eliminate cross-entity context leakage and raw section header contamination in generated answers?
* **RQ4 (End-to-End Grounded Answer Quality):** Does the complete RAG pipeline improve overall factual correctness, citation coverage, and grounding score compared with simpler RAG baselines?
* **RQ5 (Latency-Quality Trade-off):** What is the exact latency overhead introduced by each stage of the advanced pipeline, and is the quality improvement justified by the runtime cost?

---

## 3. Hypotheses

* **H1 (Chunking Quality):** Adaptive chunking aligned to document structure (e.g., technical docs vs. research papers) will increase Retrieval Recall@5 by at least 15% over fixed 500-token chunking.
* **H2 (Retrieval Relevance):** Hybrid RRF fusion + Cross-Encoder reranking will yield higher Context Precision@5 than dense vector search alone.
* **H3 (Leakage & Hallucination Suppression):** Query-aware evidence selection will reduce unrelated adjacent section leakage and hallucination rate to 0.0% on focused single-entity queries.
* **H4 (Out-of-Domain Safety):** Multi-stage verification will achieve 100% grounded refusal (zero ungrounded claims and zero citations) on out-of-domain/unanswerable queries.
* **H5 (Multi-hop Reasoning):** Multi-query transformation and GraphRAG traversal will preserve chronological multi-hop narrative structure across multi-chunk questions.

---

## 4. Controlled System Configurations

To isolate the individual contribution of each architectural component, all experiments evaluate the same dataset and questions under 5 strictly controlled pipeline configurations:

### Baseline 1: Basic RAG
* **Chunking:** Fixed-size chunking (`CHUNK_SIZE = 500`, `CHUNK_OVERLAP = 100`)
* **Retrieval:** Single-modality Dense Vector Retrieval (`all-MiniLM-L6-v2`, `Top-K = 5`)
* **Reranking:** Disabled
* **Compression / Evidence Selection:** Disabled (Full retrieved raw chunks passed directly to LLM)
* **Verification & Grounding:** Disabled

### Baseline 2: Adaptive Chunking RAG
* **Chunking:** Adaptive Chunking Strategy (`ADAPTIVE_CHUNKING_STRATEGY = "rules"`, domain-tailored sizes)
* **Retrieval:** Single-modality Dense Vector Retrieval (`Top-K = 5`)
* **Reranking:** Disabled
* **Compression / Evidence Selection:** Disabled
* **Verification & Grounding:** Disabled

### Baseline 3: Hybrid RAG
* **Chunking:** Adaptive Chunking Strategy
* **Retrieval:** Hybrid Retrieval (Dense Vector 0.5 + BM25 Sparse 0.5, RRF fusion $k=60.0$, `Top-K = 5`)
* **Reranking:** Disabled
* **Compression / Evidence Selection:** Disabled
* **Verification & Grounding:** Disabled

### Baseline 4: Hybrid + Reranker
* **Chunking:** Adaptive Chunking Strategy
* **Retrieval:** Hybrid Retrieval (`Top-K = 10`)
* **Reranking:** Cross-Encoder Reranking (`cross-encoder/ms-marco-MiniLM-L-2-v2`, Retained `Top-K = 5`, Score Threshold = 0.02)
* **Compression / Evidence Selection:** Disabled
* **Verification & Grounding:** Disabled

### Proposed Full System: ContentIQ / DocumentIQ RAG Pipeline
* **Chunking:** Adaptive Chunking Strategy
* **Query Processing:** Query Transformation (Multi-Query Generation, Ambiguity Scoring, Expansion)
* **Retrieval:** Hybrid Retrieval + Knowledge Graph RAG (`GRAPHRAG_ENABLED = True`, Traversal Depth = 2)
* **Reranking:** Cross-Encoder Reranking
* **Context Compression:** Sentence-level redundancy elimination and token compression (`MAX_CONTEXT_TOKENS = 2048`)
* **Evidence Selection:** Sentence-level query-aware evidence selection, focus subject entity qualification, and header noise removal
* **Synthesis & Verification:** Grounded LLM generation, Hallucination Detection, Claim Verification, Citation Mapping, and Self-Reflection Confidence Scoring

---

## 5. Multi-Domain Benchmark Dataset Specification

The evaluation benchmark incorporates 5 distinct document domains to evaluate generalizability across structured, semi-structured, and unstructured corpora.

### Domain 1: Epic Narrative & Classical Literature
* **Document:** `ramayana_full.txt` / `Ramayana_23_Page_Test_Document.pdf` (Multi-section epic narrative)
* **Characteristics:** High entity overlap, complex relationships, multi-character story arcs, section headers.

### Domain 2: Financial & Corporate Reports
* **Document:** `Financial_Report.pdf` (Corporate acquisition & earnings document)
* **Characteristics:** Quantitative metrics, company entities, financial figures, transaction dates.

### Domain 3: Legal & HR Offer Documents
* **Document:** `offerLetter.pdf` / `offerLetter.txt` (Structured employment agreement)
* **Characteristics:** Key-value pairs, position titles, contract durations, unpunctuated line breaks.

### Domain 4: Sci-Fi Fiction & Narrative
* **Document:** `DocumentIQ_Test_Story.txt` (Short story featuring fictional entities like Raman Iyer, Starlight-7)
* **Characteristics:** Fictional proper nouns, character motivations, location tracking.

### Domain 5: Scanned & OCR Technical Assets
* **Document:** `test_ocr_asset.png` / `test_scanned_pdf.pdf` (Scanned image & PDF technical documents)
* **Characteristics:** OCR noise, scanned text layout, bounding box text extraction.

---

## 6. Benchmark Question Categories & Ground-Truth Specification

| ID | Category | Target Question | Primary Domain | Expected Evidence / Ground Truth | Answerable? | Difficulty |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **Q1** | Single-hop Factual | *"Who kidnapped Sita and how did it happen?"* | Literature | Ravana disguised as a mendicant, lured Rama/Lakshmana via Maricha, abducted Sita from Panchavati in Pushpaka Vimana to Ashoka Vatika. | Yes | Easy |
| **Q2** | Single-hop Focused | *"What did Hanuman do in Lanka?"* | Literature | Leaped ocean, found Sita in Ashoka Vatika, gave signet ring, fought warriors, tail set ablaze, burned Lanka, reported to Rama. | Yes | Easy |
| **Q3** | Single-hop Focused | *"How did Sugriva help Rama find Sita?"* | Literature | Formed alliance with Rama, regained throne from Vali, mobilized monkey army, sent search parties in 4 cardinal directions. | Yes | Medium |
| **Q4** | Multi-step / Chronological | *"Explain the sequence of events from Sita's abduction to Hanuman finding her in Lanka."* | Literature | Abduction by Ravana $\rightarrow$ Jatayu fight & clue $\rightarrow$ Rama/Sugriva alliance $\rightarrow$ Monkey army search $\rightarrow$ Hanuman reaching Ashoka Vatika. | Yes | Hard |
| **Q5** | Single-hop Entity | *"Who was Jatayu and what happened to him?"* | Literature | Vulture king who fought Ravana to rescue Sita; wings clipped, mortally wounded, informed Rama of Ravana heading south. | Yes | Easy |
| **Q6** | Out-of-Domain Refusal | *"What is the capital of France?"* | None | Grounded Refusal ("I couldn't find information about this in the uploaded documents.") with zero citations. | No | Easy |
| **Q7** | Relationship / Multi-Entity | *"How did both Jatayu and Sugriva assist Rama after Sita was abducted?"* | Literature | Jatayu provided initial location clue; Sugriva provided army and search organization. | Yes | Medium |
| **Q8** | Factual Extraction | *"How much did Acme Corp pay to acquire Beta Ltd?"* | Financial | Acme Corp acquired Beta Ltd for $2 billion in 2025. | Yes | Easy |
| **Q9** | Precise Extraction | *"What is the position offered and duration of internship?"* | HR / Legal | Position: Data Analyst Intern; Duration: 4 months. | Yes | Easy |
| **Q10**| OCR Technical Extraction | *"What is the secret OCR code?"* | Scanned OCR | Secret OCR Code: Antigravity RAG works! | Yes | Medium |

---

## 7. Metrics & Scientifically Justified Evaluation Dimensions

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
* **Stage Latencies (ms):** Query transformation, retrieval, reranking, evidence selection, LLM generation.

---

## 8. Experimental Protocol & Reproducibility Settings

To guarantee strict scientific reproducibility, all experimental runs use exact parameter values configured in the codebase:

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
| **Baseline 1: Basic RAG** | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED |
| **Baseline 2: Adaptive Chunking** | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED |
| **Baseline 3: Hybrid RAG** | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED |
| **Baseline 4: Hybrid + Reranker** | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED |
| **Proposed Full System** | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED |

### Table 2: Evidence Selection & Leakage Suppression Performance

| Pipeline Configuration | Q2 Raw Header Leakage | Q3 Unrelated Entity Leakage | Q6 Out-of-Domain Refusal | Citation Coverage |
| :--- | :---: | :---: | :---: | :---: |
| **Baseline 1: Basic RAG** | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED |
| **Baseline 4: Hybrid + Reranker** | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED |
| **Proposed Full System** | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED |

### Table 3: System Latency Breakdown (ms)

| Pipeline Configuration | Retrieval Latency | Rerank Latency | Evidence Selection Latency | Generation Latency | Total Latency |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: Basic RAG** | NOT YET MEASURED | N/A | N/A | NOT YET MEASURED | NOT YET MEASURED |
| **Baseline 4: Hybrid + Reranker** | NOT YET MEASURED | NOT YET MEASURED | N/A | NOT YET MEASURED | NOT YET MEASURED |
| **Proposed Full System** | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED |

---

## 10. Threats to Validity & Limitations

* **API LLM Nondeterminism:** While `temperature=0.0` is configured, remote LLM API updates may introduce slight lexical variations across benchmark runs.
* **Synthetic / Mock Fallback:** When `GEMINI_API_KEY` is omitted, the pipeline falls back to rule-based deterministic mock generation. Comparative benchmarks must run with live Gemini API keys to measure production LLM quality.
* **Document Corpus Size:** Current benchmark covers 5 document domains; scaling to thousands of documents may require indexing optimizations.

---
*Document Version: 1.0.0 | Status: Experiment Specification Frozen*
