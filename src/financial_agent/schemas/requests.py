from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class RequestContext(BaseModel):
    tenant_id: str = Field(default="tenant_danske_mock")
    user_id: str = Field(default="user_banker_001")
    client_id: Optional[str] = None
    engagement_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None

class UserRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = Field(..., description="Banker request e.g., Prepare brief for Nordic Industrial A/S")
    context: RequestContext = Field(default_factory=RequestContext)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # For golden suite / eval
    task_id: Optional[str] = None
    dataset: Optional[str] = None
    expected_behavior: Optional[str] = None
