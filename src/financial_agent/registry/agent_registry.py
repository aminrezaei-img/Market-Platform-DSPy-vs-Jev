"""
Agent Registry - first-class agent identity
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase

class AgentManifest(RegistryEntry):
    """
    Agent manifest per spec section 4
    """
    id: str  # e.g. markets.pre_meeting_brief
    version: str  # semver
    owner: str = "markets-ai"
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    workflow_id: str = "pre_meeting_brief_v3"
    workflow_version: str = "3"
    input_contract: Dict[str, Any] = Field(default_factory=dict)
    output_contract: Dict[str, Any] = Field(default_factory=dict)
    model_policy: Dict[str, str] = Field(default_factory=dict)  # supervisor, verifier
    tool_policy: Dict[str, Any] = Field(default_factory=dict)  # allow list
    memory_policy: Dict[str, str] = Field(default_factory=dict)
    eval_policy: Dict[str, str] = Field(default_factory=dict)  # required_suite
    status: str = "active"  # active, deprecated, blocked

    def full_id(self) -> str:
        return f"{self.id}@{self.version}"

class AgentRegistry(RegistryBase[AgentManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("agents", AgentManifest, registry_root)

    def get_active(self) -> List[AgentManifest]:
        return [e for e in self._cache.values() if e.status == "active"]

    def reconstruct(self, agent_id: str, version: str) -> Dict[str, Any]:
        """
        Reconstruct agent from registry state - must be possible
        """
        manifest = self.get(agent_id, version)
        if not manifest:
            raise ValueError(f"Agent {agent_id}@{version} not found")

        return {
            "agent": manifest.model_dump(),
            "workflow_ref": f"{manifest.workflow_id}@{manifest.workflow_version}",
            "model_policy": manifest.model_policy,
            "tool_policy": manifest.tool_policy,
            "memory_policy": manifest.memory_policy,
            "eval_policy": manifest.eval_policy,
            "reconstructable": True
        }
