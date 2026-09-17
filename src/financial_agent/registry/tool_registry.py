"""
Tool Registry - backed by ToolGateway
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase

class ToolManifest(RegistryEntry):
    id: str  # tool_id
    version: str
    description: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    owner: str = "platform"
    authorisation_policy: Dict[str, Any] = Field(default_factory=dict)  # which agents can use
    authoritative: bool = False  # is this authoritative business state?
    state_mutating: bool = False
    timeout_ms: int = 5000
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    data_classification: str = "internal"  # public, internal, confidential, restricted
    status: str = "active"
    tags: List[str] = Field(default_factory=list)

class ToolRegistry(RegistryBase[ToolManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("tools", ToolManifest, registry_root)

    def get_allowed_for_agent(self, agent_capabilities: List[str]) -> List[ToolManifest]:
        """Get tools allowed for given agent capabilities"""
        allowed = []
        for tool in self._cache.values():
            if tool.status != "active":
                continue
            # Check auth policy
            policy = tool.authorisation_policy
            if not policy:
                allowed.append(tool)
                continue
            # If policy has allowed_agents or allowed_capabilities
            if "allow_all" in policy and policy["allow_all"]:
                allowed.append(tool)
            elif "allowed_capabilities" in policy:
                if any(cap in policy["allowed_capabilities"] for cap in agent_capabilities):
                    allowed.append(tool)
            else:
                allowed.append(tool)
        return allowed

    def get_research_tools(self) -> List[ToolManifest]:
        """Research agent can only use non-authoritative, non-internal tools"""
        return [t for t in self._cache.values() if not t.authoritative and t.data_classification in ["public", "external"] and t.status == "active"]

    def get_authoritative_tools(self) -> List[ToolManifest]:
        return [t for t in self._cache.values() if t.authoritative]
