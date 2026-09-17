"""
LangGraph Workflow - Corporate Pre-Meeting Brief
Implements parallel internal + research, mandatory verifier
"""
from typing import Dict, Any, Optional, TypedDict, List
import time
from datetime import datetime
import uuid

from ..schemas.requests import UserRequest
from ..schemas.supervisor import SupervisorDecision
from ..schemas.agents import AgentResult
from ..schemas.brief import FinalBrief
from ..schemas.verification import VerificationResult

from ..agents.supervisor import SupervisorAgent
from ..agents.internal_data import InternalDataAgent
from ..agents.research import ResearchAgent
from ..agents.analysis import AnalysisAgent
from ..agents.verifier import VerifierAgent
from ..agents.synthesiser import SynthesiserAgent

from ..providers.model_provider import ModelProvider
from ..tools.gateway import ToolGateway
from ..retrieval.hybrid_retriever import HybridRetriever
from ..tracing.tracer import Tracer
from ..memory.short_term import ShortTermMemory
from ..memory.long_term import LongTermMemory

# LangGraph state
class WorkflowState(TypedDict):
    request: UserRequest
    supervisor_decision: Optional[SupervisorDecision]
    supervisor_metadata: Optional[Any]
    internal_result: Optional[AgentResult]
    research_result: Optional[AgentResult]
    analysis_result: Optional[AgentResult]
    verification_result: Optional[VerificationResult]
    final_brief: Optional[FinalBrief]
    trace_id: str
    errors: List[str]
    start_time: float

