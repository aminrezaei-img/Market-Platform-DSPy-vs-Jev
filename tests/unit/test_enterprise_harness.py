"""Unit tests for Enterprise Harness - Phase 1E"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from financial_agent.registry import (
    AgentRegistry, WorkflowRegistry, ModelRegistry, ProgramRegistry,
    ToolRegistry, DatasetRegistry, SuiteRegistry, ScorerRegistry,
    JudgeRegistry, ExperimentRegistry, FailureRegistry,
    AgentManifest, WorkflowManifest, ModelManifest, ProgramManifest,
    ToolManifest, DatasetManifest, SuiteManifest
)
from financial_agent.enterprise import (
    TraceBus, PolicyEngine, EnterpriseMemoryService,
    EvidencePackGenerator, ReplayEngine, OnlineEvalInterface
)
from financial_agent.enterprise.trace_bus import TraceEventType
from financial_agent.enterprise.policy import PolicyInput, PolicyDecision
from financial_agent.enterprise.eval_harness import EnterpriseEvalHarness

def test_agent_registry():
    reg = AgentRegistry(registry_root="test_registry")
    manifest = AgentManifest(
        id="test.agent",
        version="1.0.0",
        owner="test",
        description="Test agent",
        capabilities=["test"],
        workflow_id="test_wf",
        workflow_version="1"
    )
    reg.register(manifest)
    retrieved = reg.get("test.agent", "1.0.0")
    assert retrieved is not None
    assert retrieved.id == "test.agent"
    assert reg.exists("test.agent", "1.0.0")

    # Reconstruct
    recon = reg.reconstruct("test.agent", "1.0.0")
    assert recon["reconstructable"] is True

    # Cleanup
    reg.delete("test.agent", "1.0.0")

def test_workflow_registry():
    reg = WorkflowRegistry(registry_root="test_registry")
    manifest = WorkflowManifest(
        id="test_workflow",
        version="1.0.0",
        description="Test workflow"
    )
    reg.register(manifest)
    retrieved = reg.get("test_workflow", "1.0.0")
    assert retrieved is not None
    reg.delete("test_workflow", "1.0.0")

def test_model_registry():
    reg = ModelRegistry(registry_root="test_registry")
    manifest = ModelManifest(
        id="mock.test",
        version="1.0.0",
        provider="mock",
        model_id="mock-model"
    )
    reg.register(manifest)
    retrieved = reg.get("mock.test", "1.0.0")
    assert retrieved is not None
    assert retrieved.provider == "mock"
    reg.delete("mock.test", "1.0.0")

def test_program_registry_lineage():
    reg = ProgramRegistry(registry_root="test_registry")
    prog1 = ProgramManifest(
        id="test_prog",
        version="1.0.0",
        dspy_signature="DecomposeBankerRequest",
        dspy_module="Predict",
        artifact_path="test.json",
        evidence_type="measured"
    )
    prog2 = ProgramManifest(
        id="test_prog",
        version="2.0.0",
        dspy_signature="DecomposeBankerRequest",
        dspy_module="Predict",
        optimizer="MIPROv2",
        parent_program="test_prog@1.0.0",
        artifact_path="test2.json",
        evidence_type="simulated",
        lineage=["test_prog@1.0.0"]
    )
    reg.register(prog1)
    reg.register(prog2)

    lineage = reg.get_lineage("test_prog", "2.0.0")
    assert len(lineage) == 2

    reg.delete("test_prog", "1.0.0")
    reg.delete("test_prog", "2.0.0")

def test_tool_registry():
    reg = ToolRegistry(registry_root="test_registry")
    manifest = ToolManifest(
        id="test_tool",
        version="1.0.0",
        description="Test tool",
        authoritative=False,
        data_classification="public"
    )
    reg.register(manifest)
    retrieved = reg.get("test_tool", "1.0.0")
    assert retrieved is not None

    research_tools = reg.get_research_tools()
    # Should include our test tool if public and non-authoritative
    assert any(t.id == "test_tool" for t in research_tools)

    reg.delete("test_tool", "1.0.0")

def test_dataset_registry_training_allowed():
    reg = DatasetRegistry(registry_root="test_registry")
    ds_eval = DatasetManifest(
        id="test_eval",
        version="1.0.0",
        task_count=10,
        training_allowed=False,
        evaluation_only=True
    )
    ds_train = DatasetManifest(
        id="test_train",
        version="1.0.0",
        task_count=10,
        training_allowed=True,
        evaluation_only=False
    )
    reg.register(ds_eval)
    reg.register(ds_train)

    assert reg.check_training_allowed("test_eval", "1.0.0") is False
    assert reg.check_training_allowed("test_train", "1.0.0") is True

    # FinAgent must be eval only
    finagent = DatasetManifest(
        id="finagent_1_1_1",
        version="1.0.0",
        task_count=20,
        training_allowed=False,
        evaluation_only=True
    )
    reg.register(finagent)
    assert reg.check_training_allowed("finagent_1_1_1", "1.0.0") is False

    reg.delete("test_eval", "1.0.0")
    reg.delete("test_train", "1.0.0")
    reg.delete("finagent_1_1_1", "1.0.0")

def test_evidence_type_separation():
    # Every result must have evidence_type measured/simulated/expected
    # UI must visually distinguish
    reg = ProgramRegistry(registry_root="test_registry")
    measured = ProgramManifest(
        id="test_prog",
        version="1.0.0",
        artifact_path="test.json",
        evidence_type="measured"
    )
    simulated = ProgramManifest(
        id="test_prog",
        version="2.0.0",
        artifact_path="test2.json",
        evidence_type="simulated"
    )
    reg.register(measured)
    reg.register(simulated)

    m = reg.get("test_prog", "1.0.0")
    s = reg.get("test_prog", "2.0.0")

    assert m.evidence_type == "measured"
    assert s.evidence_type == "simulated"
    assert m.evidence_type != s.evidence_type

    reg.delete("test_prog", "1.0.0")
    reg.delete("test_prog", "2.0.0")

def test_trace_bus():
    bus = TraceBus(trace_dir="test_traces")
    trace_id = bus.start_trace()

    event = bus.emit_simple(
        event_type=TraceEventType.tool_call,
        component="credit_agent",
        payload={"tool_name": "credit_snapshot"},
        agent_id="markets.pre_meeting_brief",
        agent_version="1.2.0",
        artifact_versions={"tool": "credit_snapshot@2", "model": "test@1"}
    )

    assert event.trace_id == trace_id
    assert event.agent_id == "markets.pre_meeting_brief"
    assert "tool" in event.artifact_versions

    events = bus.get_events(trace_id)
    assert len(events) == 1

    # Replay ready
    replay_info = bus.replay_ready(trace_id)
    assert replay_info["replayable"] is True

def test_policy_engine():
    engine = PolicyEngine()

    # research_agent + credit_snapshot -> DENY
    inp = PolicyInput(agent="research_agent", tool="credit_snapshot", action="read")
    decision = engine.evaluate(inp)
    assert decision == PolicyDecision.DENY

    # internal_agent + credit_snapshot -> ALLOW
    inp2 = PolicyInput(agent="internal_agent", tool="credit_snapshot", action="read")
    decision2 = engine.evaluate(inp2)
    assert decision2 == PolicyDecision.ALLOW

    # change_credit_limit -> REQUIRE_APPROVAL
    inp3 = PolicyInput(agent="any_agent", tool="change_credit_limit", action="mutate")
    decision3 = engine.evaluate(inp3)
    assert decision3 == PolicyDecision.REQUIRE_APPROVAL

    # All decisions traced
    assert len(engine.get_log()) >= 3

def test_memory_service_namespaces():
    service = EnterpriseMemoryService()

    # Store preference
    record = service.store_simple(
        tenant="tenant_danske_mock",
        user="user_banker_001",
        client=None,
        engagement=None,
        agent=None,
        content={"brief_style": "concise"},
        source="user"
    )
    assert record.authoritative is False

    # Store client-specific
    record2 = service.store_simple(
        tenant="tenant_danske_mock",
        user="user_banker_001",
        client="client_001",
        engagement=None,
        agent=None,
        content={"risk_appetite": "conservative"},
        source="analyst"
    )

    # Retrieve for client_002 should not leak client_001
    results = service.retrieve(
        tenant="tenant_danske_mock",
        user="user_banker_001",
        client="client_002"
    )
    # Should not contain conservative
    contents = [str(r.content) for r in results]
    assert not any("conservative" in c for c in contents)
    # Should contain concise (global preference)
    assert any("concise" in c for c in contents)

    # Authoritative should be blocked
    with pytest.raises(ValueError):
        service.store_simple(
            tenant="tenant_danske_mock",
            user="user_banker_001",
            client="client_001",
            engagement=None,
            agent=None,
            content={"credit_exposure": 450000000},
            source="user"
        )

def test_evidence_pack():
    generator = EvidencePackGenerator(registry_root="test_registry", output_dir="test_evidence_packs")

    mock_results = {
        "metrics": {"accuracy": 0.85},
        "p0_failures": 0,
        "p1_failures": 0,
        "model_versions": {"supervisor": "test@1"},
        "datasets": ["golden@1"],
        "scorer_versions": ["test@1"]
    }

    pack = generator.generate(
        candidate_identity="test.agent@1.0.0",
        baseline_identity="test.agent@0.9.0",
        experiment_results=mock_results,
        evidence_type="measured"
    )

    assert pack.candidate_identity == "test.agent@1.0.0"
    assert pack.lifecycle_decision in ["PASS", "BLOCK", "HUMAN_REVIEW", "PASS_WITH_WARNINGS"]
    assert pack.evidence_type == "measured"

    # Test BLOCK when P1>0
    mock_results_block = {
        "metrics": {"accuracy": 0.85},
        "p0_failures": 0,
        "p1_failures": 1,
        "model_versions": {},
        "datasets": [],
        "scorer_versions": []
    }
    pack_block = generator.generate(
        candidate_identity="test.agent@1.1.0",
        baseline_identity="test.agent@1.0.0",
        experiment_results=mock_results_block,
        evidence_type="measured"
    )
    assert pack_block.lifecycle_decision == "BLOCK"

def test_failure_registry():
    # Use main registry which is bootstrapped
    reg = FailureRegistry(registry_root="registry_store")
    failures = reg.get_blocking()
    # Should have P0/P1 blocking failures
    assert len(failures) > 0
    p0 = reg.get_p0()
    assert len(p0) > 0
    p1 = reg.get_p1()
    assert len(p1) > 0

def test_judge_calibration():
    reg = JudgeRegistry(registry_root="registry_store")
    judges = reg.get_calibrated(min_agreement=0.8)
    # Should have at least one calibrated judge
    assert len(judges) >= 1
    for judge in judges:
        assert judge.calibration.agreement >= 0.8

def test_experiment_registry_measured_simulated():
    reg = ExperimentRegistry(registry_root="test_registry")
    from financial_agent.registry.experiment_registry import ExperimentManifest

    measured = ExperimentManifest(
        id="exp_measured",
        version="1",
        candidate="test@1.0.0",
        agent_id="test",
        agent_version="1.0.0",
        suite_id="test_suite",
        suite_version="1.0.0",
        evidence_type="measured"
    )
    simulated = ExperimentManifest(
        id="exp_simulated",
        version="1",
        candidate="test@2.0.0",
        agent_id="test",
        agent_version="2.0.0",
        suite_id="test_suite",
        suite_version="1.0.0",
        evidence_type="simulated"
    )
    reg.register(measured)
    reg.register(simulated)

    measured_list = reg.get_measured()
    simulated_list = reg.get_simulated()

    assert any(e.id == "exp_measured" for e in measured_list)
    assert any(e.id == "exp_simulated" for e in simulated_list)

    reg.delete("exp_measured", "1")
    reg.delete("exp_simulated", "1")

def test_online_eval():
    iface = OnlineEvalInterface(sample_rate=1.0)  # sample all

    trace = {
        "trace_id": "test_trace",
        "agent_id": "test_agent",
        "p1_failures": 1,
        "tool_errors": 0,
        "latency_ms": 1000,
        "abstention_rate": 0.8
    }

    sample = iface.ingest(trace)
    assert sample.sampled is True

    alerts = iface.get_alerts()
    # Should have P1 alert
    assert len(alerts) >= 1
    assert any(a.alert_type.value == "P1_UNSUPPORTED_CLAIM" for a in alerts)

def test_replay_engine():
    bus = TraceBus(trace_dir="test_traces")
    trace_id = bus.start_trace()
    bus.emit_simple(
        event_type=TraceEventType.request_received,
        component="supervisor",
        payload={"query": "Test query", "client_id": "client_001"}
    )

    engine = ReplayEngine(trace_bus=bus)
    result = engine.replay(trace_id, "markets.pre_meeting_brief", "1.3.0")

    assert result["original_trace_id"] == trace_id
    assert result["candidate"] == "markets.pre_meeting_brief@1.3.0"
    assert result["original_request"]["query"] == "Test query"
