import logging
import math
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.document_chunk import DocumentChunk

logger = logging.getLogger("app.services.bm25_retriever")

class BM25Okapi:
    def __init__(self, corpus: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.corpus_size = len(corpus)
        self.avg_doc_len = 0.0
        self.doc_lens = []
        self.doc_term_freqs = []  # List[Dict[str, int]]
        self.idf = {}  # Dict[str, float]
        
        self._initialize()

    STOP_WORDS = {
        'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t', 'as', 'at',
        'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can\'t', 'cannot', 'could',
        'did', 'didn\'t', 'do', 'does', 'doesn\'t', 'doing', 'don\'t', 'down', 'during', 'each', 'few', 'for', 'from',
        'further', 'had', 'hadn\'t', 'has', 'hasn\'t', 'have', 'haven\'t', 'having', 'he', 'he\'d', 'he\'ll', 'he\'s',
        'her', 'here', 'here\'s', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'how\'s', 'i', 'i\'d', 'i\'ll',
        'i\'m', 'i\'ve', 'if', 'in', 'into', 'is', 'isn\'t', 'it', 'it\'s', 'its', 'itself', 'let\'s', 'me', 'more',
        'most', 'mustn\'t', 'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other',
        'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'shan\'t', 'she', 'she\'d', 'she\'ll',
        'she\'s', 'should', 'shouldn\'t', 'so', 'some', 'such', 'than', 'that', 'that\'s', 'the', 'their', 'theirs',
        'them', 'themselves', 'then', 'there', 'there\'s', 'these', 'they', 'they\'d', 'they\'ll', 'they\'re', 'they\'ve',
        'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasn\'t', 'we', 'we\'d',
        'we\'ll', 'we\'re', 'we\'ve', 'were', 'weren\'t', 'what', 'what\'s', 'when', 'when\'s', 'where', 'where\'s',
        'which', 'while', 'who', 'who\'s', 'whom', 'why', 'why\'s', 'with', 'won\'t', 'would', 'wouldn\'t', 'you',
        'you\'d', 'you\'ll', 'you\'re', 'you\'ve', 'your', 'yours', 'yourself', 'yourselves'
    }

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r'\b\w+\b', text.lower())
        filtered = [t for t in tokens if t not in self.STOP_WORDS]
        return filtered if filtered else tokens

    def _initialize(self):
        total_len = 0
        nd = {}  # Term -> count of docs containing term
        
        for doc in self.corpus:
            tokens = self._tokenize(doc.get("chunk_text", ""))
            doc_len = len(tokens)
            self.doc_lens.append(doc_len)
            total_len += doc_len
            
            freqs = {}
            for token in tokens:
                freqs[token] = freqs.get(token, 0) + 1
            self.doc_term_freqs.append(freqs)
            
            for token in freqs.keys():
                nd[token] = nd.get(token, 0) + 1
                
        self.avg_doc_len = (total_len / self.corpus_size) if self.corpus_size > 0 else 0.0
        
        for term, freq in nd.items():
            self.idf[term] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

    def score_query(self, query: str) -> List[float]:
        query_tokens = self._tokenize(query)
        scores = []
        for i in range(self.corpus_size):
            score = 0.0
            doc_len = self.doc_lens[i]
            freqs = self.doc_term_freqs[i]
            for token in query_tokens:
                if token in freqs:
                    tf = freqs[token]
                    idf = self.idf.get(token, 0.0)
                    score += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * (1.0 - self.b + self.b * doc_len / self.avg_doc_len))
            scores.append(score)
        return scores

class BM25Retriever:
    def search(self, db: Session, query: str, user_doc_ids: List[int], limit: int) -> List[Dict[str, Any]]:
        if not user_doc_ids:
            logger.info("BM25: Empty user_doc_ids list. Returning empty search hits.")
            return []
            
        chunks_db = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(user_doc_ids)).all()
        if not chunks_db:
            logger.info(f"BM25: No chunk records found in DB for document IDs {user_doc_ids}.")
            return []
            
        corpus = []
        for chunk in chunks_db:
            corpus.append({
                "chunk_id": str(chunk.id),
                "document_id": chunk.document_id,
                "page_number": chunk.page_number,
                "chunk_text": chunk.chunk_text,
                "chunk_index": chunk.chunk_index
            })
            
        ranker = BM25Okapi(corpus)
        scores = ranker.score_query(query)
        
        scored_hits = []
        for idx, doc in enumerate(corpus):
            score = scores[idx]
            if score > 0.0:
                hit = dict(doc)
                hit["score"] = round(score, 4)
                scored_hits.append(hit)
                
        # Sort descending by BM25 score
        scored_hits.sort(key=lambda x: x["score"], reverse=True)
        hits = scored_hits[:limit]
        
        logger.info(f"BM25: Query: '{query}' | Total matching chunks: {len(scored_hits)} | Returning top {len(hits)}")
        return hits

bm25_retriever = BM25Retriever()