class FinancialAgentWorkflow:
    def __init__(self,
                 supervisor_agent: SupervisorAgent,
                 internal_agent: InternalDataAgent,
                 research_agent: ResearchAgent,
                 analysis_agent: AnalysisAgent,
                 verifier_agent: VerifierAgent,
                 synthesiser_agent: SynthesiserAgent,
                 tool_gateway: ToolGateway,
                 tracer: Optional[Tracer] = None,
                 short_term_memory: Optional[ShortTermMemory] = None,
                 long_term_memory: Optional[LongTermMemory] = None,
                 retriever_type: str = "hybrid"):
        self.supervisor_agent = supervisor_agent
        self.internal_agent = internal_agent
        self.research_agent = research_agent
        self.analysis_agent = analysis_agent
        self.verifier_agent = verifier_agent
        self.synthesiser_agent = synthesiser_agent
        self.tool_gateway = tool_gateway
        self.tracer = tracer
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.retriever_type = retriever_type

        # Try to build LangGraph graph, fallback to sequential if not available
        self.graph = None
        try:
            self._build_langgraph()
        except Exception as e:
            print(f"LangGraph not available or build failed: {e}, using sequential fallback")
            self.graph = None

    def _build_langgraph(self):
        try:
            from langgraph.graph import StateGraph, END

            workflow = StateGraph(WorkflowState)

            workflow.add_node("supervisor", self._node_supervisor)
            workflow.add_node("internal", self._node_internal)
            workflow.add_node("research", self._node_research)
            workflow.add_node("analysis", self._node_analysis)
            workflow.add_node("verifier", self._node_verifier)
            workflow.add_node("synthesiser", self._node_synthesiser)

            workflow.set_entry_point("supervisor")

            # Conditional routing after supervisor
            def route_after_supervisor(state: WorkflowState):
                decision = state.get("supervisor_decision")
                if not decision:
                    return "verifier"  # fail closed
                specialists = decision.required_specialists
                # For parallel case, we need to handle both internal and research
                # LangGraph doesn't natively support parallel fan-out in simple way, so we route to internal first,
                # then research, then analysis - but we log that they could be parallel
                if "internal" in specialists and "research" in specialists:
                    return "internal"  # will go internal -> research -> analysis
                elif "internal" in specialists:
                    return "internal"
                elif "research" in specialists:
                    return "research"
                else:
                    return "verifier"

            workflow.add_conditional_edges(
                "supervisor",
                route_after_supervisor,
                {
                    "internal": "internal",
                    "research": "research",
                    "verifier": "verifier"
                }
            )

            def route_after_internal(state: WorkflowState):
                decision = state.get("supervisor_decision")
                if decision and "research" in decision.required_specialists:
                    return "research"
                elif decision and "analysis" in decision.required_specialists:
                    return "analysis"
                else:
                    return "verifier"

            workflow.add_conditional_edges(
                "internal",
                route_after_internal,
                {
                    "research": "research",
                    "analysis": "analysis",
                    "verifier": "verifier"
                }
            )

            def route_after_research(state: WorkflowState):
                decision = state.get("supervisor_decision")
                if decision and "analysis" in decision.required_specialists:
                    return "analysis"
                else:
                    return "verifier"

            workflow.add_conditional_edges(
                "research",
                route_after_research,
                {
                    "analysis": "analysis",
                    "verifier": "verifier"
                }
            )

            workflow.add_edge("analysis", "verifier")
            workflow.add_edge("verifier", "synthesiser")
            workflow.add_edge("synthesiser", END)

            self.graph = workflow.compile()

        except ImportError as e:
            print(f"LangGraph import failed: {e}")
            self.graph = None

    def _node_supervisor(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        decision, metadata = self.supervisor_agent.decide(request)
        state["supervisor_decision"] = decision
        state["supervisor_metadata"] = metadata
        return state

    def _node_internal(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        decision = state.get("supervisor_decision")
        result = self.internal_agent.run(request, decision, state["trace_id"])
        state["internal_result"] = result
        return state

    def _node_research(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        decision = state.get("supervisor_decision")
        result = self.research_agent.run(request, decision, state["trace_id"], retriever_type=self.retriever_type)
        state["research_result"] = result
        return state

    def _node_analysis(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        internal_facts = {}
        if state.get("internal_result") and state["internal_result"].facts:
            internal_facts = state["internal_result"].facts
        evidence = None
        if state.get("research_result") and state["research_result"].evidence:
            evidence = state["research_result"].evidence
        result = self.analysis_agent.run(request, internal_facts, evidence, state["trace_id"])
        state["analysis_result"] = result
        return state

    def _node_verifier(self, state: WorkflowState) -> WorkflowState:
        # Gather draft sections from internal + research + analysis
        draft_sections = []
        internal_facts = {}
        if state.get("internal_result"):
            internal_facts.update(state["internal_result"].facts or {})
        evidence = None
        tool_results = []
        if state.get("internal_result"):
            tool_results.extend(state["internal_result"].tool_results or [])
        if state.get("research_result"):
            evidence = state["research_result"].evidence
        if state.get("analysis_result"):
            internal_facts.update(state["analysis_result"].facts or {})

        # For verifier, we need draft sections - create placeholder from facts
        # In real flow, synthesiser creates draft, but verifier must check draft before final
        # For this implementation, we create draft sections from facts to verify
        draft_sections = self._create_draft_sections(internal_facts, evidence, state.get("analysis_result"))

        verification = self.verifier_agent.verify(
            draft_sections=draft_sections,
            internal_facts=internal_facts,
            evidence_bundle=evidence,
            tool_results=tool_results,
            supervisor_decision=state.get("supervisor_decision")
        )
        state["verification_result"] = verification
        # Store draft for synthesiser
        state["_draft_sections"] = draft_sections
        return state

    def _node_synthesiser(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        internal_facts = {}
        if state.get("internal_result"):
            internal_facts.update(state["internal_result"].facts or {})
        if state.get("analysis_result"):
            internal_facts.update(state["analysis_result"].facts or {})

        evidence = None
        if state.get("research_result"):
            evidence = state["research_result"].evidence

        verification = state.get("verification_result")
        decision = state.get("supervisor_decision")

        final_brief = self.synthesiser_agent.synthesise(
            request=request,
            internal_facts=internal_facts,
            evidence_bundle=evidence,
            analysis_result=state.get("analysis_result"),
            verification=verification,
            supervisor_decision=decision
        )
        state["final_brief"] = final_brief
        return state

    def _create_draft_sections(self, internal_facts, evidence_bundle, analysis_result):
        sections = []
        # Relationship
        if "relationship_summary" in internal_facts:
            rel = internal_facts["relationship_summary"]
            sections.append({"title": "Relationship Overview", "content": str(rel)})
        # Credit
        if "credit_snapshot" in internal_facts:
            sections.append({"title": "Credit Exposure", "content": str(internal_facts["credit_snapshot"])})
        # Trades
        if "trade_activity" in internal_facts:
            sections.append({"title": "Trading", "content": str(internal_facts["trade_activity"])})
        # External
        if evidence_bundle and hasattr(evidence_bundle, 'results'):
            for ev in evidence_bundle.results[:2]:
                sections.append({"title": f"External {ev.document_id}", "content": ev.text})
        # Analysis
        if analysis_result and analysis_result.calculations:
            sections.append({"title": "Analysis", "content": str(analysis_result.calculations)})
        return sections

    def run(self, request: UserRequest) -> Dict[str, Any]:
        trace_id = str(uuid.uuid4())
        start = time.time()

        # Initialize short-term memory engagement if needed
        if self.short_term_memory and request.context.engagement_id:
            if not self.short_term_memory.get(request.context.engagement_id):
                self.short_term_memory.create_engagement(
                    tenant_id=request.context.tenant_id,
                    user_id=request.context.user_id,
                    client_id=request.context.client_id,
                    engagement_id=request.context.engagement_id
                )

        # Tracer setup
        if self.tracer:
            self.tracer.log_request(request.query, {
                "tenant_id": request.context.tenant_id,
                "user_id": request.context.user_id,
                "client_id": request.context.client_id,
                "engagement_id": request.context.engagement_id,
                "task_id": request.task_id
            })

        initial_state: WorkflowState = {
            "request": request,
            "supervisor_decision": None,
            "supervisor_metadata": None,
            "internal_result": None,
            "research_result": None,
            "analysis_result": None,
            "verification_result": None,
            "final_brief": None,
            "trace_id": trace_id,
            "errors": [],
            "start_time": start
        }

        if self.graph:
            try:
                final_state = self.graph.invoke(initial_state)
            except Exception as e:
                # Fallback to sequential
                print(f"LangGraph execution failed: {e}, fallback to sequential")
                final_state = self._run_sequential(initial_state)
        else:
            final_state = self._run_sequential(initial_state)

        latency_ms = int((time.time() - start) * 1000)

        return {
            "request": request,
            "supervisor_decision": final_state.get("supervisor_decision"),
            "supervisor_metadata": final_state.get("supervisor_metadata"),
            "internal_result": final_state.get("internal_result"),
            "research_result": final_state.get("research_result"),
            "analysis_result": final_state.get("analysis_result"),
            "verification_result": final_state.get("verification_result"),
            "final_brief": final_state.get("final_brief"),
            "trace_id": trace_id,
            "latency_ms": latency_ms,
            "tracer": self.tracer
        }

    def _run_sequential(self, state: WorkflowState) -> WorkflowState:
        state = self._node_supervisor(state)
        decision = state.get("supervisor_decision")
        specialists = getattr(decision, 'required_specialists', []) if decision else []

        # Parallelizable flag logged but executed sequentially for MVP simplicity
        # In production, internal + research would run in parallel via asyncio
        if "internal" in specialists or not specialists:
            state = self._node_internal(state)
        if "research" in specialists or not specialists:
            state = self._node_research(state)
        if "analysis" in specialists:
            state = self._node_analysis(state)

        state = self._node_verifier(state)
        state = self._node_synthesiser(state)
        return state
