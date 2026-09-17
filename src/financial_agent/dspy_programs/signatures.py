"""
DSPy Signatures - Phase 1.5
Declarative LM programming with typed signatures
"""
import dspy
from typing import List, Literal

# 6. Program 1 — Banker Query Decomposition (centerpiece)
class DecomposeBankerRequest(dspy.Signature):
    """Decompose a banker request into bounded information and action requirements.
    Preserve original request intent. Generate subqueries as derived search/action plans.
    Focus on banking reliability: answerability, risk, human review, tool selection."""

    request: str = dspy.InputField(desc="Original banker request, e.g., Prepare brief for Nordic Industrial A/S")
    memory_context: str = dspy.InputField(desc="Safe namespaced memory context, e.g., user prefers concise briefs")
    available_sources: List[str] = dspy.InputField(desc="Available data sources: synthetic_crm, synthetic_credit, sec_filings, trading, etc.")
    available_tools: List[str] = dspy.InputField(desc="Available tools: client_lookup, credit_snapshot, document_search, etc.")

    task_type: str = dspy.OutputField(desc="One of: pre_meeting_brief, credit_lookup, relationship_lookup, trading_lookup, false_premise, unanswerable, conflict_check")
    answerability: str = dspy.OutputField(desc="One of: answerable, requires_internal_data, requires_external_data, insufficient_evidence, incorrect_premise, conflict_detected, tool_unavailable, policy_blocked")
    required_specialists: List[str] = dspy.OutputField(desc="List subset of: internal, research, analysis")
    required_tools: List[str] = dspy.OutputField(desc="List of required tool names from available_tools")
    research_questions: List[str] = dspy.OutputField(desc="Derived research subqueries for external retrieval, 2-4 focused questions")
    risk_level: str = dspy.OutputField(desc="One of: low, medium, high, critical")
    needs_human_review: bool = dspy.OutputField(desc="True if conflict, missing authoritative data, false premise, or high risk")

# 10. Program 2 — Retrieval Query Generation
class GenerateResearchQueries(dspy.Signature):
    """Generate focused retrieval queries for a financial research task.
    Each query should be specific, include company name, and target one information need."""

    banker_request: str = dspy.InputField(desc="Original banker request")
    task_plan: str = dspy.InputField(desc="Decomposed task plan from DecomposeBankerRequest")
    company: str = dspy.InputField(desc="Company name, e.g., Nordic Industrial A/S")

    queries: List[str] = dspy.OutputField(desc="List of 2-4 focused retrieval queries for external financial documents")

# 25. DSPy Verifier Enhancement - Claim extraction
class ExtractClaims(dspy.Signature):
    """Extract factual claims from a banker brief that need verification.
    Focus on claims with numbers, exposures, limits, financial metrics."""

    brief: str = dspy.InputField(desc="Final brief markdown or sections")

    claims: List[str] = dspy.OutputField(desc="List of factual claims that need evidence, e.g., 'Credit limit DKK 800m', 'EBITDA increased 4%'")

# Claim verification
class VerifyClaim(dspy.Signature):
    """Verify a single claim against evidence.
    Determine if claim is supported, unsupported, conflicting, or insufficient evidence."""

    claim: str = dspy.InputField(desc="Single factual claim to verify")
    evidence: List[str] = dspy.InputField(desc="List of evidence passages with doc IDs")

    verdict: Literal["SUPPORTED", "UNSUPPORTED", "CONFLICTING", "INSUFFICIENT_EVIDENCE"] = dspy.OutputField(desc="Verification verdict")
    evidence_ids: List[str] = dspy.OutputField(desc="List of evidence document IDs that support or contradict claim")
    reasoning: str = dspy.OutputField(desc="Brief reasoning for verdict, max 2 sentences")

# Additional signature for tool-aware research
class ResearchWithTools(dspy.Signature):
    """Answer a financial research question using available tools.
    Use document_search to find evidence, document_fetch for details, calculator for calculations."""

    question: str = dspy.InputField(desc="Research question to answer")
    company: str = dspy.InputField(desc="Company name")
    context: str = dspy.InputField(desc="Additional context from internal data or prior steps")

    answer: str = dspy.OutputField(desc="Answer with citations, or abstention reason if insufficient evidence")
    evidence_used: List[str] = dspy.OutputField(desc="Document IDs used")
    tools_used: List[str] = dspy.OutputField(desc="Tools used in reasoning")
