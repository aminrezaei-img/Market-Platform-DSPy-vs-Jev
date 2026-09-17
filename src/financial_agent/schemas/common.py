from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ModelMetadata(BaseModel):
    provider: str = Field(description="e.g., anthropic, openai, mock, lfm")
    model_name: str
    model_version: Optional[str] = None
    prompt_version: str = Field(default="v1")
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    estimated_cost: Optional[float] = None

class Provenance(BaseModel):
    source: str = Field(description="e.g., synthetic_crm, synthetic_credit, sec_filing, calculator")
    document_id: Optional[str] = None
    section: Optional[str] = None

class GovernanceMetadata(BaseModel):
    source: str
    authoritative: bool = Field(default=False, description="Is this from authoritative system?")
    freshness_timestamp: Optional[datetime] = None
    permitted: bool = Field(default=True, description="Is use permitted for this workflow?")
    provenance: str = Field(description="Human-readable provenance")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    document_id: Optional[str] = None
