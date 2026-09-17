"""
Analysis Agent - deterministic calculations, compare values
"""
from typing import Optional, Dict, Any, List
from ..schemas.requests import UserRequest
from ..schemas.agents import AgentResult, AgentType
from ..tools.gateway import ToolGateway
from ..tracing.tracer import Tracer

class AnalysisAgent:
    def __init__(self, tool_gateway: ToolGateway, tracer: Optional[Tracer] = None):
        self.tool_gateway = tool_gateway
        self.tracer = tracer

    def run(self, request: UserRequest, internal_facts: Dict[str, Any], evidence_bundle: Any, trace_id: str) -> AgentResult:
        if self.tracer:
            self.tracer.log_agent_start(AgentType.analysis.value, {"query": request.query})

        calculations = []
        warnings = []
        facts = {}

        # Example calculations for demo
        try:
            # 1. Calculate utilization if credit data available
            credit = internal_facts.get("credit_snapshot", {})
            if isinstance(credit, dict) and credit.get("exposure") and credit.get("limit"):
                exposure = credit["exposure"]
                limit = credit["limit"]
                # Use calculator tool
                calc_res = self.tool_gateway.call(
                    tool_name="calculator",
                    caller_agent="analysis",
                    trace_id=trace_id,
                    expression=f"{exposure} / {limit} * 100"
                )
                if self.tracer:
                    self.tracer.log_tool_call("calculator", {"expression": f"{exposure} / {limit} * 100"}, "analysis")
                    self.tracer.log_tool_result(calc_res, "analysis")

                if calc_res.is_success():
                    calculations.append({
                        "operation": "utilization_pct",
                        "expression": f"{exposure} / {limit} * 100",
                        "result": calc_res.data["result"],
                        "source": "credit_snapshot"
                    })
                    facts["calculated_utilization"] = calc_res.data["result"]

            # 2. EBITDA change calculation from external docs if available
            if evidence_bundle and hasattr(evidence_bundle, 'results'):
                for ev in evidence_bundle.results:
                    if "ebitda" in ev.text.lower() and "increase" in ev.text.lower():
                        # Extract numbers via table_extractor tool
                        extract_res = self.tool_gateway.call(
                            tool_name="table_extractor",
                            caller_agent="analysis",
                            trace_id=trace_id,
                            text=ev.text
                        )
                        if self.tracer:
                            self.tracer.log_tool_call("table_extractor", {"text": ev.text[:100]}, "analysis")
                            self.tracer.log_tool_result(extract_res, "analysis")

                        if extract_res.is_success():
                            calculations.append({
                                "operation": "table_extraction",
                                "source_doc": ev.document_id,
                                "result": extract_res.data
                            })

            # 3. Revenue growth
            gl = internal_facts.get("gl_summary", {})
            if isinstance(gl, dict) and gl.get("revenue_ytd"):
                facts["revenue_ytd"] = gl["revenue_ytd"]

        except Exception as e:
            warnings.append(f"Analysis calculation error: {e}")
            if self.tracer:
                self.tracer.log_error(f"Analysis agent error: {e}", agent="analysis")

        result = AgentResult(
            agent_type=AgentType.analysis,
            success=True,
            facts=facts,
            calculations=calculations,
            warnings=warnings
        )

        if self.tracer:
            self.tracer.log_agent_end(AgentType.analysis.value, result)

        return result
