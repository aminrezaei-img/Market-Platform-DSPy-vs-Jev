"""Unit tests for DSPy programs - Phase 1.5"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import dspy
from financial_agent.dspy_programs.signatures import DecomposeBankerRequest, GenerateResearchQueries, ExtractClaims, VerifyClaim
from financial_agent.dspy_programs.query_planner import QueryPlannerPredict, QueryPlannerCoT, MockDSPyLM, dspy_to_supervisor_decision
from financial_agent.dspy_programs.memory_adapter import DSPyMemoryAdapter
from financial_agent.dspy_programs.tool_adapter import DSPyToolAdapter
from financial_agent.memory.short_term import ShortTermMemory
from financial_agent.memory.long_term import LongTermMemory
from financial_agent.providers.internal_provider import SyntheticInternalDataProvider
from financial_agent.providers.external_provider import MockExternalProvider
from financial_agent.tools.gateway import ToolGateway
from financial_agent.optimization.datasets import DSPyOptimizationDataset
from financial_agent.optimization.metrics import DSPyControlMetric

def test_dspy_signatures_exist():
    # Check signatures are valid dspy.Signature
    assert issubclass(DecomposeBankerRequest, dspy.Signature)
    assert issubclass(GenerateResearchQueries, dspy.Signature)
    assert issubclass(ExtractClaims, dspy.Signature)
    assert issubclass(VerifyClaim, dspy.Signature)

def test_mock_dspy_lm():
    from financial_agent.dspy_programs.query_planner import create_mock_dspy_lm
    mock_lm = create_mock_dspy_lm()
    dspy.settings.configure(lm=mock_lm)

    program = QueryPlannerPredict()
    result = program(
        request="Prepare a pre-meeting brief for Nordic Industrial A/S",
        memory_context="No preferences",
        available_sources=["synthetic_crm", "sec_filings"],
        available_tools=["client_lookup", "document_search"]
    )

    assert hasattr(result, 'task_type')
    assert hasattr(result, 'answerability')
    assert hasattr(result, 'required_specialists')
    assert hasattr(result, 'required_tools')

def test_dspy_to_supervisor_conversion():
    from financial_agent.dspy_programs.query_planner import create_mock_dspy_lm
    mock_lm = create_mock_dspy_lm()
    dspy.settings.configure(lm=mock_lm)

    program = QueryPlannerPredict()
    result = program(
        request="Why did Nordic Industrial A/S EBITDA decline 17% in 2025?",
        memory_context="",
        available_sources=["sec_filings"],
        available_tools=["document_search"]
    )

    decision = dspy_to_supervisor_decision(result)
    # With DummyLM list, first answer is pre_meeting_brief, second is false_premise
    # So first call returns pre_meeting_brief, but should still be valid
    assert decision.task_type.value in ["pre_meeting_brief", "false_premise", "conflict_check", "credit_lookup"]
    assert decision.confidence >= 0

def test_memory_adapter_no_leak():
    stm = ShortTermMemory()
    ltm = LongTermMemory()
    adapter = DSPyMemoryAdapter(stm, ltm)

    # Store client-specific
    from financial_agent.schemas.memory import MemoryItem, MemoryType
    item_a = MemoryItem(
        tenant_id="tenant_danske_mock",
        user_id="user_banker_001",
        client_id="client_001",
        memory_type=MemoryType.long_term_decision,
        content={"risk_appetite": "conservative"},
        is_authoritative=False,
        source="analyst"
    )
    ltm.store(item_a)

    # Store preference
    pref = MemoryItem(
        tenant_id="tenant_danske_mock",
        user_id="user_banker_001",
        client_id=None,
        memory_type=MemoryType.long_term_preference,
        content={"brief_style": "concise"},
        is_authoritative=False,
        source="user"
    )
    ltm.store(pref)

    # Retrieve for client_002 should not leak client_001
    ctx = adapter.get_safe_context("tenant_danske_mock", "user_banker_001", "client_002", None)
    assert "conservative" not in ctx
    assert "concise" in ctx or "No prior" in ctx or "brief_style" in ctx

def test_memory_adapter_blocks_authoritative():
    stm = ShortTermMemory()
    ltm = LongTermMemory()
    adapter = DSPyMemoryAdapter(stm, ltm)

    from financial_agent.schemas.memory import MemoryType
    with pytest.raises(ValueError):
        adapter.validate_and_store(
            tenant_id="tenant_danske_mock",
            user_id="user_banker_001",
            client_id="client_001",
            engagement_id=None,
            content={"credit_exposure": 450_000_000},
            memory_type=MemoryType.long_term_decision
        )

def test_tool_adapter_research_tools():
    internal = SyntheticInternalDataProvider()
    external = MockExternalProvider()
    gateway = ToolGateway(internal, external)
    adapter = DSPyToolAdapter(gateway)

    tools = adapter.get_research_tools()
    tool_names = [t.name for t in tools]

    assert "document_search" in tool_names
    assert "document_fetch" in tool_names
    assert "calculator" in tool_names
    # Should NOT include internal tools
    assert "credit_snapshot" not in tool_names
    assert "trade_activity" not in tool_names

def test_tool_adapter_gateway_preserved():
    internal = SyntheticInternalDataProvider()
    external = MockExternalProvider()
    gateway = ToolGateway(internal, external)
    adapter = DSPyToolAdapter(gateway)

    tools = adapter.get_research_tools()
    # Find document_search tool
    search_tool = [t for t in tools if t.name == "document_search"][0]

    # Call through DSPy tool wrapper -> should go through gateway and log
    gateway.clear_logs()
    result_str = search_tool.func(query="Nordic Industrial revenue")

    assert "SUCCESS" in result_str or "FAILED" in result_str
    # Gateway should have logged
    assert len(gateway.call_logs) > 0
    assert gateway.call_logs[0].tool_name == "document_search"

def test_optimization_dataset():
    ds = DSPyOptimizationDataset(size=60, seed=42)
    assert len(ds.get_train()) == 36  # 60% of 60
    assert len(ds.get_dev()) == 12   # 20%
    assert len(ds.get_holdout()) == 12  # 20%

    summary = ds.summary()
    assert summary["total"] == 60
    assert "pre_meeting_brief" in str(summary["categories"]) or "credit_lookup" in str(summary["categories"])

    examples = ds.to_dspy_examples("train")
    assert len(examples) == 36
    assert hasattr(examples[0], 'request')
    assert hasattr(examples[0], 'task_type')

def test_control_metric():
    ds = DSPyOptimizationDataset(size=10)
    examples = ds.to_dspy_examples("train")
    metric = DSPyControlMetric()

    from financial_agent.dspy_programs.query_planner import create_mock_dspy_lm
    mock_lm = create_mock_dspy_lm()
    dspy.settings.configure(lm=mock_lm)

    program = QueryPlannerPredict()
    example = examples[0]
    pred = program(
        request=example.request,
        memory_context=example.memory_context,
        available_sources=example.available_sources,
        available_tools=example.available_tools
    )

    score = metric(example, pred)
    assert 0.0 <= score <= 1.0

    # Test P0/P1 failure gives 0
    import dspy as dspy_lib
    false_example = dspy_lib.Example(
        request="Why did EBITDA decline 17%?",
        memory_context="",
        available_sources=["sec"],
        available_tools=["document_search"],
        task_type="false_premise",
        answerability="incorrect_premise",
        required_specialists=["research"],
        required_tools=["document_search"],
        research_questions=["..."],
        risk_level="high",
        needs_human_review=True
    ).with_inputs("request", "memory_context", "available_sources", "available_tools")

    wrong_pred = dspy_lib.Prediction(
        task_type="pre_meeting_brief",
        answerability="answerable",
        required_specialists=["internal", "research"],
        required_tools=["client_lookup", "document_search"],
        research_questions=["q1", "q2"],
        risk_level="medium",
        needs_human_review=False
    )

    score_wrong = metric(false_example, wrong_pred)
    assert score_wrong == 0.0  # P1 failure

def test_control_metric_with_feedback():
    ds = DSPyOptimizationDataset(size=10)
    examples = ds.to_dspy_examples("train")
    metric = DSPyControlMetric()

    from financial_agent.dspy_programs.query_planner import create_mock_dspy_lm
    mock_lm = create_mock_dspy_lm()
    dspy.settings.configure(lm=mock_lm)

    program = QueryPlannerPredict()
    example = examples[0]
    pred = program(
        request=example.request,
        memory_context=example.memory_context,
        available_sources=example.available_sources,
        available_tools=example.available_tools
    )

    score, feedback = metric.with_feedback(example, pred)
    assert 0.0 <= score <= 1.0
    assert isinstance(feedback, str)
    assert len(feedback) > 0
