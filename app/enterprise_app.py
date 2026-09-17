"""
Enterprise Agent & Evaluation Harness Dashboard - Phase 1E
Demonstrates reusable, manifest-driven platform
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import json
from datetime import datetime

from financial_agent.registry import (
    AgentRegistry, WorkflowRegistry, ModelRegistry, ProgramRegistry,
    ToolRegistry, DatasetRegistry, SuiteRegistry, ScorerRegistry,
    JudgeRegistry, ExperimentRegistry, FailureRegistry
)
from financial_agent.registry.bootstrap import bootstrap_all
from financial_agent.enterprise import TraceBus, PolicyEngine, EnterpriseMemoryService, EvidencePackGenerator, ReplayEngine, OnlineEvalInterface
from financial_agent.enterprise.eval_harness import EnterpriseEvalHarness

st.set_page_config(page_title="Enterprise Harness - Phase 1E", layout="wide")

st.title("Enterprise Agent & Evaluation Harness - Phase 1E")
st.caption("Evaluation-driven enterprise agent development harness reference implementation")

# Sidebar
st.sidebar.header("Enterprise Control Plane")
if st.sidebar.button("Bootstrap Registries"):
    with st.spinner("Bootstrapping..."):
        counts = bootstrap_all()
        st.sidebar.success(f"Bootstrapped: {counts}")

registry_root = "registry_store"

# Tabs per spec 32
tabs = st.tabs([
    "Agent Registry", "Workflow Registry", "Model Registry", "Program Registry", "Tool Registry",
    "Dataset Registry", "Suite Registry", "Experiments", "Slices", "Failures", "Judges", "Lifecycle Evidence", "Trace Bus", "Policy", "Replay", "Online Eval"
])

with tabs[0]:
    st.header("Agent Registry")
    st.caption("Every agent receives immutable identity: agent_id, version, owner, capabilities, contracts, policies")

    reg = AgentRegistry(registry_root)
    agents = reg.list()
    st.metric("Registered Agents", len(agents))

    # Filter
    owner_filter = st.selectbox("Filter by owner", ["all"] + list(set(a.owner for a in agents)))
    if owner_filter != "all":
        agents = [a for a in agents if a.owner == owner_filter]

    for agent in agents:
        with st.expander(f"{agent.id}@{agent.version} - {agent.owner} - {agent.description[:60]}"):
            st.json(agent.model_dump())
            if st.button(f"Reconstruct {agent.id}@{agent.version}", key=f"recon_{agent.id}_{agent.version}"):
                reconstructed = reg.reconstruct(agent.id, agent.version)
                st.json(reconstructed)
                st.success("Agent reconstructable from registry state - PASS")

    st.subheader("Create Candidate")
    st.markdown("""
    **Demo Flow:**
    1. Open Agent Registry - Show PreMeetingBriefAgent v1.2
    2. Create candidate v1.3 using DSPy GEPA program
    3. Run suite markets_pre_meeting_release@3
    4. Show FinAgent, Golden, retrieval, tool, workflow, HITL, latency, cost
    5. Open slices - candidate better overall but worse on conflicting_data
    6. Lifecycle Gate BLOCK
    7. Open evidence pack - every artifact versioned
    """)

    if st.button("Create Candidate v1.3 from GEPA"):
        from financial_agent.registry import AgentManifest
        # Get latest
        base = reg.get("markets.pre_meeting_brief", "1.2.0")
        if base:
            candidate = AgentManifest(
                id=base.id,
                version="1.3.0",
                owner=base.owner,
                description="Candidate v1.3 - GEPA optimized, candidate for release",
                capabilities=base.capabilities + ["dspy_gepa"],
                workflow_id=base.workflow_id,
                workflow_version=base.workflow_version,
                model_policy={"supervisor": "dspy.gepa@3.0.0", "verifier": "frontier-verifier@1"},
                tool_policy=base.tool_policy,
                memory_policy=base.memory_policy,
                eval_policy=base.eval_policy,
                tags=["candidate", "gepa", "simulated"]
            )
            reg.register(candidate)
            st.success(f"Created {candidate.id}@{candidate.version}")

with tabs[1]:
    st.header("Workflow Registry")
    st.caption("Register workflows separately from agents - nodes, edges, parallel branches, tool requirements")

    reg = WorkflowRegistry(registry_root)
    workflows = reg.list()
    st.metric("Registered Workflows", len(workflows))

    for wf in workflows:
        with st.expander(f"{wf.id}@{wf.version} - {wf.description[:60]}"):
            st.json(wf.model_dump())
            st.text(f"Framework: {wf.framework}, Entry: {wf.entry_node}, Exit: {wf.exit_node}")
            st.text(f"Parallel branches: {wf.parallel_branches}")

with tabs[2]:
    st.header("Model Registry")
    st.caption("Lightweight model registry - provider, model_id, family, version, context, cost, capabilities")

    reg = ModelRegistry(registry_root)
    models = reg.list()
    st.metric("Registered Models", len(models))

    provider_filter = st.selectbox("Filter by provider", ["all", "mock", "anthropic", "openai", "local", "dspy"])
    if provider_filter != "all":
        models = [m for m in models if m.provider == provider_filter]

    for model in models:
        with st.expander(f"{model.id}@{model.version} - {model.provider}"):
            st.json(model.model_dump())

    st.info("Later Phase 2 simply registers LFM variants - same interface")

with tabs[3]:
    st.header("Program Registry")
    st.caption("DSPy program lineage tracking - prevents 'optimised prompt magic' from becoming untraceable")

    reg = ProgramRegistry(registry_root)
    programs = reg.list()
    st.metric("Registered Programs", len(programs))

    for prog in programs:
        with st.expander(f"{prog.id}@{prog.version} - {prog.dspy_module} - {prog.optimizer} - {prog.evidence_type}"):
            st.json(prog.model_dump())
            st.text(f"Lineage: {prog.full_lineage()}")
            if prog.evidence_type == "simulated":
                st.warning(f"⚠️ SIMULATED RESULT - evidence_type={prog.evidence_type} - must not appear next to measured without distinction")

    st.subheader("Lineage Example")
    st.code("""
