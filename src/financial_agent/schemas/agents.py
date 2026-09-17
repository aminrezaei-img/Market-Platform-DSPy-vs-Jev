from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from enum import Enum
from .evidence import EvidenceBundle
from .tools import ToolResult
from .common import ModelMetadata

class AgentType(str, Enum):
    supervisor = "supervisor"
    internal_data = "internal_data"
    research = "research"
    analysis = "analysis"
    verifier = "verifier"
    synthesiser = "synthesiser"

class AgentResult(BaseModel):
    agent_type: AgentType
    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(default_factory=dict)
    evidence: Optional[EvidenceBundle] = None
    tool_results: List[ToolResult] = Field(default_factory=list)
    model_metadata: Optional[ModelMetadata] = None
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    # For internal data agent: structured facts
    facts: Dict[str, Any] = Field(default_factory=dict)
    # For analysis agent: calculations
    calculations: List[Dict[str, Any]] = Field(default_factory=list)
