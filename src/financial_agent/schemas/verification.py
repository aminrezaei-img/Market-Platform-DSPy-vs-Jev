from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class VerifierRecommendation(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    FAIL_NEEDS_HUMAN = "FAIL_NEEDS_HUMAN"
    BLOCK = "BLOCK"

class UnsupportedClaim(BaseModel):
    claim: str
    reason: str = Field(description="Why unsupported: no evidence, conflicting, etc.")
    severity: str = Field(default="P1")

class ConflictRecord(BaseModel):
    field: str
    value_a: str
    source_a: str
    value_b: str
    source_b: str
    description: Optional[str] = None

class VerificationResult(BaseModel):
    supported_claims: int = Field(default=0, ge=0)
    total_claims: int = Field(default=0, ge=0)
    citation_precision: float = Field(default=0.0, ge=0.0, le=1.0)
    unsupported_claims: List[UnsupportedClaim] = Field(default_factory=list)
    conflicts: List[ConflictRecord] = Field(default_factory=list)
    critical_failure: bool = Field(default=False)
    recommendation: VerifierRecommendation = Field(default=VerifierRecommendation.PASS)
    reasoning: Optional[str] = None
    missing_information: List[str] = Field(default_factory=list)
    human_review_required: bool = Field(default=False)
    human_review_reasons: List[str] = Field(default_factory=list)

    def grounding_score(self) -> float:
        if self.total_claims == 0:
            return 1.0
        return self.supported_claims / self.total_claims

    def has_p1_failure(self) -> bool:
        return len(self.unsupported_claims) > 0 or self.critical_failure
