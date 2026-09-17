"""
Tool Gateway - Maps to AgentCore Gateway
Enforces authz, logging, timeout, error semantics
"""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time
import uuid
from ..schemas.tools import ToolDefinition, ToolResult, ToolStatus, ToolCallLog
from ..schemas.tracing import TraceEvent, TraceEventType
from ..providers.internal_provider import InternalDataProvider
from ..providers.external_provider import ExternalResearchProvider

class ToolGateway:
    def __init__(self, internal_provider: InternalDataProvider, external_provider: ExternalResearchProvider):
        self.internal_provider = internal_provider
        self.external_provider = external_provider
        self.tool_definitions = self._build_definitions()
        self.call_logs: List[ToolCallLog] = []
        self.unauthorized_attempts: List[Dict] = []

        # Authz matrix: which agent can call which tool
        self.authz_matrix = {
            "internal_data": ["client_lookup", "relationship_summary", "credit_snapshot", "trade_activity", "gl_summary", "calculator"],
            "research": ["document_search", "document_fetch", "calculator", "table_extractor"],
            "analysis": ["calculator", "table_extractor", "client_lookup", "credit_snapshot", "trade_activity"],
            "supervisor": ["client_lookup"],
            "verifier": [],  # verifier does not call tools directly, it inspects outputs
            "synthesiser": [],
            "system": ["client_lookup", "relationship_summary", "credit_snapshot", "trade_activity", "gl_summary", "document_search", "document_fetch", "calculator", "table_extractor"]
        }

    def _build_definitions(self) -> Dict[str, ToolDefinition]:
        return {
            "client_lookup": ToolDefinition(
                name="client_lookup",
                description="Lookup client by name or ID",
                input_schema={"type": "object", "properties": {"client_name": {"type": "string"}, "client_id": {"type": "string"}}, "required": []},
                output_schema={"type": "object"},
                authorisation_scope=["internal_read", "crm_read"],
                timeout_seconds=5,
                is_authoritative=True,
                is_state_mutating=False
            ),
            "relationship_summary": ToolDefinition(
                name="relationship_summary",
                description="Get relationship overview for client",
                input_schema={"type": "object", "properties": {"client_id": {"type": "string"}}, "required": ["client_id"]},
                output_schema={"type": "object"},
                authorisation_scope=["internal_read", "crm_read"],
                timeout_seconds=5,
                is_authoritative=False,
                is_state_mutating=False
            ),
            "credit_snapshot": ToolDefinition(
                name="credit_snapshot",
                description="Get current credit exposure, limit, utilization",
                input_schema={"type": "object", "properties": {"client_id": {"type": "string"}}, "required": ["client_id"]},
                output_schema={"type": "object"},
                authorisation_scope=["internal_read", "credit_read"],
                timeout_seconds=5,
                is_authoritative=True,
                is_state_mutating=False
            ),
            "trade_activity": ToolDefinition(
                name="trade_activity",
                description="Get recent trading activity",
                input_schema={"type": "object", "properties": {"client_id": {"type": "string"}, "days": {"type": "integer"}}, "required": ["client_id"]},
                output_schema={"type": "object"},
                authorisation_scope=["internal_read", "trading_read"],
                timeout_seconds=5,
                is_authoritative=True,
                is_state_mutating=False
            ),
            "gl_summary": ToolDefinition(
                name="gl_summary",
                description="Get GL summary / balances",
                input_schema={"type": "object", "properties": {"client_id": {"type": "string"}}, "required": ["client_id"]},
                output_schema={"type": "object"},
                authorisation_scope=["internal_read", "gl_read"],
                timeout_seconds=5,
                is_authoritative=True,
                is_state_mutating=False
            ),
            "document_search": ToolDefinition(
                name="document_search",
                description="Search external financial documents (SEC filings, news)",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}}, "required": ["query"]},
                output_schema={"type": "object"},
                authorisation_scope=["external_read"],
                timeout_seconds=10,
                is_authoritative=False,
                is_state_mutating=False
            ),
            "document_fetch": ToolDefinition(
                name="document_fetch",
                description="Fetch document by ID",
                input_schema={"type": "object", "properties": {"document_id": {"type": "string"}}, "required": ["document_id"]},
                output_schema={"type": "object"},
                authorisation_scope=["external_read"],
                timeout_seconds=5,
                is_authoritative=False,
                is_state_mutating=False
            ),
            "calculator": ToolDefinition(
                name="calculator",
                description="Deterministic calculator for financial metrics",
                input_schema={"type": "object", "properties": {"expression": {"type": "string"}, "operation": {"type": "string"}}, "required": ["expression"]},
                output_schema={"type": "object"},
                authorisation_scope=["deterministic"],
                timeout_seconds=2,
                is_authoritative=False,
                is_state_mutating=False
            ),
            "table_extractor": ToolDefinition(
                name="table_extractor",
                description="Extract numeric table from text",
                input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
                output_schema={"type": "object"},
                authorisation_scope=["deterministic"],
                timeout_seconds=3,
                is_authoritative=False,
                is_state_mutating=False
            ),
        }

    def is_authorized(self, agent: str, tool_name: str) -> bool:
        allowed = self.authz_matrix.get(agent, [])
        # system can call all
        if agent == "system":
            return True
        return tool_name in allowed

    def call(self, tool_name: str, caller_agent: str, trace_id: str, tenant_id: str = "tenant_danske_mock", client_id: Optional[str] = None, **kwargs) -> ToolResult:
        start = time.time()
        # Auth check
        if not self.is_authorized(caller_agent, tool_name):
            self.unauthorized_attempts.append({
                "tool": tool_name,
                "caller": caller_agent,
                "timestamp": datetime.utcnow().isoformat(),
                "tenant_id": tenant_id
            })
            result = ToolResult(
                tool_name=tool_name,
                status=ToolStatus.auth_error,
                data=None,
                error_code="UNAUTHORIZED",
                error_message=f"Agent {caller_agent} not authorized to call {tool_name}"
            )
            # Log
            log = ToolCallLog(
                trace_id=trace_id,
                tool_name=tool_name,
                input=kwargs,
                caller_agent=caller_agent,
                result=result,
                latency_ms=int((time.time()-start)*1000),
                tenant_id=tenant_id,
                client_id=client_id
            )
            self.call_logs.append(log)
            return result

        # Dispatch - ensure client_id from explicit param is passed if not in kwargs
        # The gateway signature has tenant_id and client_id explicit for logging/isolation
        # but providers need client_id in kwargs, so inject if missing
        if client_id and "client_id" not in kwargs:
            kwargs["client_id"] = client_id

        try:
            if tool_name == "client_lookup":
                result = self.internal_provider.client_lookup(**kwargs)
            elif tool_name == "relationship_summary":
                result = self.internal_provider.relationship_summary(**kwargs)
            elif tool_name == "credit_snapshot":
                result = self.internal_provider.credit_snapshot(**kwargs)
            elif tool_name == "trade_activity":
                result = self.internal_provider.trade_activity(**kwargs)
            elif tool_name == "gl_summary":
                result = self.internal_provider.gl_summary(**kwargs)
            elif tool_name == "document_search":
                result = self.external_provider.search_tool_result(**kwargs)
            elif tool_name == "document_fetch":
                ev = self.external_provider.fetch(kwargs.get("document_id"))
                if ev:
                    from ..schemas.common import GovernanceMetadata
                    result = ToolResult(
                        tool_name=tool_name,
                        status=ToolStatus.success,
                        data=ev.model_dump(),
                        governance=ev.governance
                    )
                else:
                    result = ToolResult(
                        tool_name=tool_name,
                        status=ToolStatus.not_found,
                        data=None,
                        error_code="DOC_NOT_FOUND"
                    )
            elif tool_name == "calculator":
                result = self._calculator_tool(**kwargs)
            elif tool_name == "table_extractor":
                result = self._table_extractor_tool(**kwargs)
            else:
                result = ToolResult(
                    tool_name=tool_name,
                    status=ToolStatus.error,
                    data=None,
                    error_code="UNKNOWN_TOOL",
                    error_message=f"Unknown tool {tool_name}"
                )
        except Exception as e:
            result = ToolResult(
                tool_name=tool_name,
                status=ToolStatus.error,
                data=None,
                error_code="EXCEPTION",
                error_message=str(e)
            )

        latency_ms = int((time.time()-start)*1000)
        result.latency_ms = latency_ms

        log = ToolCallLog(
            trace_id=trace_id,
            tool_name=tool_name,
            input=kwargs,
            caller_agent=caller_agent,
            result=result,
            latency_ms=latency_ms,
            tenant_id=tenant_id,
            client_id=client_id
        )
        self.call_logs.append(log)
        return result

    def _calculator_tool(self, expression: str = "", operation: str = "eval", **kwargs) -> ToolResult:
        from ..schemas.common import GovernanceMetadata
        try:
            # Only allow safe eval
            allowed_chars = set("0123456789.+-*/()% ")
            if not all(c in allowed_chars for c in expression):
                # Try to parse percent change
                if "%" in expression or "change" in operation.lower():
                    # Simple percent change calc
                    import re
                    nums = re.findall(r"[-+]?\d*\.?\d+", expression)
                    if len(nums) >= 2:
                        old = float(nums[0])
                        new = float(nums[1])
                        if old != 0:
                            change = (new - old) / old * 100
                            return ToolResult(
                                tool_name="calculator",
                                status=ToolStatus.success,
                                data={"expression": expression, "result": change, "operation": "percent_change"},
                                governance=GovernanceMetadata(source="calculator", authoritative=False, permitted=True, provenance="deterministic calculator", retrieved_at=datetime.utcnow())
                            )
                raise ValueError("Invalid characters in expression")
            result = eval(expression, {"__builtins__": {}}, {})
            return ToolResult(
                tool_name="calculator",
                status=ToolStatus.success,
                data={"expression": expression, "result": result},
                governance=GovernanceMetadata(source="calculator", authoritative=False, permitted=True, provenance="deterministic calculator", retrieved_at=datetime.utcnow())
            )
        except Exception as e:
            return ToolResult(
                tool_name="calculator",
                status=ToolStatus.error,
                data=None,
                error_code="CALC_ERROR",
                error_message=str(e)
            )

    def _table_extractor_tool(self, text: str = "", **kwargs) -> ToolResult:
        from ..schemas.common import GovernanceMetadata
        import re
        # Simple extraction of numbers with context
        try:
            # Find patterns like "EBITDA DKK 420 million"
            pattern = r"([A-Za-z ]+)\s+DKK\s+([\d,\.]+)\s*(million|billion)?"
            matches = re.findall(pattern, text, re.IGNORECASE)
            extracted = [{"field": m[0].strip(), "value": m[1], "unit": m[2]} for m in matches]
            return ToolResult(
                tool_name="table_extractor",
                status=ToolStatus.success,
                data={"extracted": extracted, "text_snippet": text[:200]},
                governance=GovernanceMetadata(source="table_extractor", authoritative=False, permitted=True, provenance="deterministic extractor", retrieved_at=datetime.utcnow())
            )
        except Exception as e:
            return ToolResult(
                tool_name="table_extractor",
                status=ToolStatus.error,
                data=None,
                error_code="EXTRACT_ERROR",
                error_message=str(e)
            )

    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        return self.tool_definitions.get(tool_name)

    def list_tools(self) -> List[str]:
        return list(self.tool_definitions.keys())

    def clear_logs(self):
        self.call_logs.clear()
        self.unauthorized_attempts.clear()
