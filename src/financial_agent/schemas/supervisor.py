from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional
from enum import Enum

class TaskType(str, Enum):
    pre_meeting_brief = "pre_meeting_brief"
    credit_lookup = "credit_lookup"
    relationship_lookup = "relationship_lookup"
    trading_lookup = "trading_lookup"
    false_premise = "false_premise"
    unanswerable = "unanswerable"
    conflict_check = "conflict_check"

class Answerability(str, Enum):
    answerable = "answerable"
    requires_internal_data = "requires_internal_data"
    requires_external_data = "requires_external_data"
    insufficient_evidence = "insufficient_evidence"
    incorrect_premise = "incorrect_premise"
    conflict_detected = "conflict_detected"
    tool_unavailable = "tool_unavailable"
    policy_blocked = "policy_blocked"

class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class SupervisorDecision(BaseModel):
    task_type: TaskType = Field(..., description="Classified task type")
    answerability: Answerability = Field(..., description="Can we answer? Why not?")
    required_specialists: List[Literal["internal", "research", "analysis"]] = Field(
        default_factory=list,
        description="Which specialists needed"
    )
    required_tools: List[str] = Field(
        default_factory=list,
        description="Tools expected to be needed"
    )
    parallelisable: bool = Field(default=True, description="Can internal+research run in parallel?")
    risk_level: RiskLevel = Field(default=RiskLevel.medium)
    needs_human_review: bool = Field(default=False)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    reasoning_summary: Optional[str] = Field(default=None, max_length=500, description="2 sentence max, not chain-of-thought")

    @field_validator('required_specialists')
    @classmethod
    def validate_specialists(cls, v):
        allowed = {"internal", "research", "analysis"}
        for item in v:
            if item not in allowed:
                raise ValueError(f"Invalid specialist {item}")
        return v

    def is_answerable(self) -> bool:
        return self.answerability == Answerability.answerable

    def requires_human(self) -> bool:
        return self.needs_human_review or self.answerability in [
            Answerability.conflict_detected,
            Answerability.tool_unavailable,
            Answerability.policy_blocked
        ] or self.risk_level in [RiskLevel.high, RiskLevel.critical]