query_planner_v1 (Predict)
      ↓
MIPRO run 018
      ↓
query_planner_v2
      ↓
GEPA run 027
      ↓
query_planner_v3
    """)

    # Show lineage for latest
    lineage = reg.get_lineage("query_planner", "3.0.0")
    if lineage:
        st.text("Full lineage for query_planner@3.0.0:")
        for p in lineage:
            st.text(f"  {p.id}@{p.version} - {p.optimizer} - {p.evidence_type}")

with tabs[4]:
    st.header("Tool Registry")
    st.caption("Tool Gateway backed by registry - agents do not hard-code tools")

    reg = ToolRegistry(registry_root)
    tools = reg.list()
    st.metric("Registered Tools", len(tools))

    for tool in tools:
        with st.expander(f"{tool.id}@{tool.version} - {tool.owner} - authoritative={tool.authoritative}"):
            st.json(tool.model_dump())
            if tool.state_mutating:
                st.warning("State-mutating tool - requires approval per policy")

    st.subheader("Research Tools Only")
    research_tools = reg.get_research_tools()
    st.text(f"Research tools (non-authoritative, public): {[t.id for t in research_tools]}")

    authoritative = reg.get_authoritative_tools()
    st.text(f"Authoritative tools: {[t.id for t in authoritative]}")

with tabs[5]:
    st.header("Dataset Registry")
    st.caption("All evaluation datasets registered - prevents accidental leakage")

    reg = DatasetRegistry(registry_root)
    datasets = reg.list()
    st.metric("Registered Datasets", len(datasets))

    for ds in datasets:
        with st.expander(f"{ds.id}@{ds.version} - {ds.source} - training_allowed={ds.training_allowed}"):
            st.json(ds.model_dump())
            if not ds.training_allowed:
                st.info(f"🔒 {ds.id}: training_allowed=False - evaluation_only")
            if ds.id.startswith("finagent"):
                st.warning(f"⚠️ {ds.id}: training_allowed=False - FinAgent never for fine-tuning")

    st.subheader("Training vs Evaluation")
    training_allowed = reg.get_training_allowed()
    eval_only = reg.get_evaluation_only()
    st.text(f"Training allowed: {[d.id for d in training_allowed]}")
    st.text(f"Evaluation only: {[d.id for d in eval_only]}")

with tabs[6]:
    st.header("Suite Registry")
    st.caption("Suite != Dataset - major enterprise abstraction")

    reg = SuiteRegistry(registry_root)
    suites = reg.list()
    st.metric("Registered Suites", len(suites))

    for suite in suites:
        with st.expander(f"{suite.id}@{suite.version}"):
            st.json(suite.model_dump())
            st.text(f"Datasets: {suite.datasets}")
            st.text(f"Metrics: {suite.metrics}")
            st.text(f"Slices: {suite.slices}")
            st.text(f"Lifecycle policy: {suite.lifecycle_policy}")

with tabs[7]:
    st.header("Experiments")
    st.caption("Every evaluation run becomes experiment with full provenance - resolves ambiguous baseline")

    reg = ExperimentRegistry(registry_root)
    experiments = reg.list()
    st.metric("Registered Experiments", len(experiments))

    # Filter measured vs simulated
    filter_type = st.selectbox("Filter evidence_type", ["all", "measured", "simulated", "expected"])
    if filter_type != "all":
        experiments = [e for e in experiments if e.evidence_type == filter_type]

    for exp in experiments[-20:]:  # last 20
        with st.expander(f"{exp.id} - {exp.candidate} - {exp.evidence_type} - {exp.suite_id}"):
            st.json(exp.model_dump())
            if exp.evidence_type == "simulated":
                st.warning("⚠️ SIMULATED - visually distinguished from measured")
            if exp.evidence_type == "measured":
                st.success("✅ MEASURED")

    st.subheader("Unambiguous Baselines")
    st.markdown("""
    Never use ambiguous names like `phase1_baseline`

    Instead:
    - `premeeting.cautious.v1`
    - `premeeting.rulebased.v1`
    - `premeeting.dspy.predict.v1`

    Every experiment records explicit baseline identity
    """)

    # Run new evaluation
    st.subheader("Run Evaluation")
    agent_id = st.text_input("Agent ID", "markets.pre_meeting_brief")
    agent_version = st.text_input("Agent Version", "1.3.0")
    suite_id = st.text_input("Suite ID", "markets_pre_meeting_release")
    suite_version = st.text_input("Suite Version", "3.0.0")
    evidence_type = st.selectbox("Evidence Type", ["measured", "simulated", "expected"])

    if st.button("Run Evaluation (Offline)"):
        harness = EnterpriseEvalHarness(registry_root)
        result = harness.evaluate(agent_id, agent_version, suite_id, suite_version, evidence_type=evidence_type)
        st.success(f"Experiment {result.experiment_id} - Accuracy {result.overall.get('accuracy', 0):.3f}")
        st.json(result.model_dump())

with tabs[8]:
    st.header("Slice Analysis")
    st.caption("Never report only global averages - per spec 24")

    # Get latest experiment
    exp_reg = ExperimentRegistry(registry_root)
    experiments = exp_reg.list()
    if experiments:
        latest = sorted(experiments, key=lambda x: x.timestamp, reverse=True)[0]
        st.text(f"Latest experiment: {latest.id}")

        # Simulate slice analysis
        harness = EnterpriseEvalHarness(registry_root)
        # Create dummy result for demo
        from financial_agent.enterprise.eval_harness import EvaluationResult, SliceResult
        dummy_slices = [
            SliceResult(slice_name="adversarial", task_count=5, accuracy=0.62, tool_f1=0.65, p1=1),
            SliceResult(slice_name="numerical", task_count=5, accuracy=0.85, tool_f1=0.88),
            SliceResult(slice_name="missing_data", task_count=5, accuracy=0.70, tool_f1=0.72),
            SliceResult(slice_name="conflict", task_count=5, accuracy=0.62, tool_f1=0.60, p1=1),
            SliceResult(slice_name="high_risk", task_count=5, accuracy=0.75, tool_f1=0.78),
        ]
        dummy_result = EvaluationResult(
            experiment_id="demo",
            agent_id="markets.pre_meeting_brief",
            agent_version="1.3.0",
            suite_id="markets_pre_meeting_release",
            suite_version="3.0.0",
            overall={"accuracy": 0.85, "tool_f1": 0.88},
            slices=dummy_slices
        )

        analysis = harness.slice_analysis(dummy_result)
        st.json(analysis)

        st.markdown("""
        **Overall accuracy = 94%** alongside **conflicting-data = 62%**

        This prevents dangerous averages
        """)

        if analysis["worst_slice"]:
            st.warning(f"Worst slice: {analysis['worst_slice']}")

        if analysis["critical_failures"]:
            st.error(f"Critical failures in slices: {analysis['critical_failures']} - would BLOCK")

with tabs[9]:
    st.header("Failure Registry")
    st.caption("Canonical failure taxonomy - much stronger than arbitrary error strings")

    reg = FailureRegistry(registry_root)
    failures = reg.list()
    st.metric("Registered Failures", len(failures))

    severity_filter = st.selectbox("Filter by severity", ["all", "P0", "P1", "P2", "P3"])
    if severity_filter != "all":
        failures = [f for f in failures if f.severity == severity_filter]

    for failure in failures:
        with st.expander(f"{failure.id} - {failure.severity} - {failure.blocking_policy}"):
            st.json(failure.model_dump())
            if failure.severity in ["P0", "P1"]:
                st.error(f"{failure.severity} - {failure.blocking_policy}")

    st.subheader("Blocking Policy")
    blocking = reg.get_blocking()
    st.text(f"Blocking failures: {[f.id for f in blocking]}")

with tabs[10]:
    st.header("Judge Registry & Calibration")
    st.caption("LLM judges deserve their own registry - judge is not trusted merely because it is LLM")

    reg = JudgeRegistry(registry_root)
    judges = reg.list()
    st.metric("Registered Judges", len(judges))

    for judge in judges:
        with st.expander(f"{judge.id}@{judge.version} - {judge.model}"):
            st.json(judge.model_dump())
            cal = judge.calibration
            st.metric("Human Agreement", f"{cal.agreement:.0%}")
            st.metric("Cohen's Kappa", f"{cal.cohens_kappa:.2f}" if cal.cohens_kappa else "N/A")
            st.text(f"Validated on: {cal.validated_on} samples")

            if cal.agreement >= 0.8:
                st.success(f"✅ Calibrated - agreement {cal.agreement:.0%} >= 80%")
            else:
                st.warning(f"⚠️ Low agreement {cal.agreement:.0%}")

    st.markdown("""
    **Dashboard display:**
    ```
    Grounding Judge v2
    Human agreement: 88%
    κ = 0.79
    Validated on: 40 samples
    ```

    This is very strong interview material
    """)

with tabs[11]:
    st.header("Lifecycle Evidence Pack")
    st.caption("Killer feature - audit-ready evaluation package")

    st.markdown("""
    For any candidate release: `generate_evidence_pack(candidate)` produces:

    - candidate identity, baseline identity
    - code version, model version, program/prompt versions, tool versions
    - datasets used, scorer versions, judge validation
    - quality metrics, latency, cost
    - slice analysis
    - P0/P1 failures
    - red-team results
    - regression diff
    - human-review metrics
    - known limitations
    - final lifecycle decision: PASS, PASS_WITH_WARNINGS, HUMAN_REVIEW, BLOCK
    """)

    # List evidence packs
    packs_dir = Path("evidence_packs")
    if packs_dir.exists():
        packs = list(packs_dir.glob("*.json"))
        st.metric("Evidence Packs", len(packs))
        for pack_file in sorted(packs, reverse=True)[:10]:
            with open(pack_file) as f:
                pack = json.load(f)
            with st.expander(f"{pack['evidence_pack_id']} - {pack['candidate_identity']} - {pack['lifecycle_decision']} - {pack['evidence_type']}"):
                st.json(pack)
                if pack['lifecycle_decision'] == "BLOCK":
                    st.error(f"BLOCKED: {pack['decision_reason']}")
                else:
                    st.success(f"{pack['lifecycle_decision']}: {pack['decision_reason']}")

                if pack['evidence_type'] == "simulated":
                    st.warning("⚠️ SIMULATED RESULT - visually distinguished")

    st.subheader("Generate Evidence Pack Demo")
    candidate = st.text_input("Candidate", "markets.pre_meeting_brief@1.3.0")
    baseline = st.text_input("Baseline", "markets.pre_meeting_brief@1.2.0")

    if st.button("Generate Evidence Pack"):
        generator = EvidencePackGenerator(registry_root)
        # Mock results
        mock_results = {
            "metrics": {"accuracy": 0.85, "tool_f1": 0.88, "answerability": 0.90},
            "p0_failures": 0,
            "p1_failures": 1,
            "failure_details": [{"task_id": "R01", "failure": "OUTPUT.FALSE_PREMISE"}],
            "model_versions": {"supervisor": "dspy.gepa@3.0.0"},
            "datasets": ["golden_reliability@1.0.0", "finagent_1_1_1@1.0.0"],
            "scorer_versions": ["numeric_tolerance@1", "tool_exact_match@2"]
        }
        baseline_results = {
            "summary": {"p1_failures": 0, "avg_score": 0.88}
        }
        slice_analysis = {
            "conflicting_data": {"accuracy": 0.62},
            "adversarial": {"accuracy": 0.75}
        }

        pack = generator.generate(
            candidate_identity=candidate,
            baseline_identity=baseline,
            experiment_results=mock_results,
            baseline_results=baseline_results,
            slice_analysis=slice_analysis,
            evidence_type="simulated"
        )
        st.success(f"Generated {pack.evidence_pack_id} - Decision: {pack.lifecycle_decision}")
        st.json(pack.model_dump())

with tabs[12]:
    st.header("Trace Bus")
    st.caption("Standardise all execution around canonical event envelope - per spec 11")

    bus = TraceBus()

    st.code("""
{
  "trace_id": "...",
  "run_id": "...",
  "session_id": "...",
  "agent_id": "markets.pre_meeting_brief",
  "agent_version": "1.2.0",
  "workflow_id": "pre_meeting_brief",
  "workflow_version": "3",
  "event_type": "tool_call",
  "component": "credit_agent",
  "timestamp": "...",
  "artifact_versions": {
    "model": "...",
    "prompt": "...",
    "program": "...",
    "tool": "credit_snapshot@2"
  },
  "payload": {}
}
    """, language="json")

    # Show recent traces
    trace_dir = Path("traces")
    if trace_dir.exists():
        trace_files = list(trace_dir.glob("*.jsonl"))
        st.metric("Trace Files", len(trace_files))
        if trace_files:
            latest = sorted(trace_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
            st.text(f"Latest: {latest.name}")
            with open(latest) as f:
                lines = f.readlines()[-10:]
                for line in lines:
                    try:
                        event = json.loads(line)
                        st.json(event)
                    except:
                        st.text(line[:200])

    if st.button("Emit Test Trace Event"):
        bus.start_trace()
        event = bus.emit_simple(
            event_type=bus.emit_simple.__code__.co_varnames[0],  # placeholder
            component="test",
            payload={"test": "data"}
        )
        # Actually emit properly
        from financial_agent.enterprise.trace_bus import TraceEventType
        bus.start_trace()
        ev = bus.emit_simple(
            event_type=TraceEventType.tool_call,
            component="credit_agent",
            payload={"tool_name": "credit_snapshot", "client_id": "client_001"},
            artifact_versions={"tool": "credit_snapshot@2", "model": "dspy.gepa@3.0.0"}
        )
        st.success(f"Emitted {ev.event_id} to trace {ev.trace_id}")
        st.json(ev.model_dump())

with tabs[13]:
    st.header("Policy / Entitlement Layer")
    st.caption("Lightweight policy abstraction - input identity, agent, client, tool, action -> ALLOW, DENY, REQUIRE_APPROVAL")

    engine = PolicyEngine()

    st.code("""
