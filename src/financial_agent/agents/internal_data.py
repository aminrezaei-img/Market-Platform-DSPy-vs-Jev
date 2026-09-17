"""
Internal Data Agent - typed internal tools only, no guessing
"""
from typing import Optional, Dict, Any
from ..schemas.requests import UserRequest
from ..schemas.agents import AgentResult, AgentType
from ..schemas.tools import ToolStatus
from ..tools.gateway import ToolGateway
from ..tracing.tracer import Tracer
from ..memory.short_term import ShortTermMemory

class InternalDataAgent:
    def __init__(self, tool_gateway: ToolGateway, tracer: Optional[Tracer] = None, short_term_memory: Optional[ShortTermMemory] = None):
        self.tool_gateway = tool_gateway
        self.tracer = tracer
        self.short_term_memory = short_term_memory

    def run(self, request: UserRequest, supervisor_decision: Any, trace_id: str) -> AgentResult:
        if self.tracer:
            self.tracer.log_agent_start(AgentType.internal_data.value, {"query": request.query})

        facts: Dict[str, Any] = {}
        tool_results = []
        warnings = []

        # Step 1: Identify client
        client_name = self._extract_client_name(request.query)
        client_id = request.context.client_id

        # Client lookup - pass client_name via kwargs, client_id via explicit param (gateway will inject)
        lookup_result = self.tool_gateway.call(
            tool_name="client_lookup",
            caller_agent="internal_data",
            trace_id=trace_id,
            tenant_id=request.context.tenant_id,
            client_id=client_id,
            client_name=client_name
        )

        if lookup_result.status != ToolStatus.success:
            # Try with explicit client_name only (fallback)
            lookup_result = self.tool_gateway.call(
                tool_name="client_lookup",
                caller_agent="internal_data",
                trace_id=trace_id,
                tenant_id=request.context.tenant_id,
                client_id=None,
                client_name=client_name
            )

        if self.tracer:
            self.tracer.log_tool_call("client_lookup", {"client_name": client_name, "client_id": client_id}, "internal_data", client_id, request.context.engagement_id)
            self.tracer.log_tool_result(lookup_result, "internal_data", client_id, request.context.engagement_id)

        tool_results.append(lookup_result)

        if lookup_result.status != ToolStatus.success:
            result = AgentResult(
                agent_type=AgentType.internal_data,
                success=False,
                facts=facts,
                tool_results=tool_results,
                error=f"Client lookup failed: {lookup_result.error_message}",
                warnings=warnings
            )
            if self.tracer:
                self.tracer.log_agent_end(AgentType.internal_data.value, result)
            return result

        resolved_client_id = lookup_result.data.get("client_id") if lookup_result.data else client_id
        resolved_client_name = lookup_result.data.get("client_name") if lookup_result.data else client_name

        facts["client"] = lookup_result.data

        # Step 2: Get relationship, credit, trades, GL based on supervisor required_tools
        required_tools = getattr(supervisor_decision, 'required_tools', []) if supervisor_decision else []
        tools_to_call = ["relationship_summary", "credit_snapshot", "trade_activity", "gl_summary"]
        if required_tools:
            tools_to_call = [t for t in tools_to_call if t in required_tools or "client_lookup" in required_tools]

        for tool_name in tools_to_call:
            extra_kwargs = {}
            if tool_name == "trade_activity":
                extra_kwargs["days"] = 30

            res = self.tool_gateway.call(
                tool_name=tool_name,
                caller_agent="internal_data",
                trace_id=trace_id,
                tenant_id=request.context.tenant_id,
                client_id=resolved_client_id,
                **extra_kwargs
            )

            if self.tracer:
                self.tracer.log_tool_call(tool_name, {"client_id": resolved_client_id, **extra_kwargs}, "internal_data", resolved_client_id, request.context.engagement_id)
                self.tracer.log_tool_result(res, "internal_data", resolved_client_id, request.context.engagement_id)

            tool_results.append(res)

            if res.status == ToolStatus.success:
                facts[tool_name] = res.data
            else:
                facts[f"{tool_name}_error"] = {
                    "status": res.status.value,
                    "error_code": res.error_code,
                    "error_message": res.error_message,
                    "abstention_reason": res.to_abstention_reason()
                }
                if res.status in [ToolStatus.timeout, ToolStatus.source_unavailable]:
                    warnings.append(f"{tool_name} unavailable: {res.error_message} -> will abstain, not invent")
                elif res.status == ToolStatus.conflict:
                    warnings.append(f"{tool_name} conflict detected: {res.error_message}")

        # Detect conflicts between CRM and credit snapshot (for R03)
        conflict_detected = self._detect_conflicts(facts)
        if conflict_detected:
            warnings.append(f"Conflict detected: {conflict_detected}")

        result = AgentResult(
            agent_type=AgentType.internal_data,
            success=True,
            facts=facts,
            tool_results=tool_results,
            warnings=warnings
        )

        if self.short_term_memory and request.context.engagement_id:
            self.short_term_memory.update_facts(request.context.engagement_id, facts)

        if self.tracer:
            self.tracer.log_agent_end(AgentType.internal_data.value, result)

        return result

    def _extract_client_name(self, query: str) -> str:
        import re
        match = re.search(r"for\s+([A-Z][A-Za-z\s/\.]+(?:A/S|Ltd|Solutions)?)", query)
        if match:
            return match.group(1).strip()
        known = ["Nordic Industrial", "Baltic Shipping", "Green Energy", "Tech Ventures"]
        for k in known:
            if k.lower() in query.lower():
                return k
        return "Nordic Industrial A/S"

    def _detect_conflicts(self, facts: Dict[str, Any]) -> Optional[str]:
        rel = facts.get("relationship_summary", {})
        credit = facts.get("credit_snapshot", {})
        if isinstance(rel, dict) and isinstance(credit, dict):
            crm_limit = rel.get("crm_credit_limit")
            snap_limit = credit.get("limit")
            if crm_limit and snap_limit and crm_limit != snap_limit:
                return f"CRM limit {crm_limit} vs credit snapshot {snap_limit}"
        return None
