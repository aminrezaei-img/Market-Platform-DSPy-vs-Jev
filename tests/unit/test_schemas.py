"""Unit tests for schemas - Milestone 1"""
import pytest
from src.financial_agent.schemas import (
    UserRequest, SupervisorDecision, TaskType, Answerability, RiskLevel,
    Evidence, ToolDefinition, ToolResult, ToolStatus,
    VerificationResult, VerifierRecommendation,
    FinalBrief, TraceEvent, TraceEventType,
    EvaluationResult, FailureSeverity, LifecycleDecision, LifecycleOutcome
)
from src.financial_agent.schemas.common import GovernanceMetadata, ModelMetadata
from datetime import datetime

def test_user_request_schema():
    req = UserRequest(query="Prepare brief for Nordic Industrial A/S")
    assert req.query
    assert req.context.tenant_id == "tenant_danske_mock"

def test_supervisor_decision_schema():
    decision = SupervisorDecision(
        task_type=TaskType.pre_meeting_brief,
        answerability=Answerability.answerable,
        required_specialists=["internal", "research"],
        required_tools=["client_lookup", "document_search"],
        parallelisable=True,
        risk_level=RiskLevel.medium,
        needs_human_review=False,
        confidence=0.85
    )
    assert decision.is_answerable()
    assert not decision.requires_human()

def test_supervisor_fail_closed():
    decision = SupervisorDecision(
        task_type=TaskType.pre_meeting_brief,
        answerability=Answerability.tool_unavailable,
        required_specialists=["internal"],
        required_tools=["client_lookup"],
        parallelisable=False,
        risk_level=RiskLevel.high,
        needs_human_review=True,
        confidence=0.0
    )
    assert decision.requires_human()

def test_evidence_governance():
    gov = GovernanceMetadata(
        source="SEC",
        authoritative=True,
        permitted=True,
        provenance="SEC filing",
        retrieved_at=datetime.utcnow()
    )
    ev = Evidence(
        document_id="10K_2025",
        source="SEC",
        section="Financial",
        text="Revenue 2.4B",
        score=0.9,
        retriever="hybrid",
        governance=gov
    )
    assert ev.document_id == "10K_2025"
    assert ev.governance.authoritative

def test_tool_result_abstention():
    result = ToolResult(
        tool_name="credit_snapshot",
        status=ToolStatus.timeout,
        error_code="TIMEOUT"
    )
    assert result.to_abstention_reason() == "SOURCE_UNAVAILABLE"
    assert result.is_failure()

def test_verification_result():
    vr = VerificationResult(
        supported_claims=8,
        total_claims=10,
        citation_precision=0.8,
        recommendation=VerifierRecommendation.PASS_WITH_WARNINGS
    )
    assert vr.grounding_score() == 0.8
    assert not vr.has_p1_failure()

def test_trace_event():
    ev = TraceEvent(
        event_type=TraceEventType.request_received,
        payload={"query": "test"}
    )
    assert ev.event_type == TraceEventType.request_received

def test_evaluation_result():
    er = EvaluationResult(
        run_id="test_run",
        task_id="R01",
        dataset="golden_suite",
        failure_severity=FailureSeverity.NONE
    )
    assert not er.is_blocking()
    assert er.is_pass()

    er2 = EvaluationResult(
        run_id="test_run",
        task_id="R01",
        dataset="golden_suite",
        failure_severity=FailureSeverity.P0
    )
    assert er2.is_blocking()

def test_lifecycle_decision():
    ld = LifecycleDecision(
        candidate_run_id="candidate_001",
        outcome=LifecycleOutcome.BLOCK,
        reason="P0 failure"
    )
    assert ld.is_blocked()
