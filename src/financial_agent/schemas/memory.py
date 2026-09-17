from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum

class MemoryType(str, Enum):
    short_term = "short_term"
    long_term_preference = "long_term_preference"
    long_term_decision = "long_term_decision"
    long_term_engagement_note = "long_term_engagement_note"

class MemoryItem(BaseModel):
    memory_id: str = Field(default_factory=lambda: f"mem_{datetime.utcnow().timestamp()}")
    tenant_id: str = Field(default="tenant_danske_mock")
    user_id: str = Field(default="user_banker_001")
    client_id: Optional[str] = None
    engagement_id: Optional[str] = None
    memory_type: MemoryType
    content: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_authoritative: bool = Field(default=False, description="Must be false for long-term")
    source: str = Field(default="user")
    embedding: Optional[list] = None

    def is_client_specific(self) -> bool:
        return self.client_id is not None

    def is_authoritative_state(self) -> bool:
        # Check if content contains authoritative fields
        auth_fields = {"credit_exposure", "credit_limit", "positions", "market_price", "gl_balance", "exposure", "limit"}
        content_keys = set(self.content.keys())
        return len(auth_fields.intersection(content_keys)) > 0 and self.is_authoritative
