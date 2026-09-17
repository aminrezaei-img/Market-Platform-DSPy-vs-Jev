from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

class FailureSeverity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    NONE = "NONE"

class FailureRecord(BaseModel):
    severity: FailureSeverity
    reason: str
    field: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None

class ScoreBundle(BaseModel):
    # L1 Retrieval
    recall_at_5: Optional[float] = None
    recall_at_10: Optional[float] = None
    mrr: Optional[float] = None
    gold_evidence_retrieval_rate: Optional[float] = None

    # L2 Tool/Routing
    task_classification_correct: Optional[bool] = None
    tool_selection_em: Optional[bool] = None
    tool_precision: Optional[float] = None
    tool_recall: Optional[float] = None
    argument_valid: Optional[bool] = None
    unnecessary_tool_calls: Optional[int] = None

    # L3 Financial correctness
    financial_correct: Optional[bool] = None
    exact_match: Optional[bool] = None
    absolute_error: Optional[float] = None
    relative_error: Optional[float] = None
    within_tolerance: Optional[bool] = None

    # L4 Grounding
    supported_claims: Optional[int] = None
    total_claims: Optional[int] = None
    grounding_score: Optional[float] = None
    citation_precision: Optional[float] = None
    unsupported_claims_count: Optional[int] = None

    # L5 Abstention
    abstention_correct: Optional[bool] = None
    abstention_precision: Optional[float] = None
    abstention_recall: Optional[float] = None
    false_confidence: Optional[bool] = None
    false_premise_detected: Optional[bool] = None

    # L6 Reliability
    reliability_pass: Optional[bool] = None

    # L7 Workflow
    workflow_success: Optional[bool] = None
    required_sections_present: Optional[bool] = None
    conflicts_surfaced: Optional[bool] = None
    missing_disclosed: Optional[bool] = None
    human_review_surfaced: Optional[bool] = None

    # Human review routing
    escalation_correct: Optional[bool] = None
    escalation_precision: Optional[float] = None
    escalation_recall: Optional[float] = None

    # Operational
    latency_ms: Optional[int] = None
    p50_latency_ms: Optional[int] = None
    p95_latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost: Optional[float] = None
    tool_call_count: Optional[int] = None
    model_call_count: Optional[int] = None
    error_count: Optional[int] = None

class EvaluationResult(BaseModel):
    run_id: str
    task_id: str
    dataset: str = Field(default="golden_suite")
    agent_version: str = Field(default="0.1.0")
    prompt_version: str = Field(default="supervisor-v1")
    retriever_version: str = Field(default="hybrid-v1")
    model_provider: str = Field(default="mock")
    model_name: str = Field(default="mock-model")
    tools_requested: List[str] = Field(default_factory=list)
    tools_executed: List[str] = Field(default_factory=list)
    retrieved_documents: List[str] = Field(default_factory=list)
    response: Optional[str] = None
    latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost: Optional[float] = None
    scores: ScoreBundle = Field(default_factory=ScoreBundle)
    failure_severity: FailureSeverity = Field(default=FailureSeverity.NONE)
    failure_reason: Optional[str] = None
    failure_records: List[FailureRecord] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    git_commit: Optional[str] = None
    dataset_version: Optional[str] = None
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)

    def is_pass(self) -> bool:
        return self.failure_severity in [FailureSeverity.NONE, FailureSeverity.P4, FailureSeverity.P3] or self.failure_severity == FailureSeverity.NONE

    def is_blocking(self) -> bool:
        return self.failure_severity in [FailureSeverity.P0, FailureSeverity.P1]
