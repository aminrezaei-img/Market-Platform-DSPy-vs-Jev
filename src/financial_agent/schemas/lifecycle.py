from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

class LifecycleOutcome(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK = "BLOCK"

class RegressionComparison(BaseModel):
    baseline_run_id: str
    candidate_run_id: str
    baseline_metrics: Dict[str, Any] = Field(default_factory=dict)
    candidate_metrics: Dict[str, Any] = Field(default_factory=dict)
    deltas: Dict[str, Any] = Field(default_factory=dict)
    regressions: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    blocking_failures: List[str] = Field(default_factory=list)

class LifecycleDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"ld_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    baseline_run_id: Optional[str] = None
    candidate_run_id: str
    outcome: LifecycleOutcome
    reason: str
    blocking_gates_violated: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    comparison: Optional[RegressionComparison] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    evaluator_version: str = Field(default="lifecycle-gate-v1")

    def is_blocked(self) -> bool:
        return self.outcome == LifecycleOutcome.BLOCK
