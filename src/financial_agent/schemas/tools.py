from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Literal
from datetime import datetime
from enum import Enum
from .common import GovernanceMetadata

class ToolStatus(str, Enum):
    success = "success"
    not_found = "not_found"
    timeout = "timeout"
    auth_error = "auth_error"
    conflict = "conflict"
    source_unavailable = "source_unavailable"
    error = "error"

class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    authorisation_scope: list = Field(default_factory=lambda: ["internal_read"])
    timeout_seconds: int = Field(default=5)
    error_behaviour: Literal["return_error_object", "raise"] = Field(default="return_error_object")
    is_authoritative: bool = Field(default=False)
    is_state_mutating: bool = Field(default=False)

class ToolResult(BaseModel):
    tool_name: str
    status: ToolStatus = Field(default=ToolStatus.success)
    data: Optional[Any] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    governance: Optional[GovernanceMetadata] = None
    latency_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def is_success(self) -> bool:
        return self.status == ToolStatus.success

    def is_failure(self) -> bool:
        return self.status != ToolStatus.success

    def to_abstention_reason(self) -> Optional[str]:
        mapping = {
            ToolStatus.not_found: "NOT_FOUND_IN_AUTHORITATIVE_SOURCE",
            ToolStatus.timeout: "SOURCE_UNAVAILABLE",
            ToolStatus.source_unavailable: "SOURCE_UNAVAILABLE",
            ToolStatus.auth_error: "PERMISSION_DENIED",
            ToolStatus.conflict: "CONFLICT_DETECTED",
        }
        return mapping.get(self.status)

class ToolCallLog(BaseModel):
    trace_id: str
    tool_name: str
    input: Dict[str, Any]
    caller_agent: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    result: Optional[ToolResult] = None
    latency_ms: Optional[int] = None
    tenant_id: str = Field(default="tenant_danske_mock")
    client_id: Optional[str] = None
