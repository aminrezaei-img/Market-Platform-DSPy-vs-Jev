from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from .common import GovernanceMetadata

class Evidence(BaseModel):
    document_id: str
    source: str = Field(description="SEC, synthetic_crm, etc.")
    section: Optional[str] = None
    text: str
    score: float = Field(default=0.0, ge=0.0, description="Relevance score, normalized to 0-1 where possible, raw BM25 may be >1 but capped in retriever")
    retriever: str = Field(default="hybrid", description="bm25, dense, hybrid")
    metadata: dict = Field(default_factory=dict)
    governance: GovernanceMetadata

    @property
    def normalized_score(self) -> float:
        # Cap at 1.0 for display
        return min(1.0, self.score)

class EvidenceBundle(BaseModel):
    query: str
    results: List[Evidence] = Field(default_factory=list)
    retriever_type: str = Field(default="hybrid")
    latency_ms: Optional[int] = None
    total_retrieved: int = Field(default=0)

    def top_k(self, k: int = 5) -> List[Evidence]:
        return sorted(self.results, key=lambda x: x.score, reverse=True)[:k]

    def has_gold(self, gold_doc_id: str) -> bool:
        return any(ev.document_id == gold_doc_id for ev in self.results)
