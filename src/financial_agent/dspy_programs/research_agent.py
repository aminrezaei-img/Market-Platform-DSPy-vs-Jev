"""
DSPy Research Tool Agent - Phase 1.5
One genuine DSPy tool-using agent using ReAct
Wraps existing Tool Gateway, does NOT bypass gateway
"""
from typing import List, Optional
import dspy
from .signatures import ResearchWithTools
from .tool_adapter import DSPyToolAdapter
from ..tools.gateway import ToolGateway
from ..tracing.tracer import Tracer

class ResearchToolAgentPredict(dspy.Module):
    """
    Simple Predict version for research
    """
    def __init__(self):
        super().__init__()
        self.researcher = dspy.Predict(ResearchWithTools)

    def forward(self, question: str, company: str, context: str):
        return self.researcher(question=question, company=company, context=context)

class ResearchToolAgentReAct(dspy.Module):
    """
    DSPy ReAct agent with tools
    Tools: document_search, document_fetch, calculator
    Architecture:
    DSPy ReAct -> DSPy tool wrapper -> Existing Tool Gateway -> authz/schema/logging/provenance
    """
    def __init__(self, gateway: ToolGateway, trace_id: str = "dspy_react"):
        super().__init__()
        self.gateway = gateway
        self.trace_id = trace_id
        self.tool_adapter = DSPyToolAdapter(gateway, trace_id=trace_id)
        research_tools = self.tool_adapter.get_research_tools()

        # ReAct with tools - DSPy 3.x API
        self.react = dspy.ReAct(
            signature=ResearchWithTools,
            tools=research_tools
        )

    def forward(self, question: str, company: str, context: str):
        return self.react(question=question, company=company, context=context)

# Wrapper that integrates with Phase 1 workflow and tracing
class DSPyResearchAgentWrapper:
    """
    Wrapper that makes DSPy ReAct agent compatible with Phase 1 AgentResult and Tracer
    """
    def __init__(self, gateway: ToolGateway, tracer: Optional[Tracer] = None, program_type: str = "react"):
        self.gateway = gateway
        self.tracer = tracer
        self.program_type = program_type

        if program_type == "react":
            self.agent = ResearchToolAgentReAct(gateway, trace_id=tracer.trace_id if tracer else "dspy_react")
        else:
            self.agent = ResearchToolAgentPredict()

    def run(self, question: str, company: str, context: str = "") -> dict:
        if self.tracer:
            from ..schemas.tracing import TraceEventType
            self.tracer.log(
                event_type=TraceEventType.agent_start,
                agent="dspy_research",
                payload={"question": question, "company": company, "program_type": self.program_type}
            )

        try:
            result = self.agent(question=question, company=company, context=context)

            output = {
                "answer": getattr(result, 'answer', str(result)),
                "evidence_used": getattr(result, 'evidence_used', []),
                "tools_used": getattr(result, 'tools_used', []),
                "raw": result
            }

            if self.tracer:
                self.tracer.log(
                    event_type=TraceEventType.agent_end,
                    agent="dspy_research",
                    payload=output
                )

            return output
        except Exception as e:
            if self.tracer:
                self.tracer.log(
                    event_type=TraceEventType.error,
                    agent="dspy_research",
                    payload={"error": str(e)}
                )
            return {
                "answer": f"Research failed: {e}",
                "evidence_used": [],
                "tools_used": [],
                "error": str(e)
            }

# Mock for testing without API keys
def create_mock_research_agent(gateway: ToolGateway, tracer: Optional[Tracer] = None):
    """
    Mock that simulates tool trajectory without real LM
    Expected trajectory for "What was latest revenue and YoY % change?":
    document_search -> document_fetch -> calculator -> answer + evidence
    """
    class MockReAct:
        def __init__(self, gateway):
            self.gateway = gateway

        def __call__(self, question: str, company: str, context: str):
            # Simulate trajectory
            trace = []

            # Step 1: document_search
            search_result = self.gateway.call(
                tool_name="document_search",
                caller_agent="research",
                trace_id="mock_dspy",
                query=f"{company} revenue 2025"
            )
            trace.append(("document_search", search_result))

            # Step 2: document_fetch (fetch top result)
            if search_result.status.value == "success" and search_result.data:
                results = search_result.data.get("results", [])
                if results:
                    doc_id = results[0].get("document_id", "10K_2025_Nordic_Industrial")
                    fetch_result = self.gateway.call(
                        tool_name="document_fetch",
                        caller_agent="research",
                        trace_id="mock_dspy",
                        document_id=doc_id
                    )
                    trace.append(("document_fetch", fetch_result))

            # Step 3: calculator for YoY change
            calc_result = self.gateway.call(
                tool_name="calculator",
                caller_agent="research",
                trace_id="mock_dspy",
                expression="(2.4 - 2.22) / 2.22 * 100"
            )
            trace.append(("calculator", calc_result))

            # Build answer
            answer = f"{company} revenue 2025 DKK 2.4B, up 8% YoY (calculation: {calc_result.data.get('result', 8.1) if calc_result.data else 8}% from 2.22B in 2024). Evidence: 10K_2025_Nordic_Industrial"

            return dspy.Prediction(
                answer=answer,
                evidence_used=["10K_2025_Nordic_Industrial", "10K_2024_Nordic_Industrial"],
                tools_used=["document_search", "document_fetch", "calculator"]
            )

    return MockReAct(gateway)
