from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum
import uuid

class TraceEventType(str, Enum):
    request_received = "request_received"
    request_normalised = "request_normalised"
    supervisor_decision = "supervisor_decision"
    agent_start = "agent_start"
    agent_end = "agent_end"
    retrieval_query = "retrieval_query"
    retrieval_result = "retrieval_result"
    tool_call = "tool_call"
    tool_result = "tool_result"
    model_call = "model_call"
    verifier_input = "verifier_input"
    verifier_output = "verifier_output"
    synthesiser_input = "synthesiser_input"
    final_output = "final_output"
    evaluation_result = "evaluation_result"
    error = "error"
    memory_read = "memory_read"
    memory_write = "memory_write"

class ModelCallMetadata(BaseModel):
    provider: str
    model_name: str
    prompt_version: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    estimated_cost: Optional[float] = None

class TraceEvent(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: TraceEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    latency_ms: Optional[int] = None
    tenant_id: str = Field(default="tenant_danske_mock")
    user_id: str = Field(default="user_banker_001")
    client_id: Optional[str] = None
    engagement_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
