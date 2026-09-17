"""Contract tests for tool schemas and provider interfaces"""
import pytest
from src.financial_agent.tools.gateway import ToolGateway
from src.financial_agent.providers.internal_provider import SyntheticInternalDataProvider
from src.financial_agent.providers.external_provider import MockExternalProvider
from src.financial_agent.schemas.tools import ToolStatus

def test_tool_gateway_definitions():
    internal = SyntheticInternalDataProvider()
    external = MockExternalProvider()
    gateway = ToolGateway(internal, external)

    tools = gateway.list_tools()
    assert "client_lookup" in tools
    assert "credit_snapshot" in tools
    assert "document_search" in tools
    assert "calculator" in tools

    for tool_name in tools:
        defn = gateway.get_tool_definition(tool_name)
        assert defn is not None
        assert defn.name == tool_name
        assert defn.timeout_seconds > 0
        assert isinstance(defn.is_authoritative, bool)
        assert isinstance(defn.is_state_mutating, bool)

def test_tool_gateway_authz():
    internal = SyntheticInternalDataProvider()
    external = MockExternalProvider()
    gateway = ToolGateway(internal, external)

    # research agent should NOT be able to call internal tools
    result = gateway.call(
        tool_name="credit_snapshot",
        caller_agent="research",
        trace_id="test_trace",
        client_id="client_001"
    )
    assert result.status == ToolStatus.auth_error

    # internal_data agent CAN call internal tools
    result = gateway.call(
        tool_name="client_lookup",
        caller_agent="internal_data",
        trace_id="test_trace",
        client_name="Nordic Industrial A/S"
    )
    assert result.status == ToolStatus.success

def test_tool_failure_semantics():
    internal = SyntheticInternalDataProvider(simulate_failures=True)
    external = MockExternalProvider()
    gateway = ToolGateway(internal, external)

    # Tech Ventures should timeout for credit_snapshot when simulate_failures=True
    result = gateway.call(
        tool_name="credit_snapshot",
        caller_agent="internal_data",
        trace_id="test_trace",
        client_id="client_004"
    )
    # Should be timeout, not success with zero
    assert result.status == ToolStatus.timeout
    assert result.data is None or result.data.get("exposure") is None or result.status != ToolStatus.success
    # Must not invent zero
    if result.data:
        assert result.data.get("exposure") != 0 or result.status != ToolStatus.success

    # Missing data case - Green Energy
    internal2 = SyntheticInternalDataProvider(simulate_failures=False)
    gateway2 = ToolGateway(internal2, external)
    result2 = gateway2.call(
        tool_name="credit_snapshot",
        caller_agent="internal_data",
        trace_id="test_trace",
        client_id="client_003"
    )
    assert result2.status == ToolStatus.source_unavailable
    # Should not invent exposure
    assert result2.data.get("exposure") is None

def test_internal_provider_governance():
    provider = SyntheticInternalDataProvider()
    result = provider.client_lookup(client_name="Nordic Industrial A/S")
    assert result.governance is not None
    assert result.governance.authoritative == True
    assert result.governance.permitted == True
    assert result.governance.source == "synthetic_crm"

def test_external_provider_governance():
    provider = MockExternalProvider()
    results = provider.search("Nordic Industrial EBITDA", top_k=2)
    assert len(results) == 2
    for ev in results:
        assert ev.governance is not None
        assert ev.governance.provenance
