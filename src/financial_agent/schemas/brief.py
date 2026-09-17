from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from .evidence import Evidence
from .verification import VerificationResult

class BriefSection(BaseModel):
    title: str
    content: str
    evidence: List[Evidence] = Field(default_factory=list)
    verified: bool = Field(default=False)
    confidence: str = Field(default="medium")  # low, medium, high

class HumanReviewItem(BaseModel):
    item: str
    reason: str
    severity: str = Field(default="medium")
    source: Optional[str] = None

class AbstentionRecord(BaseModel):
    field: str
    reason: str  # e.g., SOURCE_UNAVAILABLE, CONFLICT_DETECTED, INCORRECT_PREMISE
    details: Optional[str] = None

class FinalBrief(BaseModel):
    client_name: str
    client_id: Optional[str] = None
    request_query: str
    sections: List[BriefSection] = Field(default_factory=list)
    verification: Optional[VerificationResult] = None
    warnings: List[str] = Field(default_factory=list)
    human_review_items: List[HumanReviewItem] = Field(default_factory=list)
    abstentions: List[AbstentionRecord] = Field(default_factory=list)
    conflicts_surfaced: List[Dict[str, Any]] = Field(default_factory=list)
    governance_summary: Dict[str, Any] = Field(default_factory=dict)
    generated_at: str = Field(default="")

    def has_critical_issues(self) -> bool:
        if self.verification and self.verification.critical_failure:
            return True
        if self.verification and self.verification.recommendation in ["BLOCK", "FAIL_NEEDS_HUMAN"]:
            return True
        return False

    def to_markdown(self) -> str:
        md = f"# Pre-Meeting Brief: {self.client_name}\n\n"
        md += f"**Query:** {self.request_query}\n\n"
        for sec in self.sections:
            md += f"## {sec.title}\n{sec.content}\n\n"
            if sec.evidence:
                md += "**Evidence:**\n"
                for ev in sec.evidence[:3]:
                    md += f"- {ev.document_id} ({ev.source}) score={ev.score:.2f}: {ev.text[:150]}...\n"
                md += "\n"
        if self.abstentions:
            md += "## Information Not Verified\n"
            for ab in self.abstentions:
                md += f"- **{ab.field}**: {ab.reason} - {ab.details or ''}\n"
            md += "\n"
        if self.conflicts_surfaced:
            md += "## Conflicts Detected\n"
            for c in self.conflicts_surfaced:
                md += f"- {c}\n"
            md += "\n"
        if self.human_review_items:
            md += "## Human Review Required\n"
            for hr in self.human_review_items:
                md += f"- {hr.item}: {hr.reason} (severity: {hr.severity})\n"
            md += "\n"
        if self.verification:
            md += f"## Verification\nRecommendation: {self.verification.recommendation}\n"
            md += f"Grounding: {self.verification.supported_claims}/{self.verification.total_claims}\n"
        return md
