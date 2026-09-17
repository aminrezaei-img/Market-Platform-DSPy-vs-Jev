"""
Bootstrap registries with initial enterprise data - Phase 1E
"""
from .agent_registry import AgentRegistry, AgentManifest
from .workflow_registry import WorkflowRegistry, WorkflowManifest, WorkflowNode, WorkflowEdge
from .model_registry import ModelRegistry, ModelManifest
from .program_registry import ProgramRegistry, ProgramManifest
from .tool_registry import ToolRegistry, ToolManifest
from .dataset_registry import DatasetRegistry, DatasetManifest
from .suite_registry import SuiteRegistry, SuiteManifest
from .scorer_registry import ScorerRegistry, ScorerManifest
from .judge_registry import JudgeRegistry, JudgeManifest, JudgeCalibration
from .failure_registry import FailureRegistry, FailureManifest

def bootstrap_all(registry_root: str = "registry_store"):
    print("Bootstrapping enterprise registries...")

    # Agent Registry
    agent_reg = AgentRegistry(registry_root)
    agents = [
        AgentManifest(
            id="markets.pre_meeting_brief",
            version="1.0.0",
            owner="markets-ai",
            description="Pre-meeting brief v1 - rule-based supervisor",
            capabilities=["corporate_research", "internal_relationship_lookup", "financial_analysis"],
            workflow_id="pre_meeting_brief",
            workflow_version="1",
            model_policy={"supervisor": "rule_based@v1", "verifier": "mock@v1"},
            tool_policy={"allow": ["client_lookup", "relationship_summary", "credit_snapshot", "trade_activity", "document_search", "calculator"]},
            memory_policy={"short_term": "engagement", "long_term": "preferences_only"},
            eval_policy={"required_suite": "markets_pre_meeting_release@1"},
            input_contract={"request": "string", "client_id": "string"},
            output_contract={"brief": "string", "citations": "array", "conflicts": "array"},
            tags=["baseline", "rule_based", "measured"]
        ),
        AgentManifest(
            id="markets.pre_meeting_brief",
            version="1.2.0",
            owner="markets-ai",
            description="Pre-meeting brief v1.2 - cautious frontier",
            capabilities=["corporate_research", "internal_relationship_lookup", "financial_analysis"],
            workflow_id="pre_meeting_brief",
            workflow_version="3",
            model_policy={"supervisor": "anthropic.claude-3-5-sonnet@1", "verifier": "frontier-verifier@1"},
            tool_policy={"allow": ["client_lookup", "relationship_summary", "credit_snapshot", "trade_activity", "document_search", "calculator", "table_extractor"]},
            memory_policy={"short_term": "engagement", "long_term": "preferences_only"},
            eval_policy={"required_suite": "markets_pre_meeting_release@3"},
            input_contract={"request": "string", "client_id": "string"},
            output_contract={"brief": "string", "citations": "array", "conflicts": "array"},
            tags=["cautious", "frontier", "measured"]
        ),
        AgentManifest(
            id="markets.pre_meeting_brief",
            version="1.3.0",
            owner="markets-ai",
            description="Pre-meeting brief v1.3 - DSPy GEPA optimized",
            capabilities=["corporate_research", "internal_relationship_lookup", "financial_analysis", "dspy_program"],
            workflow_id="pre_meeting_brief",
            workflow_version="3",
            model_policy={"supervisor": "dspy.gepa@3", "verifier": "frontier-verifier@1"},
            tool_policy={"allow": ["client_lookup", "relationship_summary", "credit_snapshot", "trade_activity", "document_search", "calculator", "table_extractor", "document_fetch"]},
            memory_policy={"short_term": "engagement", "long_term": "preferences_only"},
            eval_policy={"required_suite": "markets_pre_meeting_release@3"},
            input_contract={"request": "string", "client_id": "string"},
            output_contract={"brief": "string", "citations": "array", "conflicts": "array"},
            tags=["dspy", "gepa", "optimized", "simulated"]
        ),
        AgentManifest(
            id="markets.credit_research",
            version="1.0.0",
            owner="credit-ai",
            description="Credit research agent",
            capabilities=["credit_analysis"],
            workflow_id="credit_research",
            workflow_version="1",
            model_policy={"supervisor": "rule_based@v1"},
            tool_policy={"allow": ["client_lookup", "credit_snapshot", "calculator"]},
            memory_policy={"short_term": "engagement", "long_term": "preferences_only"},
            eval_policy={"required_suite": "credit_release@1"},
            tags=["credit", "measured"]
        ),
    ]
    for agent in agents:
        agent_reg.register(agent)
    print(f"  Agents: {len(agents)}")

    # Workflow Registry
    wf_reg = WorkflowRegistry(registry_root)
    workflows = [
        WorkflowManifest(
            id="pre_meeting_brief",
            version="1",
            owner="markets-ai",
            description="Pre-meeting brief v1 - simple sequential",
            nodes=[
                WorkflowNode(id="supervisor", type="router", agent_version="rule_based@v1"),
                WorkflowNode(id="internal_data", type="agent", agent_version="internal@v1", tool_requirements=["client_lookup", "credit_snapshot"]),
                WorkflowNode(id="research", type="agent", agent_version="research@v1", tool_requirements=["document_search"]),
                WorkflowNode(id="verifier", type="verifier", agent_version="verifier@v1"),
                WorkflowNode(id="synthesiser", type="synthesiser", agent_version="synthesiser@v1"),
            ],
            edges=[
                WorkflowEdge(from_node="supervisor", to_node="internal_data"),
                WorkflowEdge(from_node="internal_data", to_node="research"),
                WorkflowEdge(from_node="research", to_node="verifier"),
                WorkflowEdge(from_node="verifier", to_node="synthesiser"),
            ],
            parallel_branches=[],
            tool_requirements=["client_lookup", "credit_snapshot", "document_search"],
            memory_requirements={"short_term": "engagement", "long_term": "preferences_only"},
            failure_policy="fail_closed",
            framework="langgraph"
        ),
        WorkflowManifest(
            id="pre_meeting_brief",
            version="3",
            owner="markets-ai",
            description="Pre-meeting brief v3 - parallel branches, DSPy programs",
            nodes=[
                WorkflowNode(id="supervisor", type="router", agent_version="dspy.gepa@3"),
                WorkflowNode(id="internal_data", type="agent", agent_version="internal@v2", tool_requirements=["client_lookup", "credit_snapshot", "trade_activity"]),
                WorkflowNode(id="research", type="agent", agent_version="research@v2", tool_requirements=["document_search", "document_fetch"]),
                WorkflowNode(id="analysis", type="agent", agent_version="analysis@v1", tool_requirements=["calculator", "table_extractor"]),
                WorkflowNode(id="verifier", type="verifier", agent_version="verifier@v2"),
                WorkflowNode(id="synthesiser", type="synthesiser", agent_version="synthesiser@v2"),
            ],
            edges=[
                WorkflowEdge(from_node="supervisor", to_node="internal_data"),
                WorkflowEdge(from_node="supervisor", to_node="research"),
                WorkflowEdge(from_node="internal_data", to_node="analysis"),
                WorkflowEdge(from_node="research", to_node="analysis"),
                WorkflowEdge(from_node="analysis", to_node="verifier"),
                WorkflowEdge(from_node="verifier", to_node="synthesiser"),
            ],
            parallel_branches=[["internal_data", "research"]],
            tool_requirements=["client_lookup", "credit_snapshot", "trade_activity", "document_search", "calculator"],
            memory_requirements={"short_term": "engagement", "long_term": "preferences_only"},
            failure_policy="fail_closed",
            framework="langgraph"
        ),
        WorkflowManifest(
            id="credit_research",
            version="1",
            owner="credit-ai",
            description="Credit research workflow",
            nodes=[
                WorkflowNode(id="supervisor", type="router"),
                WorkflowNode(id="credit_agent", type="agent", tool_requirements=["credit_snapshot", "client_lookup"]),
                WorkflowNode(id="analysis", type="agent", tool_requirements=["calculator"]),
            ],
            edges=[
                WorkflowEdge(from_node="supervisor", to_node="credit_agent"),
                WorkflowEdge(from_node="credit_agent", to_node="analysis"),
            ],
            tool_requirements=["credit_snapshot", "client_lookup", "calculator"],
            framework="langgraph"
        ),
    ]
    for wf in workflows:
        wf_reg.register(wf)
    print(f"  Workflows: {len(workflows)}")

    # Model Registry
    model_reg = ModelRegistry(registry_root)
    models = [
        ModelManifest(
            id="mock.testing",
            version="1.0.0",
            provider="mock",
            model_id="mock-supervisor-v1",
            model_family="mock",
            context_window=8192,
            deployment="local",
            cost_metadata={"input_per_1k": 0, "output_per_1k": 0},
            capabilities=["tool_use"],
            description="Mock model for testing"
        ),
        ModelManifest(
            id="anthropic.claude-3-5-sonnet",
            version="1.0.0",
            provider="anthropic",
            model_id="claude-3-5-sonnet-20241022",
            model_family="claude",
            context_window=200000,
            deployment="bedrock",
            cost_metadata={"input_per_1k": 0.003, "output_per_1k": 0.015},
            capabilities=["reasoning", "tool_use", "vision"],
            description="Claude 3.5 Sonnet"
        ),
        ModelManifest(
            id="openai.gpt-4o",
            version="1.0.0",
            provider="openai",
            model_id="gpt-4o",
            model_family="gpt",
            context_window=128000,
            deployment="api",
            cost_metadata={"input_per_1k": 0.005, "output_per_1k": 0.015},
            capabilities=["reasoning", "tool_use"],
            description="GPT-4o"
        ),
        ModelManifest(
            id="local.lfm2.5-1.2b",
            version="1.0.0",
            provider="local",
            model_id="LFM2.5-1.2B-Instruct",
            model_family="lfm",
            context_window=8192,
            deployment="local",
            cost_metadata={"input_per_1k": 0.0001, "output_per_1k": 0.0001},
            capabilities=["tool_use"],
            description="LFM2.5 1.2B - Phase 2 placeholder"
        ),
        ModelManifest(
            id="dspy.predict",
            version="1.0.0",
            provider="dspy",
            model_id="query_planner_predict",
            model_family="dspy",
            context_window=8192,
            deployment="local",
            cost_metadata={"input_per_1k": 0, "output_per_1k": 0},
            capabilities=["routing", "tool_selection"],
            description="DSPy Predict program"
        ),
        ModelManifest(
            id="dspy.gepa",
            version="3.0.0",
            provider="dspy",
            model_id="query_planner_gepa",
            model_family="dspy",
            context_window=8192,
            deployment="local",
            cost_metadata={"input_per_1k": 0, "output_per_1k": 0},
            capabilities=["routing", "tool_selection", "optimized"],
            description="DSPy GEPA optimized program"
        ),
    ]
    for model in models:
        model_reg.register(model)
    print(f"  Models: {len(models)}")

    # Program Registry
    prog_reg = ProgramRegistry(registry_root)
    programs = [
        ProgramManifest(
            id="query_planner",
            version="1.0.0",
            dspy_signature="DecomposeBankerRequest",
            dspy_module="Predict",
            optimizer="none",
            parent_program=None,
            training_dataset=None,
            artifact_path="artifacts/dspy/baseline/query_planner_predict.json",
            dspy_version="3.3.1",
            lm_model="mock.testing@1.0.0",
            evidence_type="measured",
            lineage=[],
            description="Baseline Predict"
        ),
        ProgramManifest(
            id="query_planner",
            version="2.0.0",
            dspy_signature="DecomposeBankerRequest",
            dspy_module="ChainOfThought",
            optimizer="none",
            parent_program="query_planner@1.0.0",
            artifact_path="artifacts/dspy/cot/query_planner_cot.json",
            dspy_version="3.3.1",
            lm_model="mock.testing@1.0.0",
            evidence_type="measured",
            lineage=["query_planner@1.0.0"],
            description="ChainOfThought"
        ),
        ProgramManifest(
            id="query_planner",
            version="2.1.0",
            dspy_signature="DecomposeBankerRequest",
            dspy_module="Predict",
            optimizer="MIPROv2",
            optimizer_run="mipro_run_018",
            parent_program="query_planner@1.0.0",
            training_dataset="dspy_control_train@1",
            artifact_path="artifacts/dspy/mipro/query_planner_predict_mipro.json",
            dspy_version="3.3.1",
            lm_model="mock.testing@1.0.0",
            evidence_type="simulated",
            lineage=["query_planner@1.0.0"],
            description="MIPROv2 optimized",
            optimizer_provenance={"auto": "light", "num_trials": 5, "train_size": 36}
        ),
        ProgramManifest(
            id="query_planner",
            version="3.0.0",
            dspy_signature="DecomposeBankerRequest",
            dspy_module="Predict",
            optimizer="GEPA",
            optimizer_run="gepa_run_027",
            parent_program="query_planner@2.1.0",
            training_dataset="dspy_control_train@1",
            artifact_path="artifacts/dspy/gepa/query_planner_predict_gepa.json",
            dspy_version="3.3.1",
            lm_model="mock.testing@1.0.0",
            evidence_type="simulated",
            lineage=["query_planner@1.0.0", "query_planner@2.1.0"],
            description="GEPA optimized with feedback",
            optimizer_provenance={"auto": "light", "feedback": "treated missing as zero rather than unavailable"}
        ),
    ]
    for prog in programs:
        prog_reg.register(prog)
    print(f"  Programs: {len(programs)}")

    # Tool Registry
    tool_reg = ToolRegistry(registry_root)
    tools = [
        ToolManifest(
            id="client_lookup",
            version="2.0.0",
            description="Lookup client in CRM",
            input_schema={"client_id": "string"},
            output_schema={"client": "object"},
            owner="crm-team",
            authoritative=True,
            state_mutating=False,
            timeout_ms=2000,
            data_classification="confidential",
            authorisation_policy={"allowed_capabilities": ["internal_relationship_lookup", "corporate_research"]}
        ),
        ToolManifest(
            id="credit_snapshot",
            version="2.0.0",
            description="Get credit exposure snapshot",
            input_schema={"client_id": "string"},
            output_schema={"exposure": "number", "limit": "number"},
            owner="credit-team",
            authoritative=True,
            state_mutating=False,
            timeout_ms=3000,
            data_classification="restricted",
            authorisation_policy={"allowed_capabilities": ["internal_relationship_lookup", "credit_analysis"]}
        ),
        ToolManifest(
            id="trade_activity",
            version="1.0.0",
            description="Get trading activity",
            input_schema={"client_id": "string"},
            output_schema={"trades": "array"},
            owner="trading-team",
            authoritative=True,
            state_mutating=False,
            timeout_ms=2000,
            data_classification="confidential"
        ),
        ToolManifest(
            id="document_search",
            version="2.0.0",
            description="Search SEC filings and external docs",
            input_schema={"query": "string"},
            output_schema={"documents": "array"},
            owner="research-team",
            authoritative=False,
            state_mutating=False,
            timeout_ms=5000,
            data_classification="public",
            authorisation_policy={"allow_all": True}
        ),
        ToolManifest(
            id="document_fetch",
            version="1.0.0",
            description="Fetch document content",
            input_schema={"doc_id": "string"},
            output_schema={"content": "string"},
            owner="research-team",
            authoritative=False,
            state_mutating=False,
            timeout_ms=3000,
            data_classification="public"
        ),
        ToolManifest(
            id="calculator",
            version="1.0.0",
            description="Deterministic calculator",
            input_schema={"expression": "string"},
            output_schema={"result": "number"},
            owner="platform",
            authoritative=False,
            state_mutating=False,
            timeout_ms=1000,
            data_classification="internal"
        ),
        ToolManifest(
            id="change_credit_limit",
            version="1.0.0",
            description="Change credit limit - requires approval",
            input_schema={"client_id": "string", "new_limit": "number"},
            output_schema={"status": "string"},
            owner="credit-team",
            authoritative=False,
            state_mutating=True,
            timeout_ms=5000,
            data_classification="restricted",
            authorisation_policy={"allowed_capabilities": ["credit_admin"]}
        ),
    ]
    for tool in tools:
        tool_reg.register(tool)
    print(f"  Tools: {len(tools)}")

    # Dataset Registry
    ds_reg = DatasetRegistry(registry_root)
    datasets = [
        DatasetManifest(
            id="golden_reliability",
            version="1.0.0",
            source="internal",
            licence="internal",
            task_count=18,
            task_families=["false_premise", "missing_data", "conflict", "timeout", "injection", "privacy"],
            intended_use="evaluation",
            training_allowed=False,
            evaluation_only=True,
            content_hash="golden_v1_hash",
            path="data/golden_suite/",
            description="6 canonical R01-R06 + 12 additional"
        ),
        DatasetManifest(
            id="finagent_1_1_1",
            version="1.0.0",
            source="finagent",
            licence="mit",
            task_count=20,
            task_families=["numerical", "adversarial", "false_premise", "unanswerable"],
            intended_use="evaluation",
            training_allowed=False,
            evaluation_only=True,
            content_hash="finagent_1_1_1_hash",
            path="data/finagent/",
            description="FinAgent mock subset, never for fine-tuning"
        ),
        DatasetManifest(
            id="dspy_control_holdout",
            version="1.0.0",
            source="synthetic",
            licence="internal",
            task_count=12,
            task_families=["credit_lookup", "ambiguous", "external_research", "conflict_check"],
            intended_use="evaluation",
            training_allowed=False,
            evaluation_only=True,
            content_hash="dspy_holdout_v1",
            path="data/dspy_optimization.json",
            description="DSPy control holdout 20%"
        ),
        DatasetManifest(
            id="dspy_control_train",
            version="1.0.0",
            source="synthetic",
            licence="internal",
            task_count=36,
            task_families=["credit_lookup", "ambiguous", "external_research"],
            intended_use="training",
            training_allowed=True,
            evaluation_only=False,
            content_hash="dspy_train_v1",
            path="data/dspy_optimization.json",
            description="DSPy control train 60%"
        ),
        DatasetManifest(
            id="tau_control_future",
            version="0.1.0",
            source="tau",
            licence="internal",
            task_count=0,
            task_families=[],
            intended_use="training",
            training_allowed=True,
            evaluation_only=False,
            content_hash="future",
            path="",
            description="Future Tau control - not yet implemented",
            tags=["future", "phase2"]
        ),
    ]
    for ds in datasets:
        ds_reg.register(ds)
    print(f"  Datasets: {len(datasets)}")

    # Suite Registry
    suite_reg = SuiteRegistry(registry_root)
    suites = [
        SuiteManifest(
            id="markets_pre_meeting_release",
            version="1.0.0",
            datasets=["golden_reliability@1.0.0"],
            metrics=["financial_correctness", "tool_accuracy", "abstention"],
            slices=["adversarial", "missing_data", "conflict"],
            lifecycle_policy={"p0_max": 0, "p1_max": 0},
            description="Initial release suite - golden only"
        ),
        SuiteManifest(
            id="markets_pre_meeting_release",
            version="3.0.0",
            datasets=["golden_reliability@1.0.0", "finagent_1_1_1@1.0.0", "dspy_control_holdout@1.0.0"],
            metrics=["financial_correctness", "evidence_recall", "tool_accuracy", "abstention", "grounding", "workflow_success", "escalation"],
            slices=["adversarial", "numerical", "missing_data", "conflict", "high_risk", "tool-required", "human-review"],
            lifecycle_policy={"p0_max": 0, "p1_max": 0},
            description="Full release suite with FinAgent and DSPy holdout"
        ),
        SuiteManifest(
            id="credit_release",
            version="1.0.0",
            datasets=["golden_reliability@1.0.0"],
            metrics=["financial_correctness", "tool_accuracy"],
            slices=["numerical", "missing_data"],
            lifecycle_policy={"p0_max": 0, "p1_max": 0},
            description="Credit research release"
        ),
    ]
    for suite in suites:
        suite_reg.register(suite)
    print(f"  Suites: {len(suites)}")

    # Scorer Registry
    scorer_reg = ScorerRegistry(registry_root)
    scorers = [
        ScorerManifest(id="numeric_tolerance", version="1.0.0", description="Numeric tolerance scorer", scorer_type="deterministic", tags=["financial_correctness"]),
        ScorerManifest(id="tool_exact_match", version="2.0.0", description="Tool exact match", scorer_type="deterministic", tags=["tool_accuracy"]),
        ScorerManifest(id="citation_support", version="1.0.0", description="Citation support checker", scorer_type="deterministic", tags=["grounding"]),
        ScorerManifest(id="abstention", version="3.0.0", description="Abstention precision/recall", scorer_type="deterministic", tags=["abstention"]),
        ScorerManifest(id="workflow_completion", version="1.0.0", description="Workflow sections present", scorer_type="deterministic", tags=["workflow_success"]),
        ScorerManifest(id="llm_grounding_judge", version="2.0.0", description="LLM grounding judge", scorer_type="llm_judge", calibration_dataset="grounding_calibration@1", tags=["grounding"]),
    ]
    for scorer in scorers:
        scorer_reg.register(scorer)
    print(f"  Scorers: {len(scorers)}")

    # Judge Registry
    judge_reg = JudgeRegistry(registry_root)
    judges = [
        JudgeManifest(
            id="grounding_judge",
            version="2.0.0",
            model="anthropic.claude-3-5-sonnet@1.0.0",
            prompt="Check if claim is supported by evidence...",
            rubric="Supported, Partially Supported, Unsupported",
            description="Grounding judge v2",
            calibration=JudgeCalibration(
                agreement=0.88,
                precision=0.85,
                recall=0.90,
                cohens_kappa=0.79,
                validated_on=40,
                calibration_dataset="grounding_human_labels@1",
                last_calibrated="2026-09-15"
            ),
            tags=["grounding", "calibrated"]
        ),
        JudgeManifest(
            id="financial_correctness_judge",
            version="1.0.0",
            model="mock.testing@1.0.0",
            prompt="Check financial correctness...",
            rubric="Correct, Incorrect",
            description="Financial correctness judge",
            calibration=JudgeCalibration(
                agreement=0.92,
                precision=0.90,
                recall=0.94,
                cohens_kappa=0.85,
                validated_on=30,
                calibration_dataset="financial_human_labels@1"
            ),
            tags=["financial_correctness"]
        ),
    ]
    for judge in judges:
        judge_reg.register(judge)
    print(f"  Judges: {len(judges)}")

    # Failure Registry
    failure_reg = FailureRegistry(registry_root)
    failures = [
        FailureManifest(id="SEC.PRIVACY.CROSS_CLIENT", version="1.0.0", description="Cross-client memory leak", category="privacy", severity="P0", blocking_policy="BLOCK", detection_method="memory isolation test", remediation="Fix namespace isolation"),
        FailureManifest(id="TOOL.AUTH.UNAUTHORISED", version="1.0.0", description="Unauthorised tool access", category="tool", severity="P0", blocking_policy="BLOCK", detection_method="policy engine check", remediation="Fix tool policy"),
        FailureManifest(id="DATA.MISSING.AUTHORITATIVE", version="1.0.0", description="Missing authoritative data treated as zero", category="data", severity="P1", blocking_policy="BLOCK", detection_method="check SOURCE_UNAVAILABLE transformed to 0", remediation="Surface as unavailable"),
        FailureManifest(id="DATA.CONFLICT", version="1.0.0", description="Conflicting sources not detected", category="data", severity="P1", blocking_policy="BLOCK", detection_method="conflict check", remediation="Surface conflict and require human review"),
        FailureManifest(id="RETRIEVAL.MISSED_EVIDENCE", version="1.0.0", description="Missed gold evidence", category="retrieval", severity="P2", blocking_policy="WARNING", detection_method="recall@k"),
        FailureManifest(id="AGENT.WRONG_ROUTE", version="1.0.0", description="Wrong agent routing", category="agent", severity="P2", blocking_policy="WARNING"),
        FailureManifest(id="OUTPUT.UNSUPPORTED_CLAIM", version="1.0.0", description="Unsupported financial claim", category="output", severity="P1", blocking_policy="BLOCK", detection_method="citation support scorer"),
        FailureManifest(id="OUTPUT.FALSE_PREMISE", version="1.0.0", description="False premise not detected", category="output", severity="P1", blocking_policy="BLOCK", detection_method="abstention scorer"),
        FailureManifest(id="HITL.MISSED_ESCALATION", version="1.0.0", description="Missed human escalation", category="hitl", severity="P1", blocking_policy="BLOCK"),
        FailureManifest(id="OPS.TIMEOUT", version="1.0.0", description="Tool timeout", category="ops", severity="P2", blocking_policy="WARNING"),
    ]
    for failure in failures:
        failure_reg.register(failure)
    print(f"  Failures: {len(failures)}")

    print("Bootstrap complete!")
    return {
        "agents": len(agents),
        "workflows": len(workflows),
        "models": len(models),
        "programs": len(programs),
        "tools": len(tools),
        "datasets": len(datasets),
        "suites": len(suites),
        "scorers": len(scorers),
        "judges": len(judges),
        "failures": len(failures)
    }
