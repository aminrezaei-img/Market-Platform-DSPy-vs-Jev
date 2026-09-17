"""
Workflow Registry - framework-neutral workflow manifests
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase

class WorkflowNode(BaseModel):
    id: str
    type: str  # agent, tool, router, verifier, synthesiser
    agent_version: Optional[str] = None
    tool_requirements: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)

class WorkflowEdge(BaseModel):
    from_node: str
    to_node: str
    condition: Optional[str] = None

class WorkflowManifest(RegistryEntry):
    id: str
    version: str
    owner: str = "platform"
    description: str = ""
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)
    parallel_branches: List[List[str]] = Field(default_factory=list)
    agent_versions: Dict[str, str] = Field(default_factory=dict)
    tool_requirements: List[str] = Field(default_factory=list)
    memory_requirements: Dict[str, str] = Field(default_factory=dict)
    failure_policy: str = "fail_closed"  # fail_closed, fail_open, retry
    entry_node: str = "supervisor"
    exit_node: str = "synthesiser"
    framework: str = "langgraph"  # runtime implementation
    status: str = "active"

class WorkflowRegistry(RegistryBase[WorkflowManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("workflows", WorkflowManifest, registry_root)