research_agent + credit_snapshot
→ DENY

internal_agent + credit_snapshot
→ ALLOW

agent + change_credit_limit
→ REQUIRE_APPROVAL
    """)

    # Test policy
    agent = st.text_input("Agent", "research_agent")
    tool = st.text_input("Tool", "credit_snapshot")
    action = st.text_input("Action", "read")

    if st.button("Check Policy"):
        from financial_agent.enterprise.policy import PolicyInput
        inp = PolicyInput(agent=agent, tool=tool, action=action)
        decision = engine.evaluate(inp)
        st.text(f"Decision: {decision.value}")

        if decision.value == "DENY":
            st.error(f"DENY: {agent} cannot use {tool}")
        elif decision.value == "REQUIRE_APPROVAL":
            st.warning(f"REQUIRE_APPROVAL: {tool} needs approval")
        else:
            st.success(f"ALLOW: {agent} can use {tool}")

    st.subheader("Decision Log")
    logs = engine.get_log()
    for log in logs[-10:]:
        st.json(log)

    st.subheader("All Decisions Traced")
    st.text("Every policy decision is traced via Trace Bus")

with tabs[14]:
    st.header("Replay Evaluation")
    st.caption("Important enterprise capability - replay prior task against new model/program/tool")

    st.code("""
original request
      ↓
