"""
Retrieval: BM25, Dense, Hybrid RRF
Implements three configs per spec
"""
from typing import List, Dict, Any, Optional
import math
from collections import Counter, defaultdict
import time
from datetime import datetime
from ..schemas.evidence import Evidence, EvidenceBundle
from ..schemas.common import GovernanceMetadata
from ..providers.external_provider import MockExternalProvider

class BM25Retriever:
    def __init__(self, documents: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.doc_len = []
        self.avgdl = 0
        self.doc_freqs = []
        self.idf = {}
        self._initialize()

    def _initialize(self):
        # Simple BM25 implementation
        doc_tokens = []
        for doc in self.documents:
            tokens = (doc["text"] + " " + doc["company"]).lower().split()
            doc_tokens.append(tokens)
            self.doc_len.append(len(tokens))

        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0

        # doc freqs
        df = defaultdict(int)
        for tokens in doc_tokens:
            unique = set(tokens)
            for tok in unique:
                df[tok] += 1

        N = len(self.documents)
        for token, freq in df.items():
            self.idf[token] = math.log((N - freq + 0.5) / (freq + 0.5) + 1)

        # term freqs per doc
        for tokens in doc_tokens:
            self.doc_freqs.append(Counter(tokens))

    def score(self, query: str, doc_idx: int) -> float:
        query_tokens = query.lower().split()
        score = 0.0
        doc_freq = self.doc_freqs[doc_idx]
        doc_len = self.doc_len[doc_idx]
        for q_tok in query_tokens:
            if q_tok not in doc_freq:
                continue
            tf = doc_freq[q_tok]
            idf = self.idf.get(q_tok, 0)
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            score += idf * numerator / denominator
        return score

    def search(self, query: str, top_k: int = 5) -> List[tuple[float, Dict]]:
        scores = []
        for idx, doc in enumerate(self.documents):
            s = self.score(query, idx)
            scores.append((s, doc))
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[:top_k]

class DenseRetriever:
    def __init__(self, documents: List[Dict[str, Any]], embedding_model: str = "all-MiniLM-L6-v2"):
        self.documents = documents
        self.embedding_model_name = embedding_model
        self.embeddings = None
        self.model = None
        self._initialize()

    def _initialize(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.embedding_model_name)
            texts = [d["text"] + " " + d["company"] for d in self.documents]
            self.embeddings = self.model.encode(texts, normalize_embeddings=True)
        except Exception as e:
            # Fallback to simple TF-IDF like scoring if sentence-transformers not available
            print(f"Dense retriever fallback due to: {e}")
            self.model = None
            self.embeddings = None

    def search(self, query: str, top_k: int = 5) -> List[tuple[float, Dict]]:
        if self.model is None or self.embeddings is None:
            # Fallback to simple overlap scoring
            q_words = set(query.lower().split())
            scored = []
            for doc in self.documents:
                d_words = set((doc["text"] + " " + doc["company"]).lower().split())
                overlap = len(q_words.intersection(d_words))
                score = overlap / max(1, len(q_words))
                scored.append((score, doc))
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[:top_k]

        from sentence_transformers import util
        import torch
        query_emb = self.model.encode(query, normalize_embeddings=True)
        # Cosine similarity
        scores = util.cos_sim(query_emb, self.embeddings)[0]
        # Convert to list
        scored = [(float(scores[i]), self.documents[i]) for i in range(len(self.documents))]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

class HybridRetriever:
    def __init__(self, external_provider: MockExternalProvider = None, bm25_k1: float = 1.5, bm25_b: float = 0.75, rrf_k: int = 60):
        self.provider = external_provider or MockExternalProvider()
        self.documents = self.provider.documents
        self.bm25 = BM25Retriever(self.documents, k1=bm25_k1, b=bm25_b)
        self.dense = DenseRetriever(self.documents)
        self.rrf_k = rrf_k

    def _to_evidence(self, doc: Dict, score: float, retriever: str) -> Evidence:
        gov = GovernanceMetadata(
            source=doc["source"],
            authoritative=doc["source"] in ["SEC", "Trading System"],
            freshness_timestamp=datetime(2026, 9, 10),
            permitted=doc["metadata"].get("injection") is not True,
            provenance=f"{doc['source']} {doc['document_id']}",
            retrieved_at=datetime.utcnow(),
            document_id=doc["document_id"]
        )
        return Evidence(
            document_id=doc["document_id"],
            source=doc["source"],
            section=doc["section"],
            text=doc["text"],
            score=score,
            retriever=retriever,
            metadata=doc["metadata"],
            governance=gov
        )

    def search_bm25(self, query: str, top_k: int = 5) -> EvidenceBundle:
        start = time.time()
        results = self.bm25.search(query, top_k)
        # Normalize BM25 scores to 0-1 for consistency (divide by max)
        if results:
            max_score = max(score for score, _ in results) or 1.0
            normalized = [(score / max_score if max_score > 0 else 0.0, doc) for score, doc in results]
        else:
            normalized = results
        evidence = [self._to_evidence(doc, score, "bm25") for score, doc in normalized]
        return EvidenceBundle(query=query, results=evidence, retriever_type="bm25", latency_ms=int((time.time()-start)*1000), total_retrieved=len(evidence))

    def search_dense(self, query: str, top_k: int = 5) -> EvidenceBundle:
        start = time.time()
        results = self.dense.search(query, top_k)
        evidence = [self._to_evidence(doc, score, "dense") for score, doc in results]
        return EvidenceBundle(query=query, results=evidence, retriever_type="dense", latency_ms=int((time.time()-start)*1000), total_retrieved=len(evidence))

    def search_hybrid(self, query: str, top_k: int = 5, bm25_weight: float = 0.5, dense_weight: float = 0.5) -> EvidenceBundle:
        start = time.time()
        bm25_results = self.bm25.search(query, top_k*2)
        dense_results = self.dense.search(query, top_k*2)

        # RRF fusion
        # Map doc_id to ranks
        rrf_scores = defaultdict(float)
        doc_map = {}

        for rank, (score, doc) in enumerate(bm25_results):
            doc_id = doc["document_id"]
            rrf_scores[doc_id] += bm25_weight * (1 / (self.rrf_k + rank + 1))
            doc_map[doc_id] = doc

        for rank, (score, doc) in enumerate(dense_results):
            doc_id = doc["document_id"]
            rrf_scores[doc_id] += dense_weight * (1 / (self.rrf_k + rank + 1))
            doc_map[doc_id] = doc

        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        evidence = [self._to_evidence(doc_map[doc_id], score, "hybrid") for doc_id, score in sorted_docs]

        return EvidenceBundle(query=query, results=evidence, retriever_type="hybrid", latency_ms=int((time.time()-start)*1000), total_retrieved=len(evidence))

    def search(self, query: str, top_k: int = 5, retriever_type: str = "hybrid") -> EvidenceBundle:
        if retriever_type == "bm25":
            return self.search_bm25(query, top_k)
        elif retriever_type == "dense":
            return self.search_dense(query, top_k)
        else:
            return self.search_hybrid(query, top_k)
