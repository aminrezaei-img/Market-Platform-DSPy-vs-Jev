"""Unit tests for retrieval"""
from src.financial_agent.retrieval.hybrid_retriever import HybridRetriever, BM25Retriever, DenseRetriever
from src.financial_agent.providers.external_provider import MockExternalProvider

def test_bm25_retriever():
    provider = MockExternalProvider()
    bm25 = BM25Retriever(provider.documents)
    results = bm25.search("Nordic Industrial EBITDA", top_k=3)
    assert len(results) == 3
    # Top result should be about Nordic Industrial
    top_score, top_doc = results[0]
    assert "Nordic Industrial" in top_doc["company"] or "Nordic" in top_doc["text"]

def test_dense_retriever():
    provider = MockExternalProvider()
    dense = DenseRetriever(provider.documents)
    results = dense.search("Nordic Industrial EBITDA", top_k=3)
    assert len(results) == 3

def test_hybrid_retriever():
    provider = MockExternalProvider()
    hybrid = HybridRetriever(external_provider=provider)

    bm25_bundle = hybrid.search_bm25("Nordic Industrial revenue", top_k=3)
    assert len(bm25_bundle.results) == 3
    assert bm25_bundle.retriever_type == "bm25"

    dense_bundle = hybrid.search_dense("Nordic Industrial revenue", top_k=3)
    assert len(dense_bundle.results) == 3
    assert dense_bundle.retriever_type == "dense"

    hybrid_bundle = hybrid.search_hybrid("Nordic Industrial revenue", top_k=3)
    assert len(hybrid_bundle.results) == 3
    assert hybrid_bundle.retriever_type == "hybrid"

    # Check provenance preserved
    for ev in hybrid_bundle.results:
        assert ev.governance is not None
        assert ev.document_id
        assert ev.score >= 0

def test_retrieval_provenance():
    provider = MockExternalProvider()
    hybrid = HybridRetriever(provider)
    bundle = hybrid.search("EBITDA decline", top_k=5)
    for ev in bundle.results:
        assert ev.governance.source
        assert ev.governance.provenance
        assert ev.governance.retrieved_at