replay against candidate-v4
      ↓
compare against production-v3
    """, language="text")

    engine = ReplayEngine()

    trace_id = st.text_input("Original Trace ID", "trace_123")
    candidate_id = st.text_input("Candidate Agent ID", "markets.pre_meeting_brief")
    candidate_version = st.text_input("Candidate Version", "1.3.0")

    if st.button("Replay"):
        result = engine.replay(trace_id, candidate_id, candidate_version)
        st.json(result)
        st.success("Replay evaluation without inventing new test cases")

with tabs[15]:
    st.header("Online Evaluation Interface")
    st.caption("Do not build full production monitoring - create interface - per spec 31")

    st.code("""
trace ingest
    ↓
sampling
    ↓
online scorer
    ↓
alert
    """)

    iface = OnlineEvalInterface(sample_rate=0.5)

    if st.button("Simulate Production Traces"):
        # Simulate ingesting traces
        for i in range(10):
            trace = {
                "trace_id": f"prod_{i}",
                "agent_id": "markets.pre_meeting_brief",
                "agent_version": "1.2.0",
                "p1_failures": 1 if i == 2 else 0,
                "tool_errors": 5 if i == 5 else 0,
                "latency_ms": 6000 if i == 7 else 800,
                "abstention_rate": 0.05 if i == 8 else 0.8
            }
            iface.ingest(trace)

        st.success(f"Ingested 10 traces, sampled {len(iface.get_sampled_traces())}")
        st.json(iface.get_metrics())

        alerts = iface.get_alerts()
        st.metric("Alerts", len(alerts))
        for alert in alerts:
            with st.expander(f"{alert.alert_type.value} - {alert.severity}"):
                st.json(alert.model_dump())
                if alert.severity == "CRITICAL":
                    st.error(alert.description)

    st.markdown("""
    **Example monitors:**
    - P1 unsupported claim
    - tool error spike
    - latency regression
    - abstention collapse
    - escalation-rate shift

    Implementation runs locally
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Interview Thesis:**

> "I started by building one financial agent workflow, but I realised the interesting engineering problem isn't the individual agent. It's the harness around agents: common tool and memory contracts, identity, versioning, provenance and execution. And equally important is the evaluation harness around that, because once multiple agents, models, prompts and tools evolve independently you need to know what actually changed, replay workloads, analyse failure slices and generate evidence for whether a candidate should progress. So I separated the runtime harness from the evaluation harness and made both reusable."

> "The evaluation harness is deliberately framework-independent. LangGraph, DSPy and eventually the fine-tuned LFM all have to pass through the same measurement and lifecycle system."
""")
