"""
DSPy Tool Adapter - Phase 1.5
Wraps existing Tool Gateway functions, does NOT bypass gateway
Architecture:
DSPy ReAct -> DSPy tool wrapper -> Existing Tool Gateway -> authz/schema/logging/provenance
"""
from typing import List, Dict, Any, Callable, Optional
import dspy
from ..tools.gateway import ToolGateway
from ..schemas.tools import ToolStatus

class DSPyToolWrapper:
    """
    Wraps a single Tool Gateway tool as a DSPy tool for ReAct
    """
    def __init__(self, tool_name: str, gateway: ToolGateway, caller_agent: str = "research", trace_id: str = "dspy_trace"):
        self.tool_name = tool_name
        self.gateway = gateway
        self.caller_agent = caller_agent
        self.trace_id = trace_id
        self.definition = gateway.get_tool_definition(tool_name)

    def __call__(self, **kwargs) -> str:
        """
        Called by DSPy ReAct - must return string for LM
        """
        try:
            # Call through gateway (preserves authz, logging, provenance)
            result = self.gateway.call(
                tool_name=self.tool_name,
                caller_agent=self.caller_agent,
                trace_id=self.trace_id,
                **kwargs
            )

            if result.status == ToolStatus.success:
                # Return data as string for LM, but preserve provenance in gateway logs
                return f"SUCCESS: {result.data}"
            else:
                # Surface failure as data, not exception - agent must handle abstention
                return f"FAILED [{result.status.value}]: {result.error_code} - {result.error_message}. Must abstain, not invent. Reason: {result.to_abstention_reason()}"
        except Exception as e:
            return f"ERROR: {e}"

    def to_dspy_tool(self):
        """
        Convert to dspy.Tool for ReAct
        """
        # DSPy Tool needs name, desc, args, func
        desc = self.definition.description if self.definition else f"Tool {self.tool_name}"
        # Create a function with proper signature for DSPy
        # For simplicity, we use a generic wrapper and let DSPy infer args from docstring

        def tool_func(**kwargs):
            return self.__call__(**kwargs)

        tool_func.__name__ = self.tool_name
        tool_func.__doc__ = f"{desc}. Input: {self.definition.input_schema if self.definition else {}}"

        return dspy.Tool(
            name=self.tool_name,
            desc=desc,
            args=self.definition.input_schema if self.definition else {},
            func=tool_func
        )

class DSPyToolAdapter:
    """
    Provides restricted tool sets for DSPy agents, preserving Phase 1 permission isolation
    """
    def __init__(self, gateway: ToolGateway, trace_id: str = "dspy_trace"):
        self.gateway = gateway
        self.trace_id = trace_id

    def get_research_tools(self) -> List[dspy.Tool]:
        """
        Research DSPy agent receives only:
        document_search, document_fetch, calculator
        Does NOT receive credit_snapshot, trade_activity, gl_summary
        """
        allowed = ["document_search", "document_fetch", "calculator", "table_extractor"]
        tools = []
        for tool_name in allowed:
            if tool_name in self.gateway.list_tools():
                wrapper = DSPyToolWrapper(tool_name, self.gateway, caller_agent="research", trace_id=self.trace_id)
                tools.append(wrapper.to_dspy_tool())
        return tools

    def get_internal_tools(self) -> List[dspy.Tool]:
        """
        Internal DSPy agent (if implemented) receives its own restricted set
        """
        allowed = ["client_lookup", "relationship_summary", "credit_snapshot", "trade_activity", "gl_summary", "calculator"]
        tools = []
        for tool_name in allowed:
            if tool_name in self.gateway.list_tools():
                wrapper = DSPyToolWrapper(tool_name, self.gateway, caller_agent="internal_data", trace_id=self.trace_id)
                tools.append(wrapper.to_dspy_tool())
        return tools

    def get_tool_descriptions(self, tool_names: List[str]) -> str:
        descs = []
        for name in tool_names:
            defn = self.gateway.get_tool_definition(name)
            if defn:
                descs.append(f"{name}: {defn.description} (authoritative={defn.is_authoritative}, mutating={defn.is_state_mutating})")
        return "\n".join(descs)
